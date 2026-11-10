"""Check that the rendered video contains an active audio stream."""
from __future__ import annotations

import json
import subprocess
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="render", name="audio_present")
def check_audio_present(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    mp4_file = ctx.final_mp4
    if not mp4_file or not mp4_file.exists():
        return issues

    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=index,codec_name,channels,sample_rate,duration",
                "-of", "json",
                str(mp4_file),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        streams = data.get("streams", [])
    except Exception as exc:
        issues.append(
            Issue(
                check="audio_present",
                where=f"{mp4_file.name}",
                msg=f"Không thể kiểm tra luồng âm thanh bằng ffprobe: {exc}",
                fix_hint="Kiểm tra ffprobe đã cài đặt.",
            )
        )
        return issues

    if not streams:
        issues.append(
            Issue(
                check="audio_present",
                where=f"{mp4_file.name}",
                msg="Video xuất ra không có luồng âm thanh (audio stream bị thiếu)",
                fix_hint="Ghép file narration/final_audio vào video khi xuất bằng ffmpeg (-i narration.mp3 -c:a aac).",
            )
        )

    return issues
