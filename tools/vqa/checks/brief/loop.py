"""Check seamless loop hook requirements."""
from __future__ import annotations

import re
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


def is_loop_clip(ctx: VQAContext) -> bool:
    c = ctx.clip_json
    if c.get("loop") is True:
        return True
    if "loop" in str(c.get("genre", "")).lower():
        return True
    if "loop" in str(c.get("title", "")).lower():
        return True
    if "loop" in str(c.get("_huong_dan", "")).lower():
        return True
    if "loop hook" in ctx.brief_md.lower() or "(loop)" in ctx.brief_md.lower():
        return True
    return False


@register_check(stage="brief", name="loop")
def check_loop_hook(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    if not is_loop_clip(ctx):
        return issues

    lines = ctx.voice_json.get("lines", [])
    if not lines:
        return issues

    # 1. Last voice line must end with ':' or lead into V1
    last_line = lines[-1]
    last_text = last_line.get("text", "").strip()
    # Strip trailing tags or spaces
    clean_last = re.sub(r"\[[^\]]*\]\s*$", "", last_text).strip()
    if not clean_last.endswith(":") and not clean_last.endswith("...") and not clean_last.endswith("…"):
        issues.append(
            Issue(
                check="loop",
                where=f"voice.json line {last_line.get('id')}",
                msg=f"Video loop nhưng câu thoại cuối không kết thúc bằng dấu ':' hoặc bỏ lửng để dẫn vào câu đầu: {clean_last!r}",
                fix_hint="Kết thúc câu thoại cuối bằng dấu ':' (vd: 'Như lô hàng này:') để nối tự nhiên vào câu đầu V1.",
            )
        )

    # 2. First and last scene must use the same rec + mark
    # Parse scenes from index.html or story.py
    first_rec = None
    last_rec = None
    first_mark = None
    last_mark = None

    story_py = ctx.clip_dir / "story.py"
    if story_py.exists():
        try:
            content = story_py.read_text(encoding="utf-8")
            screen_calls = re.findall(r'screen\(\s*[\'"](\w+)[\'"]\s*,\s*([^,\n]+)\s*,\s*([^,\n]+)', content)
            if screen_calls:
                first_rec = screen_calls[0][0]
                first_mark = screen_calls[0][1].strip()
                last_rec = screen_calls[-1][0]
                last_mark = screen_calls[-1][2].strip()
        except Exception:
            pass

    if not first_rec and ctx.index_html:
        # Fallback to index.html videos
        videos = re.findall(r'src="assets/screen/(\w+)/screen\.mp4"[^>]*data-offset="([^"]+)"[^>]*data-end="([^"]+)"', ctx.index_html)
        if videos:
            first_rec = videos[0][0]
            first_mark = videos[0][1]
            last_rec = videos[-1][0]
            last_mark = videos[-1][2]

    if first_rec and last_rec:
        if first_rec != last_rec:
            issues.append(
                Issue(
                    check="loop",
                    where="story.py / index.html (cảnh 1 & cảnh cuối)",
                    msg=f"Video loop nhưng cảnh đầu dùng bản quay {first_rec!r} còn cảnh cuối dùng {last_rec!r}",
                    fix_hint=f"Cảnh mở đầu và cảnh kết thúc nối vòng phải dùng cùng bản quay ({first_rec}) và cùng khung hình zoom sát.",
                )
            )

    return issues
