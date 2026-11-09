"""Cài skill của kit cho Claude Code, tự điền đường dẫn KIT (không phải sửa tay).

Dùng:
  python tools/install_skill.py                    # cài cho mọi dự án: ~/.claude/skills/<skill>/
  python tools/install_skill.py --project <thư mục> # chỉ cho 1 dự án: <thư mục>/.claude/skills/<skill>/
  python tools/install_skill.py --skill news-explainer   # chỉ 1 skill
Skill: marketing-video (video quảng cáo AI) · product-demo-video (video demo sản phẩm quay màn hình thật) ·
news-explainer (tin tức: bắt trend, tin nóng, giải thích WHY, tường thuật clip).
Chạy lại sau khi git pull để cập nhật skill.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, pathlib, shutil

KIT = pathlib.Path(__file__).resolve().parent.parent
K = KIT.as_posix()
SKILLS = {"marketing-video": "Tài liệu đầy đủ: `KIT/docs/00..11`. Ví dụ thật: `KIT/examples/stradevn-ad-v2/`.",
          "product-demo-video": "Tài liệu: `KIT/docs/12-video-demo-san-pham.md`. Hồ sơ doanh nghiệp: `KIT/profiles/`.",
          "news-explainer": "Lịch + giọng kênh: `KIT/newsroom/`. Dựng: `KIT/tools/news_video.py`."}
ap = argparse.ArgumentParser()
ap.add_argument("--project", help="cài vào .claude/skills của dự án này thay vì thư mục người dùng")
ap.add_argument("--skill", choices=list(SKILLS), help="chỉ cài 1 skill (mặc định: tất cả)")
a = ap.parse_args()

base = pathlib.Path(a.project).resolve() if a.project else pathlib.Path.home()
for name, tail in SKILLS.items():
    if a.skill and name != a.skill: continue
    src_dir = KIT / "skills" / name; dst = base / ".claude" / "skills" / name
    dst.mkdir(parents=True, exist_ok=True)
    for sub in src_dir.iterdir():                     # tài liệu kèm skill (references/, examples/…)
        if sub.is_dir(): shutil.copytree(sub, dst / sub.name, dirs_exist_ok=True)
    src = (src_dir / "SKILL.md").read_text(encoding="utf-8")
    kit_line = f"KIT = `{K}`   ← do tools/install_skill.py điền; chuyển kit đi chỗ khác thì chạy lại. {tail}"
    line = next((l for l in src.splitlines() if l.startswith("KIT = ")), None)
    if line: src = src.replace(line, kit_line)
    else:                                              # skill viết đường dẫn tương đối → chèn KIT ngay dưới tiêu đề
        head, sep, rest = src.partition("\n# "); title, _, body = rest.partition("\n")
        src = head + sep + title + "\n\n" + kit_line + "\n" + body
    src = src.replace("<kit>", K).replace("`../../", f"`{K}/").replace("Kit root là thư mục hai cấp trên skill.", f"Kit root: `{K}`.")
    (dst / "SKILL.md").write_text(src, encoding="utf-8")
    print(f"✅ đã cài skill: {dst / 'SKILL.md'}")
print(f"   KIT = {K}\n   Mở Claude Code và nói: \"làm video marketing cho …\" · \"làm video demo sản phẩm …\" · \"hôm nay có tin gì hot\"")
