"""Dựng video từ kịch bản khai báo story.json bằng engine của screendemo.

Chuyển đổi story.json thành các lệnh gọi chính xác của Story API:
- screen(rec, r0, r1, items, badge, tail, start_zoomed, fade)
- logo_end, card, ...
- add_sfx, add_sticker
- finish(title, bgm, bgm_volume) và tinh chỉnh cues.json

Dùng:
  python screendemo/story_json.py <thư mục clip> [--variant full] [--emit-py]
"""
import argparse
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parent
sys.path.insert(0, str(HERE))
import engine
from engine import Story
import blocks as B


def resolve_sfx_path(proj_dir: pathlib.Path, ref: str) -> str:
    """Tìm đường dẫn file SFX từ tên ngắn hoặc đường dẫn tương đối."""
    if not ref:
        return ""
    if str(ref).startswith("meme:"):
        return ref
    p = pathlib.Path(ref)
    if p.is_absolute() and p.exists():
        return str(p)
    candidates = [
        proj_dir / ref,
        proj_dir / "assets" / "src" / ref,
        proj_dir / "assets" / "src" / f"sfx-{ref}.mp3",
        proj_dir / "assets" / "src" / f"{ref}.mp3",
        KIT / "audio-library" / ref,
        KIT / "audio-library" / "sfx" / ref,
    ]
    for c in candidates:
        if c.exists():
            return str(c.resolve())
    return str((proj_dir / ref).resolve())


