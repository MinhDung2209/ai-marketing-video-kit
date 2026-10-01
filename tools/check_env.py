"""Kiểm máy đã đủ đồ nghề chạy kit chưa — chạy đầu tiên trên máy mới.

Dùng: python tools/check_env.py
In ✅ / ❌ từng mục kèm cách sửa. Thoát mã 1 nếu thiếu thứ bắt buộc.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import importlib, json, os, pathlib, shutil, subprocess, sys

KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "tools"))
bad = 0

def show(ok, name, detail="", fix="", required=True):
    global bad
    mark = "✅" if ok else ("❌" if required else "⚠️ ")
    print(f"{mark} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        if fix: print(f"     → {fix}")
        if required: bad += 1

# 1. Python
show(sys.version_info >= (3, 11), "Python ≥ 3.11", sys.version.split()[0], "cài Python mới ở python.org")

# 2. Thư viện Python
for mod, pkg in [("google.auth", "google-auth"), ("requests", "requests"), ("PIL", "pillow"), ("playwright", "playwright")]:
    try:
        importlib.import_module(mod); show(True, f"pip: {pkg}")
    except ImportError:
        show(False, f"pip: {pkg}", "chưa cài", "pip install -r requirements.txt")

# 3. FFmpeg + ffprobe (+ bộ mã hoá cần cho MP4)
for exe in ("ffmpeg", "ffprobe"):
    p = shutil.which(exe)
    ver = subprocess.run([exe, "-version"], capture_output=True, text=True).stdout.split("\n")[0][:60] if p else ""
    show(bool(p), exe, ver or "không thấy trong PATH",
         "Windows: winget install Gyan.FFmpeg · macOS: brew install ffmpeg · Ubuntu: sudo apt install ffmpeg (mở lại cửa sổ lệnh)")
if shutil.which("ffmpeg"):
    enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    show("libx264" in enc and " aac " in enc, "ffmpeg có libx264 + aac", "", "cài bản FFmpeg 'full' (không phải bản essentials/lgpl)")

# 4. Chrome
try:
    from render import find_chrome
    c = find_chrome()
    show(True, "Chrome/Chromium", c or "dùng Chromium của Playwright")
except Exception as e:
    show(False, "Chrome/Chromium", str(e)[:120])

# 5. Key Google Cloud
try:
    from gcp import key_path
    k = key_path()   # thiếu key thì hàm này raise SystemExit
    show(True, "Key Google Cloud (TTS + Lyria)", k)
except BaseException as e:
    show(False, "Key Google Cloud (TTS + Lyria)", str(e)[:120], "cp config.example.json config.json rồi sửa gcp_key_path")

# 6. Thư viện âm thanh
cat = KIT / "audio-library" / "catalog.json"
if cat.exists():
    items = json.load(open(cat, encoding="utf-8"))
    missing = [i["path"] for i in items if not (KIT / "audio-library" / i["path"]).exists()]
    show(not missing, "Thư viện âm thanh", f"{len(items) - len(missing)}/{len(items)} file",
         "python tools/fetch_sources.py  (tải lại phần Pixabay/Mixkit — không lưu trong git vì giấy phép)")
else:
    show(False, "Thư viện âm thanh", "thiếu catalog.json", "python tools/fetch_sources.py")

# 7. Tuỳ chọn
show(bool(shutil.which("git")), "git", "", "cần cho tools/fetch_sources.py", required=False)
show(bool(shutil.which("node")), "Node.js", "", "chỉ cần nếu dùng npx hyperframes", required=False)

print("\n" + ("Đủ rồi — đọc tiếp docs/02-quy-trinh-tung-buoc.md" if not bad else f"Thiếu {bad} mục bắt buộc — sửa theo dòng →"))
sys.exit(1 if bad else 0)
