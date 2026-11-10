"""Check forbidden phrases and emoji in badges."""
from __future__ import annotations

import re
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check

EMOJI_RE = re.compile(
    r"[\U0001F1E6-\U0001F1FF"  # flags
    r"\U0001F300-\U0001F5FF"  # symbols & pictographs
    r"\U0001F600-\U0001F64F"  # emoticons
    r"\U0001F680-\U0001F6FF"  # transport & map
    r"\U0001F700-\U0001F77F"
    r"\U0001F780-\U0001F7FF"
    r"\U0001F800-\U0001F8FF"
    r"\U0001F900-\U0001F9FF"  # supplemental symbols
    r"\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF"
    r"]",
    flags=re.UNICODE,
)


@register_check(stage="brief", name="forbidden_phrases")
def check_forbidden_phrases(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    forbidden_list = [p.lower() for p in ctx.rules.get("forbidden_phrases", [])]

    # 1. Check voice lines and captions
    lines = ctx.voice_json.get("lines", [])
    for line in lines:
        lid = line.get("id", "unknown")
        for field in ("text", "caption"):
            val = line.get(field, "")
            if not val:
                continue
            val_lower = val.lower()
            for phrase in forbidden_list:
                if phrase in val_lower:
                    issues.append(
                        Issue(
                            check="forbidden_phrases",
                            where=f"voice.json line {lid} ({field})",
                            msg=f"Chứa cụm từ bị cấm: {phrase!r}",
                            fix_hint=f"Thay thế cụm {phrase!r} bằng thuật ngữ được duyệt (vd: 'dữ liệu xuất nhập khẩu toàn cầu' thay vì 'tờ khai hải quan').",
                        )
                    )

    # 2. Check badges
    badges = ctx.get_badges()
    disallow_emoji = ctx.rules.get("disallow_emoji_in_badges", True)

    for b in badges:
        text = b.get("text", "")
        where = b.get("where", "badge")
        text_lower = text.lower()

        # Check forbidden phrases in badge
        for phrase in forbidden_list:
            if phrase in text_lower:
                issues.append(
                    Issue(
                        check="forbidden_phrases",
                        where=where,
                        msg=f"Thẻ tiêu đề (badge) chứa cụm từ bị cấm: {phrase!r}",
                        fix_hint=f"Bỏ hoặc thay thế cụm {phrase!r} trong thẻ tiêu đề cảnh.",
                    )
                )

        # Check emoji in badge
        if disallow_emoji:
            emojis = EMOJI_RE.findall(text)
            if emojis:
                issues.append(
                    Issue(
                        check="forbidden_phrases",
                        where=where,
                        msg=f"Thẻ tiêu đề (badge) chứa emoji {emojis}: {text!r}",
                        fix_hint="Bỏ emoji khỏi thẻ tiêu đề (dùng chữ in hoa hoặc ký tự phân cách · / →).",
                    )
                )

    return issues
