"""Đóng gói bộ công cụ thành 1 file zip để mang sang máy / dự án khác.

Dùng: python kit/tools/make_package.py [--no-example]
Ra:   dist/marketing-video-kit-YYYYMMDD.zip
Luôn LOẠI: config.json (đường dẫn key riêng máy), __pycache__, file tạm _snap_/_sheet_, bản render trung gian.
--no-example: bỏ thư mục examples/ (nhẹ hơn ~90 MB).
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import sys, zipfile, datetime, pathlib
KIT = pathlib.Path(__file__).resolve().parent.parent
out_dir = KIT.parent / "dist"; out_dir.mkdir(exist_ok=True)
out = out_dir / f"marketing-video-kit-{datetime.date.today():%Y%m%d}{'-lite' if '--no-example' in sys.argv else ''}.zip"
skip_example = "--no-example" in sys.argv
n = size = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(KIT.rglob("*")):
        rel = p.relative_to(KIT)
        if p.is_dir(): continue
        if rel.name == "config.json" or "__pycache__" in rel.parts: continue
        if rel.name.startswith(("_snap_", "_sheet", "_check", "_final", "_c", "_v")): continue
        if skip_example and rel.parts[0] == "examples": continue
        z.write(p, pathlib.Path("marketing-video-kit") / rel); n += 1; size += p.stat().st_size
print(f"xong: {out}  ({n} file, {size/1e6:.0f} MB trước nén, {out.stat().st_size/1e6:.0f} MB sau nén)")
