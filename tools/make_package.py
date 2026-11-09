"""Đóng gói bộ công cụ thành 1 file zip để mang sang máy / dự án khác.

Dùng: python kit/tools/make_package.py [--no-example]
Ra:   dist/marketing-video-kit-YYYYMMDD.zip  (dist/ nằm cạnh thư mục kit)
Chỉ lấy file thuộc kit theo git (đã commit + file mới chưa bị .gitignore loại) → tự LOẠI .venv, .git, config.json,
token YouTube, profile trình duyệt mạng xã hội, _repos/, số đo radar, file tạm. Máy không có git → báo lỗi, không đoán.
--no-example: bỏ thư mục examples/ (nhẹ hơn ~90 MB).
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import sys, subprocess, zipfile, datetime, pathlib
KIT = pathlib.Path(__file__).resolve().parent.parent
out_dir = KIT.parent / "dist"; out_dir.mkdir(exist_ok=True)
skip_example = "--no-example" in sys.argv
out = out_dir / f"marketing-video-kit-{datetime.date.today():%Y%m%d}{'-lite' if skip_example else ''}.zip"
try:
    ls = subprocess.run(["git", "-C", str(KIT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                        capture_output=True, check=True).stdout.decode("utf-8").split("\0")
except Exception as e:
    raise SystemExit(f"cần git để biết file nào thuộc kit: {e}")
SECRET = ("config.json", ".youtube_token.json")
n = size = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for r in sorted(set(x for x in ls if x)):
        p = KIT / r; rel = pathlib.Path(r)
        if not p.is_file(): continue                       # file đã xoá nhưng git còn ghi
        if rel.name in SECRET or rel.name.endswith(".key.json") or "__pycache__" in rel.parts: continue
        if rel.name.startswith(("_snap_", "_sheet", "_check", "_final")): continue
        if skip_example and rel.parts[0] == "examples": continue
        z.write(p, pathlib.Path("marketing-video-kit") / rel); n += 1; size += p.stat().st_size
print(f"xong: {out}  ({n} file, {size/1e6:.0f} MB trước nén, {out.stat().st_size/1e6:.0f} MB sau nén)")
