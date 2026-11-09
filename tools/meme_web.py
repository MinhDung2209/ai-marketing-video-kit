"""Meme từ các kho lớn trên web — CHỈ LƯU LINK, lúc dựng clip mới để ffmpeg đọc link, cắt đoạn, tách nền.

Kho: meme-library/sources_web.json (greenscreenmemes, memescreens, memes-download, tiengdong, myinstants, imgflip).
Danh mục link đã chọn: meme-library/web.json.

  python tools/meme_web.py chờ                         # tìm trong web.json (tags/tên)
  python tools/meme_web.py --search "waiting" [--site memescreens] [--n 8]   # tìm TRỰC TIẾP trên các kho, in link tải thẳng
  python tools/meme_web.py --search "bất ngờ" --site tiengdong --add 1,3 --tags "bất ngờ, wow" [--kind sound]
  python tools/meme_web.py --fetch <thư mục clip> id1 id2   # ffmpeg đọc link → <clip>/assets/meme/<id>.webm|.mp3
  python tools/meme_web.py --preview id                   # 1 khung đã tách nền (kiểm bằng mắt) → in đường dẫn ảnh

engine.Story.finish() tự gọi fetch() cho sticker chưa có trong assets/meme (nên không cần chạy --fetch tay).
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import argparse, html, json, os, pathlib, re, shutil, subprocess, tempfile, unicodedata, urllib.parse, urllib.request

KIT = pathlib.Path(__file__).resolve().parent.parent
LIB = KIT / "meme-library"
WEB, SRC = LIB / "web.json", LIB / "sources_web.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
fold = lambda s: "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn").replace("đ", "d")


def ffbin(name):
    try:
        c = json.load(open(KIT / "config.json", encoding="utf-8")).get("screendemo", {}).get("ffmpeg")
        if c:
            p = pathlib.Path(c).parent / (name + (".exe" if os.name == "nt" else ""))
            if p.exists(): return str(p)
    except Exception: pass
    return shutil.which(name) or name


FF, FP = ffbin("ffmpeg"), ffbin("ffprobe")


def load(p): return json.load(open(p, encoding="utf-8"))
def get(url, ref=None):
    rq = urllib.request.Request(url, headers={"User-Agent": UA, **({"Referer": ref} if ref else {})})
    return urllib.request.urlopen(rq, timeout=30).read().decode("utf-8", "replace")


# ------------------------------------------------------------------ tìm trực tiếp trên kho
def search_site(name, s, q, n):
    if "api" in s:                                  # imgflip
        ms = json.loads(get(s["api"]))["data"]["memes"]
        return [dict(site=name, title=m["name"], page="https://imgflip.com/memetemplates", url=m["url"], kind="image")
                for m in ms if fold(q) in fold(m["name"])][:n]
    page = get(s["search"].format(q=urllib.parse.quote_plus(q)))
    base = s.get("base", "")
    if s.get("direct"):
        urls = list(dict.fromkeys(re.findall(s["media"], page)))[:n]
        return [dict(site=name, title=pathlib.Path(urllib.parse.unquote(u)).stem, page=s["search"].format(q=urllib.parse.quote_plus(q)),
                     url=(base + u if u.startswith("/") else u), kind="sound" if u.endswith(".mp3") else "full") for u in urls]
    items = [base + h if h.startswith("/") else h for h in dict.fromkeys(re.findall(s["item"], page))]
    out = []
    for it in items:
        if len(out) >= n: break
        try: p = get(it, ref=s["home"])
        except Exception: continue
        m = re.findall(s["media"], html.unescape(p))
        if not m: continue
        t = re.search(r"<title>(.*?)</title>", p, re.S)
        out.append(dict(site=name, title=html.unescape(t.group(1)).split("|")[0].split(" - ")[0].strip() if t else it,
                        page=it, url=m[0], kind="green" if "green" in (it + m[0]).lower() else "full"))
    return out


def slug(t): return re.sub(r"[^a-z0-9]+", "-", fold(t)).strip("-")[:40] or "meme"


# ------------------------------------------------------------------ tải lúc dựng
def probe_dur(src, hdr):
    r = subprocess.run([FP, "-v", "error", *hdr, "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return None


def key_color(src, hdr, t):
    raw = subprocess.run([FF, "-nostdin", "-v", "error", *hdr, "-ss", str(t), "-i", src, "-frames:v", "1",
                          "-vf", "crop=8:8:4:4,scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return raw[:3].hex() if len(raw) >= 3 else "00ff00"


def auto_crop(src, hdr, keyf, ss, t):
    """Khung bao quanh phần KHÔNG phải nền (gộp nhiều khung) → w:h:x:y, chừa lề 4%."""
    r = subprocess.run([FF, "-nostdin", "-hide_banner", *hdr, "-ss", str(ss), "-t", str(t), "-i", src, "-vf",
                        f"{keyf},format=yuva420p,alphaextract,format=yuv420p,cropdetect=limit=0.25:round=2:reset=0", "-f", "null", "-"], capture_output=True, text=True)
    c = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
    if not c: return None
    w, h, x, y = map(int, c[-1]); W = H = None
    m = re.search(r"Stream.*Video.*?(\d{3,5})x(\d{3,5})", r.stderr)
    if m: W, H = int(m.group(1)), int(m.group(2))
    px, py = int(w * .04) + 2, int(h * .04) + 2
    x, y = max(0, x - px), max(0, y - py); w, h = w + 2 * px, h + 2 * py
    if W: w, h = min(w, W - x), min(h, H - y)
    return f"{w - w % 2}:{h - h % 2}:{x}:{y}"


def fetch_one(m, dst):
    dst = pathlib.Path(dst); dst.mkdir(parents=True, exist_ok=True)
    hdr = ["-user_agent", UA, "-headers", f"Referer: {m.get('page', m['url'])}\r\n"]
    src = m["url"]; ss = float(m.get("ss", 0)); kind = m.get("kind", "green")
    dur = probe_dur(src, hdr) or float(m.get("dur", 3))
    t = float(m.get("t", max(0.1, dur - ss)))
    cut = ["-ss", f"{ss:.3f}", "-t", f"{t:.3f}"]
    res = {}
    if kind != "image":
        a = dst / f"{m['id']}.mp3"
        r = subprocess.run([FF, "-nostdin", "-v", "error", "-y", *hdr, *cut, "-i", src, "-vn", "-ac", "1", "-ar", "44100", "-b:a", "160k", str(a)], capture_output=True)
        if r.returncode == 0 and a.exists() and a.stat().st_size > 1000: res["audio"] = str(a)
    if kind == "sound": return res
    v = dst / f"{m['id']}.webm"
    if kind == "image":
        subprocess.run([FF, "-nostdin", "-v", "error", "-y", *hdr, "-i", src, "-vf", "scale=540:-2", str(dst / f"{m['id']}.png")], check=True)
        return {"image": str(dst / f"{m['id']}.png")}
    if kind == "green":
        k = m.get("key") or key_color(src, hdr, ss + 0.3)
        keyf = f"chromakey=0x{k}:{m.get('sim', 0.13)}:{m.get('blend', 0.06)}"
        crop = m.get("crop") or auto_crop(src, hdr, keyf, ss, t)
        vf = f"{'crop=' + crop + ',' if crop else ''}{keyf},despill=green,scale='min(540,iw)':-2:flags=lanczos,format=yuva420p"
        venc = ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", "-auto-alt-ref", "0"]
    else:
        vf = "scale='min(720,iw)':-2:flags=lanczos"; venc = ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32"]
    subprocess.run([FF, "-nostdin", "-v", "error", "-y", *hdr, *cut, "-i", src, "-vf", vf, "-an", *venc, str(v)], check=True)
    subprocess.run([FF, "-nostdin", "-v", "error", "-y", "-c:v", "libvpx-vp9", "-ss", f"{t * 0.45:.2f}", "-i", str(v), "-frames:v", "1", "-vf", "format=rgba", str(dst / f"{m['id']}.png")])
    res["video"] = str(v); res["dur"] = t
    return res


def catalog():
    return {m["id"]: m for m in load(WEB)["items"]} if WEB.exists() else {}


def fetch(proj, ids, force=False):
    """Gọi từ engine: tải các meme web chưa có trong <proj>/assets/meme. Trả về {id: kết quả}."""
    cat, out = catalog(), {}
    dst = pathlib.Path(proj) / "assets" / "meme"
    for i in ids:
        if i not in cat: continue
        m = cat[i]; have = dst / f"{i}.{'mp3' if m.get('kind') == 'sound' else 'webm'}"
        if have.exists() and not force:
            out[i] = {"video": str(dst / f"{i}.webm"), "audio": str(dst / f"{i}.mp3") if (dst / f"{i}.mp3").exists() else None}; continue
        print(f"  ⬇ meme {i}  ← {m['url']}")
        out[i] = fetch_one(m, dst)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("q", nargs="*"); ap.add_argument("--search"); ap.add_argument("--site"); ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--add"); ap.add_argument("--tags", default=""); ap.add_argument("--kind"); ap.add_argument("--id")
    ap.add_argument("--fetch", nargs="+"); ap.add_argument("--preview")
    a = ap.parse_args()
    if a.fetch:
        print(json.dumps(fetch(a.fetch[0], a.fetch[1:], force=True), ensure_ascii=False, indent=1)); return
    if a.preview:
        d = pathlib.Path(tempfile.mkdtemp(prefix="meme_")); r = fetch_one(catalog()[a.preview], d)
        bg = d / "preview.png"
        if r.get("video"):
            fr = d / "frame.png"
            subprocess.run([FF, "-nostdin", "-v", "error", "-y", "-c:v", "libvpx-vp9", "-ss", f"{r['dur'] * 0.45:.2f}", "-i", r["video"],
                            "-frames:v", "1", "-vf", "format=rgba", str(fr)])
            subprocess.run([FF, "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x1E1B4B:s=600x600:d=1", "-i", str(fr),
                            "-filter_complex", "[1:v]scale=580:580:force_original_aspect_ratio=decrease[f];[0:v][f]overlay=(W-w)/2:(H-h)/2",
                            "-frames:v", "1", str(bg)])
        print(json.dumps({**r, "preview": str(bg) if bg.exists() else None}, ensure_ascii=False, indent=1)); return
    if a.search:
        S = load(SRC)["sites"]; res = []
        for name, s in S.items():
            if a.site and name != a.site: continue
            if not a.site and name == "imgflip": continue
            try: res += search_site(name, s, a.search, a.n)
            except Exception as e: print(f"  ⚠ {name}: {e}")
        for k, r in enumerate(res, 1):
            print(f"{k:2d}. [{r['site']}] {r['kind']:5s} {r['title'][:60]}\n      {r['url']}")
        if a.add:
            W = load(WEB) if WEB.exists() else {"items": []}; have = {m["id"] for m in W["items"]}
            for k in [int(x) for x in a.add.split(",")]:
                r = res[k - 1]; i = a.id if (a.id and len(a.add.split(",")) == 1) else slug(r["title"])
                while i in have: i += "-2"
                W["items"].append(dict(id=i, kind=a.kind or r["kind"], title=r["title"], tags=[t.strip() for t in a.tags.split(",") if t.strip()],
                                       page=r["page"], url=r["url"], site=r["site"]))
                have.add(i); print(f"  + {i}")
            json.dump(W, open(WEB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return
    q = fold(" ".join(a.q)); n = 0
    for m in catalog().values():
        if not q or q in fold(m["id"] + " " + m.get("title", "") + " " + " ".join(m.get("tags", []))):
            print(f"{m['id']:24s} {m.get('kind', ''):6s} {', '.join(m.get('tags', [])[:5]):44s} {m.get('use', '')}"); n += 1
    print(f"— {n} meme (link) · tìm thêm trên web: --search \"từ khoá\"")


if __name__ == "__main__":
    main()
