"""Check that video has no black frames longer than 0.3s via blackdetect."""
from __future__ import annotations

import re
import subprocess
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="render", name="black_frames")
def check_black_frames(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    mp4_file = ctx.final_mp4
    if not mp4_file or not mp4_file.exists():
        return issues

    max_black = float(ctx.rules.get("audio", {}).get("max_black_duration", 0.3))

    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-nostats",
                "-i", str(mp4_file),
                "-vf", f"blackdetect=d={max_black}:pix_th=0.10",
                "-f", "null",
                "-",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        output = proc.stderr
    except Exception as exc:
        issues.append(
            Issue(
                check="black_frames",
                where=f"{mp4_file.name}",
                msg=f"Không thể chạy ffmpeg blackdetect: {exc}",
                fix_hint="Kiểm tra ffmpeg đã cài đặt trong PATH.",
            )
        )
        return issues

    # Parse blackdetect outputs
    # Example: [blackdetect @ ...] black_start:12.3 black_end:12.8 black_duration:0.5
    matches = re.finditer(r"black_start:([-\d.]+)\s+black_end:([-\d.]+)\s+black_duration:([-\d.]+)", output)
    for m in matches:
        b_start = float(m.group(1))
        b_end = float(m.group(2))
        b_dur = float(m.group(3))

        if b_dur > max_black:
            issues.append(
                Issue(
                    check="black_frames",
                    where=f"{mp4_file.name} ({b_start:.2f}s - {b_end:.2f}s)",
                    msg=f"Khung hình đen kéo dài {b_dur:.2f}s (vượt mức cho phép {max_black}s)",
                    fix_hint="Kiểm tra mối chuyển cảnh tại mốc này để đảm bảo video chuyển tiếp mượt mà, không bị hẫng khung đen.",
                )
            )

    return issues
