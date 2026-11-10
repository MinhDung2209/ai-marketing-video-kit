"""Check that ink marks per scene do not exceed threshold (avoid mark spam)."""
from __future__ import annotations

from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="shots", name="ink_marks")
def check_ink_marks(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    max_ink = ctx.rules.get("marks", {}).get("max_ink_per_scene", 2)

    screen_dir = ctx.clip_dir / "assets" / "screen"
    if not screen_dir.is_dir():
        return issues

    for shot_dir in screen_dir.iterdir():
        if not shot_dir.is_dir() or shot_dir.name.startswith(("_", ".")):
            continue
        shot_id = shot_dir.name
        marks = ctx.get_shot_marks(shot_id)

        # Count marks that drew ink (has box and ink is not False)
        ink_marks = [
            m for m in marks
            if "box" in m and m.get("ink", True) is not False
        ]

        if len(ink_marks) > max_ink:
            issues.append(
                Issue(
                    check="ink_marks",
                    where=f"assets/screen/{shot_id}",
                    msg=f"Bản quay {shot_id} có {len(ink_marks)} lần khoanh mực (vượt mức tối đa {max_ink} lần/cảnh — mark quá dày bị coi là spam)",
                    fix_hint=f"Giảm số lần khoanh mực xuống ≤ {max_ink}; các chỗ khác chuyển sang dùng focus() để camera chỉ lướt tới mà không vẽ mực.",
                )
            )

    return issues
