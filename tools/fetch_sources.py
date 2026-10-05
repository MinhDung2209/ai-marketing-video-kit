"""(Hiếm khi cần) Tải lại các repo nguồn âm thanh rồi dựng lại audio-library + catalog.json.

Toàn bộ thư viện âm thanh ĐÃ nằm sẵn trong git của kit → máy mới clone về là đủ, KHÔNG cần chạy lệnh này.
Chỉ dùng khi muốn cập nhật từ nguồn gốc (repo nguồn có thể đã đổi / biến mất — uisfx đã 404 từ 10/2026).

Dùng: python tools/fetch_sources.py [--repos ../_repos]
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, pathlib, subprocess, sys

KIT = pathlib.Path(__file__).resolve().parent.parent
# tên thư mục, URL, commit đã kiểm (xem THIRD-PARTY.md), thư mục cần lấy
# Chỉ tải đúng thư mục âm thanh (sparse checkout): nhẹ, và tránh lỗi "Filename too long" trên Windows
SOURCES = [
    ("hyperframes", "https://github.com/heygen-com/hyperframes.git", "9a27b9f", "skills/media-use/audio/assets/sfx"),
    ("video-shotcraft", "https://github.com/Vincentwei1021/video-shotcraft.git", "5ddbf52", "assets/audio"),
]
# uisfx (CC0) KHÔNG tải: repo gốc github.com/899ms/uisfx đã 404 từ 10/2026 — 936 file nằm sẵn trong git của kit
# (audio-library/sfx/uisfx/, kèm LICENSE-AUDIO gốc).

ap = argparse.ArgumentParser()
ap.add_argument("--repos", default=str(KIT.parent / "_repos"), help="nơi clone (mặc định: cạnh thư mục kit)")
a = ap.parse_args()
R = pathlib.Path(a.repos); R.mkdir(parents=True, exist_ok=True)

def git(d, *args, check=True):
    return subprocess.run(["git", "-C", str(d), "-c", "core.longpaths=true", "-c", "advice.detachedHead=false", *args], check=check)

for name, url, commit, folder in SOURCES:
    d = R / name
    if not (d / ".git").exists():
        print(f"clone {name} (chỉ {folder}) …")
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", url, str(d)], check=True)
        git(d, "sparse-checkout", "set", "--no-cone", folder)
    git(d, "fetch", "-q", "origin", check=False)
    git(d, "checkout", "-q", commit)
    print(f"✅ {name} @ {commit}")

subprocess.run([sys.executable, str(KIT / "tools" / "build_library.py"), "--repos", str(R),
                "--out", str(KIT / "audio-library")], check=True)
