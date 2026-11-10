"""Check integrated loudness (-14±1.5 LUFS) and true peak (< -1 dBTP) via ffmpeg ebur128."""
from __future__ import annotations

import re
import subprocess
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="render", name="loudness_peak")
def check_loudness_peak(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    mp4_file = ctx.final_mp4
    if not mp4_file or not mp4_file.exists():
        return issues

    audio_rules = ctx.rules.get("audio", {})
    target_lufs = float(audio_rules.get("target_lufs", -14.0))
    lufs_tol = float(audio_rules.get("lufs_tolerance", 1.5))
    max_peak = float(audio_rules.get("max_true_peak", -1.0))

    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-nostats",
                "-i", str(mp4_file),
                "-filter_complex", "ebur128=peak=true",
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
                check="loudness_peak",
                where=f"{mp4_file.name}",
                msg=f"Không thể chạy ffmpeg ebur128: {exc}",
                fix_hint="Kiểm tra ffmpeg đã cài đặt trong PATH.",
            )
        )
        return issues

    # Parse Integrated loudness
    # Looking for:
    #   Integrated loudness:
    #     I:         -14.7 LUFS
    i_match = re.search(r"Integrated loudness:\s+I:\s+([-\d.]+)\s+LUFS", output)
    if not i_match:
        # Fallback to search any 'I:\s+([-\d.]+)\s+LUFS' near end
        matches = re.findall(r"I:\s+([-\d.]+)\s+LUFS", output)
        if matches:
            i_val = float(matches[-1])
        else:
            i_val = None
    else:
        i_val = float(i_match.group(1))

    # Parse True peak
    # Looking for:
    #   True peak:
    #     Peak:       -0.8 dBFS
    pk_match = re.search(r"True peak:\s+Peak:\s+([-\d.]+)\s+dBFS", output)
    if not pk_match:
        matches = re.findall(r"Peak:\s+([-\d.]+)\s+dBFS", output)
        if matches:
            pk_val = float(matches[-1])
        else:
            pk_val = None
    else:
        pk_val = float(pk_match.group(1))

    if i_val is not None:
        min_lufs = target_lufs - lufs_tol
        max_lufs = target_lufs + lufs_tol
        if not (min_lufs <= i_val <= max_lufs):
            issues.append(
                Issue(
                    check="loudness_peak",
                    where=f"{mp4_file.name} (Integrated Loudness)",
                    msg=f"Âm lượng tích hợp ({i_val:.1f} LUFS) nằm ngoài tiêu chuẩn ({target_lufs}±{lufs_tol} LUFS: [{min_lufs:.1f}, {max_lufs:.1f}])",
                    fix_hint="Dùng ffmpeg loudnorm hoặc điều chỉnh âm lượng tổng thể của final_audio để đạt khoảng -14 LUFS.",
                )
            )

    if pk_val is not None:
        if pk_val >= max_peak:
            issues.append(
                Issue(
                    check="loudness_peak",
                    where=f"{mp4_file.name} (True Peak)",
                    msg=f"Đỉnh âm lượng True Peak ({pk_val:.1f} dBFS) vượt ngưỡng an toàn < {max_peak:.1f} dBFS (nguy cơ méo tiếng trên loa điện thoại)",
                    fix_hint=f"Hạ âm lượng các âm thanh va đập/SFX lớn hoặc thêm bộ nén/limiter để True Peak < {max_peak:.1f} dBTP.",
                )
            )

    return issues
