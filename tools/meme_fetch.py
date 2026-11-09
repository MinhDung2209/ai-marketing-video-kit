"""Tải thư viện meme/sticker động (nguồn sạch giấy phép) → meme-library/<nguồn>/<id>.webm (nền trong suốt) + .png + catalog.json.

Dùng:  python tools/meme_fetch.py            # tải mục còn thiếu
       python tools/meme_fetch.py --force    # tải lại tất cả
Nguồn + giấy phép: meme-library/sources.json. Vì sao là WebM VP9 có alpha: render.py tua <video> từng khung chính xác
(GIF/WebP động trong <img> chạy theo đồng hồ thật → mỗi lần render một khác, không khớp nhịp).
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import argparse, json, os, pathlib, shutil, subprocess, tempfile, urllib.request

KIT = pathlib.Path(__file__).resolve().parent.parent
LIB = KIT / "meme-library"
FFMPEG = shutil.which("ffmpeg") or r"D:\Apps\ffmpeg\bin\ffmpeg.exe"
FFPROBE = shutil.which("ffprobe") or r"D:\Apps\ffmpeg\bin\ffprobe.exe"

ap = argparse.ArgumentParser(); ap.add_argument("--force", action="store_true"); a = ap.parse_args()
src = json.load(open(LIB / "sources.json", encoding="utf-8"))
cat_path = LIB / "catalog.json"
catalog = {m["id"]: m for m in json.load(open(cat_path, encoding="utf-8"))["items"]} if cat_path.exists() else {}

def duration(f):
    out = subprocess.run([FFPROBE, "-v", "error", "-count_frames", "-show_entries", "stream=nb_read_frames,r_frame_rate",
                          "-of", "json", str(f)], capture_output=True, text=True).stdout
    s = json.loads(out)["streams"][0]; n, d = s["r_frame_rate"].split("/")
    return round(int(s["nb_read_frames"]) / (int(n) / int(d)), 2)

ok = fail = 0
for key, s in src.items():
    if key.startswith("_"): continue
    out_dir = LIB / key; out_dir.mkdir(parents=True, exist_ok=True)
    for it in s["items"]:
        mid = f"{key}/{it['id']}"; webm = out_dir / f"{it['id']}.webm"; png = out_dir / f"{it['id']}.png"
        if webm.exists() and png.exists() and not a.force and mid in catalog: ok += 1; continue
        url = s["url"].format(code=it["code"])
        try:
            with tempfile.TemporaryDirectory() as td:
                gif = pathlib.Path(td) / "a.gif"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                gif.write_bytes(urllib.request.urlopen(req, timeout=60).read())
                subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(gif), "-vf", "scale=384:-1:flags=lanczos",
                                "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "32", "-an", str(webm)], check=True)
                subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(gif), "-vf", "select=eq(n\\,0),scale=384:-1",
                                "-frames:v", "1", str(png)], check=True)
                dur = duration(gif)
            catalog[mid] = {"id": mid, "file": f"{key}/{it['id']}.webm", "poster": f"{key}/{it['id']}.png", "type": "animated-emoji",
                            "duration": dur, "loop": True, "tags": it["tags"], "source": s["name"], "source_url": url,
                            "license": s["license"], "license_url": s["license_url"], "attribution": s["attribution"]}
            ok += 1; print(f"✅ {mid:28s} {dur:5.2f}s  {webm.stat().st_size // 1024} KB")
        except Exception as e:
            fail += 1; print(f"❌ {mid}: {e}")

json.dump({"_ghi_chu": "Sinh bởi tools/meme_fetch.py — không sửa tay. Tìm: python tools/meme_search.py <từ khoá>",
           "items": sorted(catalog.values(), key=lambda m: m["id"])}, open(cat_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"xong: {ok} có sẵn/tải được · {fail} lỗi · {cat_path}")
