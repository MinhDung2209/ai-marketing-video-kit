"""Gom danh mục SFX / nhạc nền công khai trên mạng về audio-library/web.json (CHỈ lưu URL + tên + thẻ + độ dài).
Tải file thật lúc dựng (audio_web.py pick/fetch). Chạy lại bất cứ lúc nào: chỉ thêm mục mới, không xoá mục cũ.

  python audio_harvest.py mixkit [--kind sfx|bgm|all] [--limit-cats N]
  python audio_harvest.py stats

Nguồn đã có bộ quét: Mixkit (≈276 danh mục SFX + ≈100 thể loại nhạc). Thêm nguồn mới = thêm 1 hàm harvest_<tên>.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import argparse, collections, datetime as dt, html, json, pathlib, re, time
import requests

KIT = pathlib.Path(__file__).resolve().parent.parent
WEB = KIT / "audio-library" / "web.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"}
S = requests.Session(); S.headers.update(UA)


def get(url, tries=3):
    for i in range(tries):
        try:
            r = S.get(url, timeout=30)
            if r.status_code == 404: return ""
            r.raise_for_status(); return r.text
        except requests.RequestException:
            time.sleep(2 * (i + 1))
    return ""


def secs(t):
    p = [int(x) for x in t.strip().split(":") if x.strip().isdigit()]
    return float(p[0] * 60 + p[1]) if len(p) == 2 else (float(p[0]) if p else None)




def parse_mixkit(page, kind, cat):
    out = []
    for blk in page.split('data-test-id="audio-player"')[1:]:   # mỗi thẻ bắt đầu bằng trình phát
        m = re.search(r'data-audio-player-preview-url-value="([^"]+)"', blk)
        i = re.search(r'data-audio-player-item-id-value="(\d+)"', blk)
        t = re.search(r'item-grid-card__title">\s*([^<]+?)\s*<', blk)
        if not (m and i and t): continue
        d = re.search(r'data-test-id="duration">\s*([\d:]+)\s*<', blk)
        tags = re.findall(r'meta-links__link"[^>]*href="/free-(?:sound-effects|stock-music)/([a-z0-9-]+)/"', blk)
        out.append(dict(id=f"mixkit-{'sfx' if kind == 'sfx' else 'bgm'}-{i[1]}", source="mixkit", kind=kind,
                        title=html.unescape(t[1]), duration=secs(d[1]) if d else None, file_url=m[1],
                        page_url=f"https://mixkit.co/free-{'sound-effects' if kind == 'sfx' else 'stock-music'}/{cat}/",
                        tags=sorted(set(tags + [cat])), creator="Mixkit"))
    return out


def harvest_mixkit(kind, limit):
    base = {"sfx": "https://mixkit.co/free-sound-effects/", "bgm": "https://mixkit.co/free-stock-music/"}[kind]
    seg = base.split("mixkit.co/")[1].strip("/")
    cats = sorted(set(re.findall(rf'href="/{seg}/([a-z0-9-]+)/"', get(base))))
    if kind == "bgm":   # trang nhạc còn liệt kê tâm trạng/nhạc cụ ở các trang con
        for extra in ("mood", "instrument", "genre"):
            cats += re.findall(rf'href="/{seg}/([a-z0-9-]+)/"', get(base + extra + "/"))
        cats = sorted(set(c for c in cats if c not in ("mood", "instrument", "genre")))
    cats = cats[:limit] if limit else cats
    print(f"mixkit {kind}: {len(cats)} danh mục", file=_sys.stderr)
    found = {}
    for n, c in enumerate(cats, 1):
        for pg in range(1, 30):
            page = get(f"{base}{c}/" + (f"?page={pg}" if pg > 1 else ""))
            items = parse_mixkit(page, kind, c) if page else []
            new = [x for x in items if x["id"] not in found]
            for x in items:
                if x["id"] in found: found[x["id"]]["tags"] = sorted(set(found[x["id"]]["tags"]) | set(x["tags"]))
                else: found[x["id"]] = x
            if not new: break
            time.sleep(0.4)
        if n % 20 == 0: print(f"  {n}/{len(cats)} danh mục · {len(found)} mục", file=_sys.stderr)
    return list(found.values())


def merge(items):
    web = json.load(open(WEB, encoding="utf-8")) if WEB.exists() else []
    idx = {w["id"]: w for w in web}; added = 0
    for x in items:
        if x["id"] in idx: idx[x["id"]]["tags"] = sorted(set(idx[x["id"]].get("tags", [])) | set(x["tags"]))
        else:
            x["added"] = dt.date.today().isoformat(); web.append(x); idx[x["id"]] = x; added += 1
    WEB.parent.mkdir(parents=True, exist_ok=True)
    json.dump(web, open(WEB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return added, len(web)


def alive(url):
    """True = còn tải được; False = chết hẳn (404/410/…); None = lỗi tạm (mạng, 429, 5xx) → không tính."""
    try:
        r = S.head(url, timeout=20, allow_redirects=True)
        if r.status_code in (403, 405):   # có nơi chặn HEAD → thử GET 1 byte
            r = S.get(url, timeout=20, headers={"Range": "bytes=0-0"}, stream=True); r.close()
        if r.status_code < 400: return True
        if r.status_code in (429,) or r.status_code >= 500: return None
        return False
    except requests.RequestException:
        return None


def audit(path, drop_after=2, workers=16):
    """Kiểm mọi URL trong 1 danh mục web.json (âm thanh hoặc meme). Ghi last_ok / fails vào từng mục;
    mục chết liên tiếp ≥ drop_after lần → chuyển sang <tên>.dead.json (không mất hẳn, khôi phục được)."""
    from concurrent.futures import ThreadPoolExecutor
    path = pathlib.Path(path); doc = json.load(open(path, encoding="utf-8"))
    items = doc["items"] if isinstance(doc, dict) else doc      # meme-library/web.json = {"_huong_dan", "items"}
    key = lambda w: next((w[k] for k in ("file_url", "url", "src", "video_url", "mp4") if w.get(k)), None)
    today = dt.date.today().isoformat()
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(lambda w: alive(key(w)) if key(w) else False, items))
    keep, dead, tmp = [], [], 0
    for w, ok in zip(items, res):
        if ok is True: w["last_ok"], w["fails"] = today, 0
        elif ok is False: w["fails"] = w.get("fails", 0) + 1
        else: tmp += 1
        (dead if w.get("fails", 0) >= drop_after else keep).append(w)
    if isinstance(doc, dict): doc["items"] = keep
    json.dump(doc if isinstance(doc, dict) else keep, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if dead:
        dp = path.with_suffix(".dead.json"); old = json.load(open(dp, encoding="utf-8")) if dp.exists() else []
        json.dump(old + dead, open(dp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    bad = sum(1 for w in keep if w.get("fails"))
    print(f"{path.name}: {len(items)} mục · còn sống {sum(1 for r in res if r is True)} · hỏng lần đầu {bad} · "
          f"lỗi tạm {tmp} · loại bỏ {len(dead)}" + (f" → {path.with_suffix('.dead.json').name}" if dead else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("source", choices=["mixkit", "stats", "audit"])
    ap.add_argument("--kind", default="all", choices=["sfx", "bgm", "all"]); ap.add_argument("--limit-cats", type=int)
    ap.add_argument("--file", action="append", help="audit: danh mục cần kiểm (mặc định: audio-library/web.json + meme-library/web.json)")
    a = ap.parse_args()
    if a.source == "audit":
        for f in a.file or [WEB, KIT / "meme-library" / "web.json"]:
            if pathlib.Path(f).exists(): audit(f)
        raise SystemExit
    if a.source == "stats":
        web = json.load(open(WEB, encoding="utf-8")) if WEB.exists() else []
        print(collections.Counter((w.get("source"), w.get("kind")) for w in web)); raise SystemExit
    for k in (["sfx", "bgm"] if a.kind == "all" else [a.kind]):
        got = harvest_mixkit(k, a.limit_cats)
        add, tot = merge(got)
        print(f"mixkit {k}: quét {len(got)} · thêm mới {add} · danh mục web.json có {tot} mục")