def build(proj_dir, variant=None, story_file="story.json", emit_py=True) -> float:
    """Đọc story.json và thực thi toàn bộ luồng dựng video qua Story API."""
    proj = pathlib.Path(proj_dir).resolve()
    s_path = proj / story_file
    if not s_path.exists():
        raise FileNotFoundError(f"Không tìm thấy {s_path}")

    story_data = json.loads(s_path.read_text(encoding="utf-8"))

    # Đọc cấu hình clip.json nếu có
    clip_cfg = {}
    clip_json = proj / "clip.json"
    if clip_json.exists():
        try:
            clip_cfg = json.loads(clip_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    brand = clip_cfg.get("brand", {})
    if "brand" in story_data:
        brand.update(story_data["brand"])

    var_name = variant or os.environ.get("VARIANT") or "full"

    # Cập nhật SFX mặc định nếu có khai báo
    sfx_defs = story_data.get("sfx_defaults", {})
    src_dir = proj / "assets" / "src"
    default_whoosh = resolve_sfx_path(proj, sfx_defs.get("whoosh", "whoosh"))
    default_pop = resolve_sfx_path(proj, sfx_defs.get("pop", "pop"))
    default_ink = resolve_sfx_path(proj, sfx_defs.get("ink", sfx_defs.get("ping", "ping")))

    if (src_dir / "sfx-whoosh.mp3").exists():
        engine.SFX["whoosh"] = str(src_dir / "sfx-whoosh.mp3")
    elif default_whoosh:
        engine.SFX["whoosh"] = default_whoosh

    if (src_dir / "sfx-pop.mp3").exists():
        engine.SFX["pop"] = str(src_dir / "sfx-pop.mp3")
    elif default_pop:
        engine.SFX["pop"] = default_pop

    if (src_dir / "sfx-ping.mp3").exists():
        engine.SFX["ink"] = str(src_dir / "sfx-ping.mp3")
    elif (src_dir / "sfx-ink.mp3").exists():
        engine.SFX["ink"] = str(src_dir / "sfx-ink.mp3")
    elif default_ink:
        engine.SFX["ink"] = default_ink

    st = Story(proj, variant=var_name, brand=brand, layout=story_data.get("layout"))

    def resolve_time(at_val):
        if isinstance(at_val, (int, float)):
            return float(at_val)
        if isinstance(at_val, dict):
            if "line" in at_val:
                line = at_val["line"]
                chunk = at_val.get("chunk", 0)
                offset = at_val.get("offset", 0.0)
                return st.chunk_onset(line, chunk) + offset
            if "last" in at_val:
                return st.last + at_val["last"]
            if "now" in at_val:
                return st.now + at_val["now"]
        raise ValueError(f"Không thể giải quyết mốc thời gian: {at_val}")

    def apply_sfx_list(sfx_list):
        for s in sfx_list or []:
            t = resolve_time(s["at"])
            f = resolve_sfx_path(proj, s.get("file") or s.get("name", ""))
            vol = s.get("vol", s.get("volume", 0.5))
            dur = s.get("dur")
            st.add_sfx(t, f, volume=vol, dur=dur)

    def apply_sticker_list(stk_list):
        for stk in stk_list or []:
            t = resolve_time(stk["at"])
            dur = stk.get("dur", 2.4)
            pos = {k: stk[k] for k in ("x", "y", "w") if k in stk}
            st.add_sticker(stk["id"], t, dur=dur, **pos)

    # Duyệt qua các cảnh
    for scene in story_data.get("scenes", []):
        stype = scene.get("type", "screen")
        if stype == "screen":
            items = []
            for it in scene.get("items", []):
                if it.get("k") == "K":
                    at_spec = it["at"]
                    if isinstance(at_spec, list):
                        at_spec = tuple(at_spec)
                    items.append(st.Kf(it["chunk"], at_spec))
                else:
                    at_spec = it.get("at")
                    if isinstance(at_spec, list):
                        at_spec = tuple(at_spec)
                    items.append(
                        st.P(
                            it["line"],
                            it["i"],
                            it["j"],
                            at=at_spec,
                            lead=it.get("lead", 0.0),
                            hint=it.get("hint", 1.0),
                            meme=it.get("meme"),
                            after=it.get("after"),
                        )
                    )

            r0 = tuple(scene["r0"]) if isinstance(scene["r0"], list) else scene["r0"]
            r1 = tuple(scene["r1"]) if isinstance(scene["r1"], list) else scene["r1"]

            st.screen(
                rec=scene["rec"],
                r0=r0,
                r1=r1,
                items=items,
                badge=scene.get("badge", ""),
                tail=scene.get("tail", 0.6),
                tail_hint=scene.get("tail_hint", 1.0),
                pre=scene.get("pre", 0.35),
                start_zoomed=scene.get("start_zoomed", False),
                fade=scene.get("fade", True),
            )
            apply_sfx_list(scene.get("sfx"))
            apply_sticker_list(scene.get("stickers"))

        elif stype == "logo_end":
            item = scene.get("item", {})
            p_item = st.P(item["line"], item["i"], item["j"])
            name = scene.get("name") or brand.get("name", "StradeVn")
            tagline = scene.get("tagline") or brand.get("tagline", "")
            url = scene.get("url") or brand.get("url", "")
            logo = scene.get("logo", "assets/logo.jpg")

            B.logo_end(st, p_item, name, tagline, url, logo=logo)
            apply_sfx_list(scene.get("sfx"))
            apply_sticker_list(scene.get("stickers"))

        elif stype == "card":
            items = [
                st.P(it["line"], it["i"], it["j"], after=it.get("after"))
                for it in scene.get("items", [])
            ]
            st.card(
                items=items,
                body=scene.get("body", ""),
                tail=scene.get("tail", 0.35),
                pre=scene.get("pre", 0.15),
                cls=scene.get("cls", ""),
                min_dur=scene.get("min_dur", 0),
            )
            apply_sfx_list(scene.get("sfx"))
            apply_sticker_list(scene.get("stickers"))

        elif stype == "question":
            item = scene.get("item", {})
            p_item = st.P(item["line"], item["i"], item["j"])
            B.question(st, p_item, scene.get("q1", ""), scene.get("q2", ""), sticker=scene.get("sticker", "thinking"))
            apply_sfx_list(scene.get("sfx"))
            apply_sticker_list(scene.get("stickers"))

        elif stype == "clock":
            item = scene.get("item", {})
            p_item = st.P(item["line"], item["i"], item["j"])
            B.clock(st, p_item, scene.get("clock_text", ""), scene.get("title", ""), scene.get("sub", ""))
            apply_sfx_list(scene.get("sfx"))
            apply_sticker_list(scene.get("stickers"))

        elif stype == "timeskip":
            item = scene.get("item", {})
            p_item = st.P(item["line"], item["i"], item["j"])
            B.timeskip(st, p_item, scene.get("big", ""), scene.get("sub", ""))
            apply_sfx_list(scene.get("sfx"))
            apply_sticker_list(scene.get("stickers"))

    # Các SFX / sticker cấp toàn cục
    apply_sfx_list(story_data.get("sfx"))
    apply_sticker_list(story_data.get("stickers"))

    # BGM và kết thúc
    bgm_info = story_data.get("bgm", {})
    bgm_file = resolve_sfx_path(proj, bgm_info.get("file", "bgm/mixkit/house-vibez.mp3"))
    bgm_vol = bgm_info.get("volume", 0.14)
    title = story_data.get("title") or clip_cfg.get("title") or clip_cfg.get("slug", "Video")

    dur = st.finish(title=title, bgm=bgm_file, bgm_volume=bgm_vol)

    # Xử lý fade và loop cho cues.json
    cues_file = st.out / "cues.json"
    if cues_file.exists():
        try:
            c = json.loads(cues_file.read_text(encoding="utf-8"))
            if isinstance(c.get("bgm"), dict):
                fade_in = bgm_info.get("fade_in")
                fade_out = bgm_info.get("fade_out")
                if bgm_info.get("loop"):
                    fade_in = fade_in if fade_in is not None else 0.05
                    fade_out = fade_out if fade_out is not None else 0.15
                if fade_in is not None:
                    c["bgm"]["fade_in"] = fade_in
                if fade_out is not None:
                    c["bgm"]["fade_out"] = fade_out
                cues_file.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as e:
            print(f"  ⚠ cập nhật cues.json: {e}", file=sys.stderr)

    # Tạo story.py chuẩn để produce.py thực thi mượt mà
    if emit_py:
        py_file = proj / "story.py"
        py_content = (
            '"""Tự động sinh bởi screendemo/story_json.py từ story.json."""\n'
            "import os, pathlib, sys\n"
            "HERE = pathlib.Path(__file__).resolve().parent\n"
            'KIT = pathlib.Path((HERE / ".videokit").read_text(encoding="utf-8").strip()).parent\n'
            'sys.path.insert(0, str(KIT / "screendemo"))\n'
            "from story_json import build\n\n"
            'if __name__ == "__main__":\n'
            "    build(HERE)\n"
        )
        py_file.write_text(py_content, encoding="utf-8")

    return dur


def main():
    parser = argparse.ArgumentParser(description="Build screendemo from story.json")
    parser.add_argument("clip_dir", help="Thư mục clip chứa story.json")
    parser.add_argument("--variant", default="full", help="Tên bản dựng (mặc định: full)")
    parser.add_argument("--no-emit-py", action="store_true", help="Không tạo lại file story.py")
    args = parser.parse_args()

    dur = build(args.clip_dir, variant=args.variant, emit_py=not args.no_emit_py)
    print(f"✅ Hoàn tất build story.json: {dur:.2f}s")


if __name__ == "__main__":
    main()
