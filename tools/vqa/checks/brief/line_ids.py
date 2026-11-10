"""Check every voice line has an id V#."""
from __future__ import annotations

import re
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check

LINE_ID_RE = re.compile(r"^V\d+$")


@register_check(stage="brief", name="line_ids")
def check_line_ids(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    lines = ctx.voice_json.get("lines", [])

    if not lines:
        issues.append(
            Issue(
                check="line_ids",
                where="voice.json",
                msg="Không tìm thấy danh sách câu thoại ('lines') trong voice.json",
                fix_hint="Thêm mảng 'lines' chứa các câu thoại V1, V2... vào voice.json.",
            )
        )
        return issues

    seen = set()
    for idx, line in enumerate(lines):
        lid = line.get("id")
        if not lid or not LINE_ID_RE.match(str(lid)):
            issues.append(
                Issue(
                    check="line_ids",
                    where=f"voice.json lines[{idx}]",
                    msg=f"Mã câu thoại không đúng định dạng V#: {lid!r}",
                    fix_hint=f"Đổi id câu thoại thành V{idx + 1}.",
                )
            )
        elif lid in seen:
            issues.append(
                Issue(
                    check="line_ids",
                    where=f"voice.json lines[{idx}]",
                    msg=f"Mã câu thoại bị trùng lặp: {lid!r}",
                    fix_hint=f"Đảm bảo mỗi câu thoại có mã id V# duy nhất.",
                )
            )
        else:
            seen.add(lid)

    return issues
