"""Tìm meme/sticker trong meme-library theo từ khoá (tiếng Việt / tiếng Anh) và chép vào dự án.

Dùng:  python tools/meme_search.py tiền                     # liệt kê
       python tools/meme_search.py --copy noto/fire noto/check <thư mục dự án>   # chép vào <dự án>/assets/meme/
       python tools/meme_search.py --rank "tiền" --used noto/money-face -n 3   # shortlist JSON
Xếp hạng tuỳ chọn qua meme_rank: --used / --used-id lặp lại theo số lần dùng
trong clip hiện tại; --used-file nhận JSON [ID, ...] hoặc {ID: số lần dùng}.
--catalog lặp lại để gộp catalog.json/web.json; --emotion lọc cảm xúc;
--rank --help liệt kê đầy đủ. Không tải tài sản hay lưu lịch sử dùng.
Trong index.html:  <video class="meme" src="assets/meme/fire.webm" muted playsinline preload="auto" data-loop="1">
(nền trong suốt; render.py tua từng khung). Luật dùng: docs/11-meme-va-sticker.md.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import json, pathlib, shutil, sys, unicodedata

# Keep ranking optional: legacy search/copy never imports the ranking module.
if "--rank" in sys.argv[1:]:
    try:
        from meme_rank import main as rank_main
    except ImportError as exc:
        print(json.dumps({
            "status": "unavailable",
            "error": f"Optional meme ranking module is unavailable: {exc}",
            "remediation": "Restore tools/meme_rank.py or use search/--copy without --rank. No download was attempted.",
        }, ensure_ascii=False, indent=2))
        sys.exit(2)
    sys.exit(rank_main([arg for arg in sys.argv[1:] if arg != "--rank"]))

LIB = pathlib.Path(__file__).resolve().parent.parent / "meme-library"
cat = json.load(open(LIB / "catalog.json", encoding="utf-8"))["items"]
fold = lambda s: "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn").replace("đ", "d")

if len(sys.argv) > 2 and sys.argv[1] == "--copy":
    *ids, proj = sys.argv[2:]
    dst = pathlib.Path(proj) / "assets" / "meme"; dst.mkdir(parents=True, exist_ok=True)
    by = {m["id"]: m for m in cat}
    for i in ids:
        m = by.get(i) or sys.exit(f"không có meme: {i}")
        shutil.copy2(LIB / m["file"], dst / pathlib.Path(m["file"]).name)
        shutil.copy2(LIB / m["poster"], dst / pathlib.Path(m["poster"]).name)
        print(f"✅ {i} → {dst / pathlib.Path(m['file']).name}  ({m['license']} — ghi nguồn: {m['attribution']})")
    sys.exit(0)

q = fold(" ".join(sys.argv[1:]))
hits = [m for m in cat if not q or q in fold(m["id"] + " " + " ".join(m["tags"]))]
for m in hits:
    print(f"{m['id']:26s} {m['duration']:5.2f}s  {', '.join(m['tags'][:5]):48s} {m['license']}")
print(f"— {len(hits)} kết quả")
