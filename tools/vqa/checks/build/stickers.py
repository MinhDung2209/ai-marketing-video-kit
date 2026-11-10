"""Check sticker pacing (none in first 3s, at most 1 per 10s)."""
from __future__ import annotations

import re
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="build", name="stickers")
def check_stickers(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    stk_rules = ctx.rules.get("stickers", {})
    min_spacing = float(stk_rules.get("min_spacing_seconds", 10.0))
    none_before = float(stk_rules.get("none_before_seconds", 3.0))

    sticker_times: List[float] = []

    # 1. Parse from story.py if available
    story_py = ctx.clip_dir / "story.py"
    if story_py.exists():
        try:
            content = story_py.read_text(encoding="utf-8")
            # Matches st.add_sticker("name", time, ...)
            matches = re.findall(r'add_sticker\([^,]+,\s*([^,\)]+)', content)
            for m in matches:
                m_str = m.strip()
                try:
                    sticker_times.append(float(m_str))
                except ValueError:
                    # expression like st.last + 0.1
                    pass
        except Exception:
            pass

    # 2. Parse from index.html if available
    if not sticker_times and ctx.index_html:
        # Matches elements with class stk or data-start
        stk_re = re.compile(r'class="[^"]*stk[^"]*"[^>]*data-start="([^"]+)"')
        for match in stk_re.finditer(ctx.index_html):
            try:
                sticker_times.append(float(match.group(1)))
            except ValueError:
                pass

    # 3. Check assets/meme usage in index.html
    if not sticker_times and ctx.index_html:
        meme_re = re.compile(r'assets/meme/([^"\'>]+)')
        for match in meme_re.finditer(ctx.index_html):
            # Check enclosing section or element data-start
            pass

    sticker_times.sort()

    # 1. None in first 3s
    for t in sticker_times:
        if t < none_before:
            issues.append(
                Issue(
                    check="stickers",
                    where=f"story.py / index.html sticker at {t:.2f}s",
                    msg=f"Sticker/meme xuất hiện quá sớm ở giây {t:.2f} (< {none_before}s đầu video)",
                    fix_hint=f"Không đặt meme/sticker ở cảnh 1 ({none_before}s đầu); dời sticker sang các cảnh sau khi đã trình bày giải pháp.",
                )
            )

    # 2. Spacing between consecutive stickers
    for i in range(1, len(sticker_times)):
        diff = sticker_times[i] - sticker_times[i - 1]
        if diff < min_spacing:
            issues.append(
                Issue(
                    check="stickers",
                    where=f"story.py / index.html stickers at {sticker_times[i-1]:.2f}s and {sticker_times[i]:.2f}s",
                    msg=f"Khoảng cách giữa 2 sticker quá dày ({diff:.1f}s < {min_spacing}s yêu cầu)",
                    fix_hint=f"Giãn khoảng cách giữa các sticker (tối thiểu 1 sticker mỗi {min_spacing}s, toàn bài chỉ nên 1-2 meme).",
                )
            )

    return issues
