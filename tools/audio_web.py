"""Tìm SFX / nhạc nền TRÊN MẠNG (rộng hơn thư viện cố định trong kit) — chỉ lưu URL, tải về lúc dựng.

  python audio_web.py search sfx "whoosh" [--max 2] [--n 12]        → liệt kê ứng viên (đánh số)
  python audio_web.py search bgm "upbeat corporate" [--min 60] [--speed high]
  python audio_web.py pick <dự án> <need-id> sfx "whoosh" --max 2 --n 8
        → tải bản nghe thử của n ứng viên vào <dự án>/sources/audio/<need-id>/NN-*.mp3,
          ghép 1 file nghe thử (đọc số thứ tự trước mỗi tiếng) + ghi candidates vào <dự án>/sources/audio/<need-id>.json
  python audio_web.py fetch <dự án> <need-id> <số> → chép bản đã chọn thành <dự án>/assets/src/<need-id>.mp3,
          ghi nguồn + giấy phép vào sources/credits.md, và lưu URL vào audio-library/web.json (dùng lại cho video sau)

Nguồn (theo thứ tự): Freesound API (config freesound_api_key — lọc độ dài chính xác, sắp theo đánh giá),
Jamendo API cho nhạc (config jamendo_client_id — lọc thể loại/tốc độ, CHỈ giữ giấy phép cho phép thương mại),
Openverse (không cần khoá; Freesound + Jamendo + ccMixter, lọc độ dài phía máy). Thiếu khoá → bỏ qua nguồn đó.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import argparse, hashlib, json, pathlib, re, shutil, subprocess, datetime as dt
import requests

KIT = pathlib.Path(__file__).resolve().parent.parent
WEB = KIT / "audio-library" / "web.json"
UA = {"User-Agent": "ai-marketing-video-kit/1.0 (audio_web)"}
T = 25


def cfg():
    try: return json.load(open(KIT / "config.json", encoding="utf-8"))
    except OSError: return {}


def commercial(lic: str) -> bool:
    l = (lic or "").lower()
    return not any(x in l for x in ("-nc", "nc-", "/nc", "noncommercial", "sampling+"))


def freesound(q, kind, max_dur, min_dur, n, key):
    if not key: return []
    lo, hi = (min_dur or 0), (max_dur or (6 if kind == "sfx" else 600))
    p = dict(query=q, token=key, page_size=min(n * 2, 60), sort="rating_desc",
             filter=f"duration:[{lo} TO {hi}]" + (" tag:music" if kind == "bgm" else ""),
             fields="id,name,duration,license,username,previews,url,avg_rating,num_downloads")
    r = requests.get("https://freesound.org/apiv2/search/text/", params=p, headers=UA, timeout=T); r.raise_for_status()
    out = []
    for x in r.json().get("results", []):
        if not commercial(x["license"]): continue
        out.append(dict(source="freesound", id=f"fs{x['id']}", title=x["name"], duration=round(x["duration"], 2),
                        file_url=x["previews"]["preview-hq-mp3"], page_url=x["url"], license=x["license"],
                        creator=x["username"], score=(x.get("avg_rating") or 0) + min(x.get("num_downloads", 0), 5000) / 2500))
    return out


def jamendo(q, min_dur, max_dur, n, cid, speed=None):
    if not cid: return []
    p = dict(client_id=cid, format="json", limit=min(n * 3, 100), fuzzytags=q, ccnc="false", include="licenses musicinfo",
             audioformat="mp32", audiodlformat="mp32")
    if speed: p["speed"] = speed
    if min_dur or max_dur: p["durationbetween"] = f"{int(min_dur or 0)}_{int(max_dur or 900)}"
    rows = []
    for _ in range(3):   # Jamendo thỉnh thoảng trả rỗng ngẫu nhiên cho cùng 1 truy vấn → thử lại
        r = requests.get("https://api.jamendo.com/v3.0/tracks/", params=p, headers=UA, timeout=T); r.raise_for_status()
        rows = r.json().get("results", [])
        if rows: break
    out = []
    for x in rows:
        lic = x.get("license_ccurl", "")
        if not commercial(lic) or not x.get("audiodownload_allowed", True): continue
        out.append(dict(source="jamendo", id=f"jm{x['id']}", title=f"{x['name']} — {x['artist_name']}", duration=x["duration"],
                        file_url=x.get("audiodownload") or x["audio"], page_url=x.get("shareurl", ""), license=lic,
                        creator=x["artist_name"], score=1.0))
    return out


def openverse(q, kind, max_dur, min_dur, n):
    src = "freesound" if kind == "sfx" else "jamendo,ccmixter,freesound"
    p = dict(q=q, source=src, license_type="commercial", page_size=20)
    r = requests.get("https://api.openverse.org/v1/audio/", params=p, headers=UA, timeout=T); r.raise_for_status()
    out = []
    for x in r.json().get("results", []):
        d = (x.get("duration") or 0) / 1000
        if max_dur and d > max_dur: continue
        if min_dur and d < min_dur: continue
        out.append(dict(source="openverse/" + x["source"], id=f"ov{x['id'][:8]}", title=x["title"], duration=round(d, 2),
                        file_url=x["url"], page_url=x.get("foreign_landing_url", ""),
                        license=f"{x['license']} {x.get('license_version') or ''}".strip(), creator=x.get("creator") or "",
                        score=0.5))
    return out


def catalog(q, kind, max_dur, min_dur, n):
    """Danh mục URL đã gom (audio_harvest.py) — như meme-library/web.json. Khớp NGUYÊN TỪ; tên nặng hơn thẻ;
    độ dài trên trang nguồn làm tròn tới giây → nới 0,5 s khi lọc."""
    if not WEB.exists(): return []
    words = [w for w in re.split(r"\W+", q.lower()) if w]
    out = []
    for w in json.load(open(WEB, encoding="utf-8")):
        if w.get("kind") != kind: continue
        d = w.get("duration") or 0
        if (max_dur and d - 0.5 > max_dur) or (min_dur and d + 0.5 < min_dur): continue
        title = set(re.split(r"\W+", w["title"].lower()))
        tags = set(t for tag in w.get("tags", []) for t in re.split(r"\W+", tag.lower()))
        st = sum(1 for x in words if x in title or x + "s" in title or x.rstrip("s") in title)
        sg = sum(1 for x in words if x in tags)
        if not (st or sg): continue
        score = 2 * st + sg + (2 if st + sg >= len(words) else 0)
        out.append(dict(w, license=w.get("license", "Mixkit Free License" if w.get("source") == "mixkit" else ""), score=score))
    return sorted(out, key=lambda x: -x["score"])[: n * 2]


def search(kind, q, max_dur=None, min_dur=None, n=12, speed=None):
    c, res, seen = cfg(), [], set()
    calls = [("Danh mục web.json", lambda: catalog(q, kind, max_dur, min_dur, n))] + (
        [("Thư viện nhạc AI", lambda: ai_search(q, n))] if kind == "bgm" else []) + [
             ("Freesound", lambda: freesound(q, kind, max_dur, min_dur, n, c.get("freesound_api_key")))]
    if kind == "bgm": calls.append(("Jamendo", lambda: jamendo(q, min_dur, max_dur, n, c.get("jamendo_client_id"), speed)))
    calls.append(("Openverse", lambda: openverse(q, kind, max_dur, min_dur, n)))
    for name, f in calls:
        try:
            got = f(); print(f"  {name}: {len(got)} kết quả", file=_sys.stderr)
        except requests.RequestException as e:
            print(f"  {name}: lỗi mạng ({e.__class__.__name__}) — bỏ qua", file=_sys.stderr); got = []
        for x in sorted(got, key=lambda x: -x["score"]):
            k = re.sub(r"\W+", "", x["title"].lower())[:30]
            if k in seen: continue
            seen.add(k); res.append(x)
    if not c.get("freesound_api_key"):
        print("  (gợi ý: thêm freesound_api_key vào config.json → SFX lọc đúng độ dài, nhiều lựa chọn hơn hẳn)", file=_sys.stderr)
    if kind == "bgm" and not c.get("jamendo_client_id"):
        print("  (gợi ý: thêm jamendo_client_id vào config.json → kho nhạc nền rất lớn, lọc theo thể loại/tốc độ)", file=_sys.stderr)
    return res[:n]


def show(res):
    for i, x in enumerate(res, 1):
        print(f"{i:>2}. [{x['source']}] {x['title'][:50]:50} {x['duration']:>6}s  {x['license']}  · {x['creator']}")


def ff(*a): return subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *a], check=True)


AI_DIR = KIT / "audio-library" / "ai"; AI_CAT = AI_DIR / "catalog.json"   # thư viện nhạc AI đã tạo → dùng lại, không tốn lượt


def ai_catalog():
    return json.load(open(AI_CAT, encoding="utf-8")) if AI_CAT.exists() else []


def ai_save(f, prompt, seed, note=""):
    """Chép bản Lyria vừa tạo vào thư viện kit (mp3) + ghi catalog: prompt, seed, thẻ, ngày."""
    cat = ai_catalog(); sid = f"lyria-{hashlib.md5(prompt.encode()).hexdigest()[:8]}-s{seed}"
    if any(x["id"] == sid for x in cat): return
    (AI_DIR / "lyria").mkdir(parents=True, exist_ok=True); dst = AI_DIR / "lyria" / f"{sid}.mp3"
    ff("-i", str(f), "-c:a", "libmp3lame", "-q:a", "2", str(dst))
    tags = sorted(set(w for w in re.split(r"[^a-z0-9]+", prompt.lower()) if len(w) > 2) - {"and", "the", "with", "for", "no", "that"})
    cat.append(dict(id=sid, source="lyria (AI)", kind="bgm", title=f"Lyria · {prompt[:60]}", prompt=prompt, seed=seed,
                    duration=32.0, path=str(dst.relative_to(KIT)).replace("\\", "/"), tags=tags, note=note,
                    added=dt.date.today().isoformat()))
    json.dump(cat, open(AI_CAT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def ai_search(q, n):
    words = [w for w in re.split(r"\W+", q.lower()) if len(w) > 2]
    out = []
    for x in ai_catalog():
        hit = sum(1 for w in words if w in x["tags"])
        if hit: out.append(dict(x, local=str(KIT / x["path"]), file_url="", page_url="", license="tạo bằng AI (Google Lyria)",
                                creator="Google Lyria", score=hit + 1))
    return sorted(out, key=lambda x: -x["score"])[:n]


def lyria(d, prompt, k):
    """Nhạc AI bằng Google Lyria (tools/lyria_bgm.py, ~32 s/bản). Có sẵn trong thư viện (cùng prompt + seed) → dùng lại."""
    out = []
    for i in range(k):
        seed = 101 + i * 37; f = d / f"ai-lyria-s{seed}.wav"
        sid = f"lyria-{hashlib.md5(prompt.encode()).hexdigest()[:8]}-s{seed}"
        old = next((x for x in ai_catalog() if x["prompt"] == prompt and x["seed"] == seed), None)
        if old:
            print(f"  Lyria seed {seed}: dùng lại từ thư viện ({old['path']})", file=_sys.stderr)
            out.append(dict(old, local=str(KIT / old["path"]), file_url="", page_url="", license="tạo bằng AI (Google Lyria)",
                            creator="Google Lyria", score=0)); continue
        if not f.exists():
            r = subprocess.run([_sys.executable, "-X", "utf8", str(KIT / "tools" / "lyria_bgm.py"), prompt, str(f), "--seed", str(seed)],
                               capture_output=True, text=True, encoding="utf-8")
            if r.returncode or not f.exists():
                print(f"  Lyria seed {seed}: lỗi — {(r.stderr or r.stdout)[-200:]}", file=_sys.stderr); continue
        ai_save(f, prompt, seed)
        out.append(dict(source="lyria (AI)", id=sid, title=f"Lyria AI · seed {seed}", duration=32.0, file_url="",
                        page_url="", license="tạo bằng AI (Google Lyria)", creator="Google Lyria", local=str(f), score=0,
                        prompt=prompt, seed=seed))
        print(f"  Lyria: tạo xong seed {seed} (đã lưu vào thư viện AI)", file=_sys.stderr)
    return out


def pick(proj, need, kind, q, max_dur, min_dur, n, speed, ai=0, ai_prompt=None):
    res = search(kind, q, max_dur, min_dur, n, speed) if n else []
    d = pathlib.Path(proj).resolve() / "sources" / "audio" / need; d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.mp3"): old.unlink()                 # bỏ bản lẻ của lần chạy trước (bản AI .wav giữ lại)
    if kind == "bgm" and (ai or not res):   # không có bản nào → tự tạo 2 bản AI
        res += lyria(d, ai_prompt or f"{q}, instrumental, no vocals, clean mix for video background", ai or 2)
    if kind == "sfx" and ai:
        print("  (SFX AI: Lyria chỉ làm nhạc; SFX AI sẽ nối vào ComfyUI Stable Audio khi có server)", file=_sys.stderr)
    if not res: sys_exit("Không tìm được ứng viên nào — đổi từ khoá ngắn hơn (vd 'whoosh', 'upbeat corporate').")
    clip = 4 if kind == "sfx" else 20                       # nghe thử: SFX 4 s đầu, nhạc 20 s đầu
    parts, ok = [], []
    for i, x in enumerate(res, 1):
        f = d / f"{i:02d}-{x['id']}.mp3"
        try:
            if x.get("local"): f = pathlib.Path(x["local"])          # bản AI đã nằm sẵn trên máy
            elif not f.exists():
                r = requests.get(x["file_url"], headers=UA, timeout=60); r.raise_for_status(); f.write_bytes(r.content)
            x["local"] = str(f); ok.append(x)
            seg = d / f"_a{i:02d}.wav"
            num = KIT / "audio-library" / "so-thu-tu" / f"{i}.wav"   # giọng đọc "một, hai…" thay tiếng bíp (bíp dễ lẫn với ping/chime)
            if num.exists(): ff("-i", str(num), "-af", "apad=pad_dur=0.35", "-ar", "44100", "-ac", "2", str(d / f"_b{i:02d}.wav"))
            else: ff("-f", "lavfi", "-i", "sine=frequency=880:duration=0.12", "-t", "0.6", "-af", "apad=pad_dur=0.5", "-ar", "44100", "-ac", "2", str(d / f"_b{i:02d}.wav"))
            ff("-i", str(f), "-t", str(clip), "-af", "loudnorm=I=-16:TP=-1.5,apad=pad_dur=0.8", "-ar", "44100", "-ac", "2", str(seg))
            parts += [d / f"_b{i:02d}.wav", seg]
        except (requests.RequestException, subprocess.CalledProcessError) as e:
            print(f"  bỏ #{i} ({e.__class__.__name__})", file=_sys.stderr)
    lst = d / "_list.txt"; lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    aud = pathlib.Path(proj) / "sources" / "audio" / f"{need}-nghe-thu.mp3"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "libmp3lame", "-q:a", "3", str(aud))
    for p in d.glob("_*"): p.unlink()
    for x in ok:                                             # chỉ giữ file nghe thử + JSON (có URL); fetch tải lại đúng bản được chọn
        if x.get("file_url"): pathlib.Path(x["local"]).unlink(missing_ok=True); x.pop("local", None)
    json.dump(dict(need=need, kind=kind, query=q, candidates=ok), open(d.parent / f"{need}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    show(ok)
    print(f"\nNghe thử (giọng đọc số thứ tự trước mỗi ứng viên): {aud}")
    print(f"Chọn: python {pathlib.Path(__file__).as_posix()} fetch {proj} {need} <số>")


def fetch(proj, need, num):
    P = pathlib.Path(proj); meta = json.load(open(P / "sources" / "audio" / f"{need}.json", encoding="utf-8"))
    x = meta["candidates"][num - 1]
    dst = P / "assets" / "src" / f"{need}.mp3"; dst.parent.mkdir(parents=True, exist_ok=True)
    if x.get("local") and pathlib.Path(x["local"]).exists():
        if x["local"].lower().endswith(".mp3"): shutil.copy(x["local"], dst)
        else: ff("-i", x["local"], "-c:a", "libmp3lame", "-q:a", "2", str(dst))   # bản AI là WAV → mp3 thật
    else:
        r = requests.get(x["file_url"], headers=UA, timeout=120); r.raise_for_status()
        tmp = dst.with_suffix(".dl"); tmp.write_bytes(r.content)
        ff("-i", str(tmp), "-c:a", "libmp3lame", "-q:a", "2", str(dst)); tmp.unlink()
    cr = P / "sources" / "credits.md"; cr.parent.mkdir(parents=True, exist_ok=True)
    with open(cr, "a", encoding="utf-8") as fh:
        fh.write(f"- {need}: \"{x['title']}\" — {x['creator']} · {x['source']} · {x['license']} · {x['page_url']}\n")
    web = json.load(open(WEB, encoding="utf-8")) if WEB.exists() else []
    if x.get("file_url") and not any(w["id"] == x["id"] for w in web):   # bản AI không có URL → không vào danh mục
        web.append({k: x[k] for k in ("id", "source", "title", "duration", "file_url", "page_url", "license", "creator")}
                   | dict(kind=meta["kind"], tags=[meta["query"]], added=dt.date.today().isoformat()))
        json.dump(web, open(WEB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"xong: {dst}  (đã ghi nguồn vào sources/credits.md, URL vào audio-library/web.json)")


def sys_exit(m): print(m, file=_sys.stderr); raise SystemExit(2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("search", "pick"):
        s = sp.add_parser(name)
        if name == "pick": s.add_argument("project"); s.add_argument("need")
        s.add_argument("kind", choices=["sfx", "bgm"]); s.add_argument("query")
        s.add_argument("--max", type=float); s.add_argument("--min", type=float); s.add_argument("--n", type=int, default=10)
        s.add_argument("--speed", choices=["verylow", "low", "medium", "high", "veryhigh"])
        s.add_argument("--ai", type=int, default=0, help="pick: thêm N bản nhạc AI (Lyria) vào danh sách nghe thử")
        s.add_argument("--ai-prompt", help="câu lệnh tiếng Anh cho Lyria (mặc định: từ khoá + instrumental)")
    s = sp.add_parser("fetch"); s.add_argument("project"); s.add_argument("need"); s.add_argument("num", type=int)
    a = ap.parse_args()
    if a.cmd == "search": show(search(a.kind, a.query, a.max, a.min, a.n, a.speed))
    elif a.cmd == "pick": pick(a.project, a.need, a.kind, a.query, a.max, a.min, a.n, a.speed, a.ai, a.ai_prompt)
    else: fetch(a.project, a.need, a.num)
