"""Check voice profile and line directions."""
from __future__ import annotations

from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="brief", name="profile_direction")
def check_profile_direction(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    profile = ctx.voice_json.get("profile", "")

    # 1. Check profile length (>= 40 words)
    words = profile.strip().split()
    if len(words) < 40:
        issues.append(
            Issue(
                check="profile_direction",
                where="voice.json 'profile'",
                msg=f"Profile giọng quá ngắn ({len(words)} từ < 40 từ yêu cầu)",
                fix_hint="Mô tả kỹ profile giọng đọc (≥ 40 từ): chân dung nhân vật (persona), năng lượng (energy), giọng vùng miền (accent), bối cảnh (scene) và phát âm thương hiệu.",
            )
        )

    # 2. Check each line has its own direction
    lines = ctx.voice_json.get("lines", [])
    prev_dir = None
    for idx, line in enumerate(lines):
        lid = line.get("id", f"V{idx + 1}")
        d = str(line.get("direction", "")).strip()
        if not d:
            issues.append(
                Issue(
                    check="profile_direction",
                    where=f"voice.json line {lid}",
                    msg=f"Câu thoại {lid} thiếu hướng dẫn sắc thái ('direction')",
                    fix_hint=f"Thêm trường 'direction' mô tả nhịp điệu và cảm xúc riêng cho câu {lid}.",
                )
            )
            continue

        if prev_dir is not None and d.lower() == prev_dir.lower():
            issues.append(
                Issue(
                    check="profile_direction",
                    where=f"voice.json line {lid}",
                    msg=f"Hướng dẫn sắc thái ('direction') của câu {lid} bị sao chép y hệt câu trước",
                    fix_hint=f"Viết lại 'direction' cho câu {lid} để phản ánh diễn biến tâm lý riêng của cảnh đó.",
                )
            )
        prev_dir = d

    # 3. Hook and CTA must differ
    if len(lines) >= 2:
        hook_dir = str(lines[0].get("direction", "")).strip().lower()
        cta_dir = str(lines[-1].get("direction", "")).strip().lower()
        if hook_dir and cta_dir and hook_dir == cta_dir:
            issues.append(
                Issue(
                    check="profile_direction",
                    where=f"voice.json hook ({lines[0].get('id')}) / CTA ({lines[-1].get('id')})",
                    msg="Hướng dẫn sắc thái của câu mở đầu (hook) và câu kết (CTA) giống nhau",
                    fix_hint="Hook cần dồn dập, tò mò; CTA cần ấm áp, mời gọi hoặc lửng lơ nối vòng.",
                )
            )

    return issues
