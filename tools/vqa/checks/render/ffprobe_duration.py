"""Check final mp4 duration matches expected timeline duration."""
from __future__ import annotations

import json
import subprocess
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="render", name="ffprobe_duration")
def check_ffprobe_duration(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    mp4_file = ctx.final_mp4
    if not mp4_file or not mp4_file.exists():
        issues.append(
            Issue(
                check="ffprobe_duration",
                where="final/*.mp4",
                msg="Không tìm thấy file MP4 render hoàn chỉnh trong final/ hoặc thư mục clip",
                fix_hint="Chạy lệnh render video trước khi kiểm tra stage render (vd: npx hyperframes render hoặc tools/render.py).",
            )
        )
        return issues

    expected_duration = None
    if ctx.cues_json.get("duration"):
        expected_duration = float(ctx.cues_json["duration"])
    elif ctx.index_html:
        import re
        m = re.search(r'data-duration="([^"]+)"', ctx.index_html)
        if m:
            expected_duration = float(m.group(1))

    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(mp4_file),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        actual_duration = float(proc.stdout.strip())
    except Exception as exc:
        issues.append(
            Issue(
                check="ffprobe_duration",
                where=f"{mp4_file.name}",
                msg=f"Không thể đọc thời lượng video bằng ffprobe: {exc}",
                fix_hint="Kiểm tra ffprobe đã cài đặt và file video không bị lỗi giải mã.",
            )
        )
        return issues

    if expected_duration is not None:
        diff = abs(actual_duration - expected_duration)
        if diff > 0.5:
            issues.append(
                Issue(
                    check="ffprobe_duration",
                    where=f"{mp4_file.name}",
                    msg=f"Thời lượng MP4 ({actual_duration:.2f}s) lệch {diff:.2f}s so với bản dựng ({expected_duration:.2f}s, ngưỡng cho phép ±0.5s)",
                    fix_hint="Kiểm tra quá trình render video có bị cắt ngang hoặc render thừa khung đen ở cuối không.",
                )
            )

    return issues
