"""Check built timeline duration against max seconds limit."""
from __future__ import annotations

import re
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="build", name="duration")
def check_duration(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    max_seconds = ctx.rules.get("max_seconds", 115)

    duration = None
    if ctx.cues_json.get("duration"):
        try:
            duration = float(ctx.cues_json["duration"])
        except Exception:
            pass

    if duration is None and ctx.index_html:
        m = re.search(r'id="root"[^>]*data-duration="([^"]+)"', ctx.index_html)
        if m:
            try:
                duration = float(m.group(1))
            except Exception:
                pass

    if duration is not None:
        if duration >= max_seconds:
            issues.append(
                Issue(
                    check="duration",
                    where="index.html / cues.json duration",
                    msg=f"Thời lượng bản dựng ({duration:.2f}s) vượt quá giới hạn tối đa ({max_seconds}s)",
                    fix_hint=f"Cắt bớt câu hoặc tăng tốc độ phát video bản quay để thời lượng dưới {max_seconds}s.",
                )
            )

    return issues
