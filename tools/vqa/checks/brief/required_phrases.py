"""Check required phrases hint."""
from __future__ import annotations

from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="brief", name="required_phrases")
def check_required_phrases(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    required_phrases = ctx.rules.get("required_phrases", [])
    if not required_phrases:
        return issues

    # Collect all text in voice lines, captions, and badges
    corpus = []
    for line in ctx.voice_json.get("lines", []):
        corpus.append(line.get("text", ""))
        corpus.append(line.get("caption", ""))
    for b in ctx.get_badges():
        corpus.append(b.get("text", ""))
    full_text = " ".join(corpus).lower()

    for phrase in required_phrases:
        if phrase.lower() not in full_text:
            issues.append(
                Issue(
                    check="required_phrases",
                    where="voice.json / badges",
                    msg=f"Thiếu cụm từ định vị thương hiệu bắt buộc: {phrase!r}",
                    fix_hint=f"Thêm cụm từ {phrase!r} vào câu giới thiệu giải pháp (V2/rehook) hoặc badge cảnh 2.",
                    level="warning",
                )
            )

    return issues
