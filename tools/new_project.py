"""Tạo dự án video mới từ khung mẫu kit/templates/video-project.

Dùng: python kit/tools/new_project.py <thư mục dự án mới>
Ví dụ: python kit/tools/new_project.py projects/cong-ty-abc/ad-v1
Sau đó làm theo kit/docs/02-quy-trinh-tung-buoc.md.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import shutil, sys, pathlib
KIT = pathlib.Path(__file__).resolve().parent.parent
dst = pathlib.Path(sys.argv[1]).resolve()
if dst.exists() and any(dst.iterdir()): raise SystemExit(f"Thư mục đã có nội dung: {dst}")
shutil.copytree(KIT / "templates" / "video-project", dst, dirs_exist_ok=True)
fonts = KIT / "templates" / "fonts"
if fonts.exists(): shutil.copytree(fonts, dst / "assets" / "fonts", dirs_exist_ok=True)
(dst / ".videokit").write_text(str(KIT / "tools"), encoding="utf-8")   # để build.py tìm được kit dù dự án nằm đâu
print("đã tạo:", dst, "\nBước tiếp: mở BRIEF.md (viết kịch bản) → voice.json (lời đọc) → xem kit/docs/02-quy-trinh-tung-buoc.md")
