"""Tìm + tải ảnh/clip stock miễn phí (Pexels video/ảnh, Unsplash ảnh) cho cảnh không cần ảnh AI.

Key (không commit): biến môi trường PEXELS_API_KEY / UNSPLASH_ACCESS_KEY, hoặc file .env ở thư mục đang chạy / kit/.env (mẫu: .env.example),
hoặc "pexels_api_key" / "unsplash_access_key" trong kit/config.json.

Dùng (chạy ở thư mục dự án):
  python <kit>/tools/stock_media.py search "da lat fog" --type video          → in ứng viên + ghép _stock_sheet.jpg để xem
  python <kit>/tools/stock_media.py search "pine forest" --type photo --source unsplash
  python <kit>/tools/stock_media.py get pexels:video:123456 assets/clips/hook.mp4
  python <kit>/tools/stock_media.py get unsplash:photo:AbCdEf assets/img/ho.jpg
Mỗi lần get ghi tác giả + link vào stock_credits.json (Pexels/Unsplash không bắt buộc ghi công nhưng nên ghi;
Unsplash yêu cầu gọi download_location — tool tự gọi). Video ưu tiên bản dọc gần 1080×1920 nhất.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, io, json, os, pathlib
import requests
from PIL import Image, ImageDraw

KIT = pathlib.Path(__file__).resolve().parent.parent

def key(name):
    if os.environ.get(name): return os.environ[name]
    for env in (pathlib.Path(".env"), KIT / ".env"):
        if env.exists():
            for ln in env.read_text(encoding="utf-8").splitlines():
                k, _, v = ln.partition("=")
                if k.strip() == name: return v.strip()
    cfg = KIT / "config.json"
    v = json.load(open(cfg, encoding="utf-8")).get(name.lower()) if cfg.exists() else None
    if v: return v
    raise SystemExit(f"Thiếu {name}: đặt biến môi trường hoặc ghi vào .env của dự án / kit/.env.")

def pexels(path, **params):
    r = requests.get(f"https://api.pexels.com/{path}", params=params, headers={"Authorization": key("PEXELS_API_KEY")}, timeout=30)
    r.raise_for_status(); return r.json()

def unsplash(path, **params):
    r = requests.get(f"https://api.unsplash.com/{path}", params=params,
                     headers={"Authorization": f"Client-ID {key('UNSPLASH_ACCESS_KEY')}"}, timeout=30)
    r.raise_for_status(); return r.json()

def best_video_file(v, w=1080, h=1920):
    files = [f for f in v["video_files"] if f.get("width") and f.get("height") and f["file_type"] == "video/mp4"]
    portrait = [f for f in files if f["height"] > f["width"]] or files
    # bản nhỏ nhất mà vẫn ≥ khung; không có thì lấy bản lớn nhất
    ok = [f for f in portrait if f["width"] >= w and f["height"] >= h]
    return min(ok, key=lambda f: f["width"] * f["height"]) if ok else max(portrait, key=lambda f: f["width"] * f["height"])

def search(a):
    items = []   # (id, thumb, mô tả)
    if a.source == "pexels" and a.type == "video":
        for v in pexels("videos/search", query=a.q, orientation=a.orientation, per_page=a.n, size="medium")["videos"]:
            f = best_video_file(v)
            items.append((f"pexels:video:{v['id']}", v["image"], f"{v['duration']}s {f['width']}x{f['height']} @{v['user']['name']} {v['url']}"))
    elif a.source == "pexels":
        for p in pexels("v1/search", query=a.q, orientation=a.orientation, per_page=a.n)["photos"]:
            items.append((f"pexels:photo:{p['id']}", p["src"]["medium"], f"{p['width']}x{p['height']} @{p['photographer']} {p['alt'][:60]}"))
    else:
        for p in unsplash("search/photos", query=a.q, orientation=a.orientation, per_page=a.n)["results"]:
            items.append((f"unsplash:photo:{p['id']}", p["urls"]["small"], f"{p['width']}x{p['height']} @{p['user']['name']} {(p.get('alt_description') or '')[:60]}"))
    for i, (iid, _, d) in enumerate(items): print(f"[{i}] {iid:<28} {d}")
    if not items: print("— không có kết quả"); return
    tw, th, cols = 240, 427, min(len(items), 6)
    sheet = Image.new("RGB", (cols * tw, -(-len(items) // cols) * th), "black"); dr = ImageDraw.Draw(sheet)
    for i, (_, url, _) in enumerate(items):
        try:
            im = Image.open(io.BytesIO(requests.get(url, timeout=30).content)).convert("RGB")
            im = im.resize((tw, int(im.height * tw / im.width))).crop((0, 0, tw, th))
            sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
        except Exception as e: print(f"  thumb [{i}] lỗi: {e}")
        x, y = (i % cols) * tw, (i // cols) * th
        dr.rectangle((x, y, x + 46, y + 34), fill="black"); dr.text((x + 8, y + 8), str(i), fill="yellow", font_size=22)
    sheet.save(a.sheet, quality=85); print("ảnh ghép:", a.sheet)

def get(a):
    src, typ, iid = a.id.split(":", 2)
    if src == "pexels" and typ == "video":
        v = pexels(f"videos/videos/{iid}"); f = best_video_file(v)
        url, credit = f["link"], {"author": v["user"]["name"], "page": v["url"], "size": f"{f['width']}x{f['height']}", "duration": v["duration"]}
    elif src == "pexels":
        p = pexels(f"v1/photos/{iid}")
        url, credit = p["src"]["original"], {"author": p["photographer"], "page": p["url"], "size": f"{p['width']}x{p['height']}"}
    else:
        p = unsplash(f"photos/{iid}")
        unsplash(p["links"]["download_location"].split("api.unsplash.com/", 1)[1])   # bắt buộc theo điều khoản Unsplash
        url = p["urls"]["raw"] + "&w=2160&fm=jpg&q=90"
        credit = {"author": p["user"]["name"], "page": p["links"]["html"], "size": f"{p['width']}x{p['height']}"}
    out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out, "wb") as fh:
            for chunk in r.iter_content(1 << 20): fh.write(chunk)
    log = pathlib.Path("stock_credits.json")
    rows = json.load(open(log, encoding="utf-8")) if log.exists() else {}
    rows[out.as_posix()] = {"source": src, "id": iid, **credit}
    json.dump(rows, open(log, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"đã tải {out} ({out.stat().st_size // 1024} KB) — {credit['author']} · {credit['page']}")

ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("search"); s.add_argument("q"); s.add_argument("--source", choices=["pexels", "unsplash"], default="pexels")
s.add_argument("--type", choices=["video", "photo"], default="video"); s.add_argument("-n", type=int, default=12)
s.add_argument("--orientation", default="portrait"); s.add_argument("--sheet", default="_stock_sheet.jpg")
g = sub.add_parser("get"); g.add_argument("id"); g.add_argument("out")
a = ap.parse_args()
if a.cmd == "search" and a.source == "unsplash" and a.type == "video": raise SystemExit("Unsplash chỉ có ảnh.")
search(a) if a.cmd == "search" else get(a)
