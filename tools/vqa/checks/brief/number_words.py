"""Check numbers in voice text are written as words, not digits."""
from __future__ import annotations

import re
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check

DIGIT_RE = re.compile(r"\b\d+([.,]\d+)?\b|\$\d+|\d+\$")


@register_check(stage="brief", name="number_words")
def check_number_words(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    lines = ctx.voice_json.get("lines", [])

    for line in lines:
        lid = line.get("id", "unknown")
        raw_text = line.get("text", "")
        # Remove bracketed tags like [short pause], [2s], etc.
        plain = re.sub(r"\[[^\]]*\]", " ", raw_text)

        matches = DIGIT_RE.findall(plain)
        # Also find all numeric tokens
        found = re.findall(r"\d[\d.,]*", plain)
        if found:
            issues.append(
                Issue(
                    check="number_words",
                    where=f"voice.json line {lid} 'text'",
                    msg=f"Lời đọc chứa chữ số thay vì chữ viết số: {', '.join(found)}",
                    fix_hint=f"Đổi chữ số trong 'text' thành chữ (vd: 24 → 'hai mươi tư', $6,64 → 'sáu phẩy sáu tư đô', 0904.11 → 'không chín không bốn, mười một'). Giữ chữ số trong 'caption'.",
                )
            )

    return issues
