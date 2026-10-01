"""Cài skill marketing-video cho Claude Code, tự điền đường dẫn KIT (không phải sửa tay).

Dùng:
  python tools/install_skill.py                    # cài cho mọi dự án: ~/.claude/skills/marketing-video/
  python tools/install_skill.py --project <thư mục> # chỉ cho 1 dự án: <thư mục>/.claude/skills/marketing-video/
Chạy lại sau khi git pull để cập nhật skill.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, pathlib

KIT = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--project", help="cài vào .claude/skills của dự án này thay vì thư mục người dùng")
a = ap.parse_args()

base = pathlib.Path(a.project).resolve() if a.project else pathlib.Path.home()
dst = base / ".claude" / "skills" / "marketing-video"
dst.mkdir(parents=True, exist_ok=True)
src = (KIT / "skills" / "marketing-video" / "SKILL.md").read_text(encoding="utf-8")
line = next(l for l in src.splitlines() if l.startswith("KIT = "))
src = src.replace(line, f"KIT = `{KIT.as_posix()}`   ← do tools/install_skill.py điền; chuyển kit đi chỗ khác thì chạy lại."
                        f" Tài liệu đầy đủ: `KIT/docs/00..10`. Ví dụ thật: `KIT/examples/stradevn-ad-v2/`.")
(dst / "SKILL.md").write_text(src, encoding="utf-8")
print(f"✅ đã cài skill: {dst / 'SKILL.md'}\n   KIT = {KIT.as_posix()}\n   Mở Claude Code và nói: \"làm video marketing cho …\"")
