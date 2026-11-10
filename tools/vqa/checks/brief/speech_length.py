"""Check total estimated speech length."""
from __future__ import annotations

import re
import subprocess
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="brief", name="speech_length")
def check_speech_length(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    max_seconds = ctx.rules.get("max_seconds", 115)
    lines = ctx.voice_json.get("lines", [])

    total_duration = 0.0
    measured = False

    # 1. Try measuring actual audio files if they exist
    audio_dir = ctx.clip_dir / "audio"
    if audio_dir.is_dir():
        durations = []
        for line in lines:
            lid = line.get("id")
            f = audio_dir / f"{lid}.mp3"
            if f.exists():
                try:
                    out = subprocess.check_output(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                        text=True,
                    ).strip()
                    durations.append(float(out))
                except Exception:
                    pass
        if len(durations) == len(lines) and durations:
            gap = ctx.voice_json.get("gap_seconds", 0.3)
            total_duration = sum(durations) + gap * max(0, len(durations) - 1)
            measured = True

    # 2. Try cues.json duration
    if not measured and ctx.cues_json.get("duration"):
        total_duration = float(ctx.cues_json["duration"])
        measured = True

    # 3. Estimate from words if no audio yet (~3.0 syllables/s + gaps)
    if not measured:
        total_words = 0
        gap = ctx.voice_json.get("gap_seconds", 0.3)
        for line in lines:
            text = re.sub(r"\[[^\]]*\]", " ", line.get("text", ""))
            words = text.strip().split()
            total_words += len(words)
        total_duration = (total_words / 3.0) + gap * max(0, len(lines) - 1)

    if total_duration >= max_seconds:
        issues.append(
            Issue(
                check="speech_length",
                where="voice.json",
                msg=f"Tổng thời lượng lời thoại ước tính ({total_duration:.1f}s) vượt quá giới hạn cho phép ({max_seconds}s)",
                fix_hint=f"Cắt bớt lời thoại hoặc rút gọn các câu dài để tổng thời lượng < {max_seconds}s (video short nên dưới 2 phút).",
            )
        )

    return issues
