"""Tìm hiệu ứng âm thanh trong kit/audio-library/catalog.json theo từ khoá (tên file / thư mục / ghi chú).

Dùng: python sfx_search.py typing           → mọi file có "typing"
      python sfx_search.py whoosh --max 1.5  → whoosh dài ≤ 1,5 giây
      python sfx_search.py --kind bgm        → liệt kê nhạc nền
Từ khoá gợi ý: typing key-press keyboard typewriter | whoosh swoosh sweep transition | click tap select |
pop notify chime success | riser impact bass | counter tick | glitch data scan | camera zoom | paper
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, json, pathlib
LIB = pathlib.Path(__file__).resolve().parent.parent / "audio-library"
ap = argparse.ArgumentParser(); ap.add_argument("q", nargs="*"); ap.add_argument("--kind"); ap.add_argument("--max", type=float)
a = ap.parse_args()
cat = json.load(open(LIB / "catalog.json", encoding="utf-8"))
n = 0
for c in cat:
    hay = (c["path"] + " " + (c.get("note") or "")).lower()
    if a.kind and c["kind"] != a.kind: continue
    if a.q and not all(q.lower() in hay for q in a.q): continue
    if a.max and (c.get("duration") or 0) > a.max: continue
    print(f'{c["path"]:<60} {c.get("duration") or "?":>6}s  {c["license"]}'); n += 1
print(f"— {n} kết quả")
