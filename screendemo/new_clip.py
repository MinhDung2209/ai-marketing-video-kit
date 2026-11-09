"""Tạo clip demo sản phẩm mới từ mẫu thể loại của 1 doanh nghiệp.

  python KIT/screendemo/new_clip.py --list                                   # doanh nghiệp + thể loại đang có
  python KIT/screendemo/new_clip.py <thư mục clip> --profile stradevn --genre ma-hs [--slug 02-thanh-long-081040]

Chép: shots.json (kịch bản thao tác) · story.py (kịch bản dựng) · clip.json (biến + chữ trên thẻ) · voice.json (lời mẫu)
+ fonts, logo, sticker cần dùng. Sau đó làm theo KIT/docs/12-video-demo-san-pham.md (bảng "Clip mới trong 8 bước")."""
import argparse, json, pathlib, re, shutil, sys
HERE = pathlib.Path(__file__).resolve().parent; KIT = HERE.parent
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dst", nargs="?"); ap.add_argument("--profile"); ap.add_argument("--genre")
    ap.add_argument("--slug"); ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    P = KIT / "profiles"
    if a.list or not a.dst:
        for p in sorted(P.iterdir()):
            if not p.is_dir(): continue
            prof = json.loads((p / "profile.json").read_text(encoding="utf-8")) if (p / "profile.json").exists() else {}
            gs = [g.name for g in (p / "genres").iterdir()] if (p / "genres").exists() else []
            print(f"{p.name:12s} {prof.get('name', ''):28s} thể loại: {', '.join(gs) or '—'}")
        return
    if not (a.profile and a.genre): raise SystemExit("cần --profile và --genre (xem --list)")
    src = P / a.profile / "genres" / a.genre
    if not src.exists(): raise SystemExit(f"không có {src}")
    dst = pathlib.Path(a.dst).resolve()
    if dst.exists() and any(dst.iterdir()): raise SystemExit(f"thư mục đã có nội dung: {dst}")
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.is_file(): shutil.copy2(f, dst / f.name)
    tpl = KIT / "templates" / "video-project"
    shutil.copy2(tpl / "fonts.css.part", dst / "fonts.css.part")
    shutil.copytree(KIT / "templates" / "fonts", dst / "assets" / "fonts", dirs_exist_ok=True)
    prof = json.loads((P / a.profile / "profile.json").read_text(encoding="utf-8"))
    logo = prof.get("brand", {}).get("logo")
    if logo and (P / a.profile / logo).exists(): shutil.copy2(P / a.profile / logo, dst / "assets" / ("logo" + pathlib.Path(logo).suffix))
    # sticker: mọi meme="…" trong story.py + mặc định của blocks (thinking, point-down)
    ids = set(re.findall(r'meme="([\w-]+)"', (dst / "story.py").read_text(encoding="utf-8"))) | {"thinking", "point-down"}
    md = dst / "assets" / "meme"; md.mkdir(parents=True, exist_ok=True)
    for i in sorted(ids):
        for ext in (".webm", ".png"):
            f = KIT / "meme-library" / "noto" / f"{i}{ext}"
            if f.exists(): shutil.copy2(f, md / f.name)
    (dst / ".videokit").write_text(str(KIT / "tools"), encoding="utf-8")
    c = json.loads((dst / "clip.json").read_text(encoding="utf-8"))
    c["slug"] = a.slug or dst.name; c["profile"] = a.profile; c["genre"] = a.genre
    c.setdefault("brand", {k: v for k, v in prof.get("brand", {}).items() if k != "logo"})
    c["variants"] = {k: v["suffix"] for k, v in prof.get("variants", {"full": {"suffix": "full"}}).items()}
    (dst / "clip.json").write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")
    print("đã tạo:", dst)
    print("bước tiếp: sửa clip.json (vars + story) và voice.json theo mặt hàng mới → xem KIT/docs/12-video-demo-san-pham.md")


if __name__ == "__main__":
    main()
