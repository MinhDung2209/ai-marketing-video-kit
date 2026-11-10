"""Kiểm tra nhạc nền (BGM): điểm vào sạch, không khoảng lặng > 0.5s, và phủ trọn độ dài video.

Luật:
  1. Không có khoảng lặng > 0.5s ở đầu bài hoặc trong lớp nhạc nền (BGM bed).
  2. Nhạc nền phải phủ kín toàn bộ độ dài video, không để đuôi cụt/lặng (silent tail).
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


def _probe_duration(f: Path) -> Optional[float]:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return float(r.stdout.strip())
    except Exception:
        return None


@register_check(stage="build", name="bgm_entry")
def check_bgm_entry(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []

    cues = ctx.cues_json
    if not cues:
        return issues

    duration = float(cues.get("duration", 0.0))
    bgm = cues.get("bgm")
    if not bgm:
        issues.append(
            Issue(
                check="bgm_entry",
                where="cues.json bgm",
                msg="Clip không có nhạc nền (BGM).",
                fix_hint="Thêm track BGM vào cues.json hoặc cấu hình sound_plan để tự động chọn nhạc nền.",
                level="warning",
            )
        )
        return issues

    bgm_start = float(bgm.get("start", 0.0))
    bgm_offset = float(bgm.get("offset", 0.0))
    bgm_file = bgm.get("file", "")

    # Kiểm tra 1: Không có khoảng lặng > 0.5s ở đầu video
    if bgm_start > 0.5:
        issues.append(
            Issue(
                check="bgm_entry",
                where=f"cues.json bgm start={bgm_start:.2f}s",
                msg=f"Nhạc nền vào muộn {bgm_start:.2f}s (> 0.5s), gây khoảng lặng ở đầu video.",
                fix_hint="Đặt bgm.start <= 0.5s và dùng phân tích Best Entry để vào nhạc đúng lúc.",
            )
        )

    # Kiểm tra 2: Nhạc nền phủ trọn độ dài video
    # Nếu bgm có loop (hoặc mix_audio stream_loop mặc định), nó sẽ lặp
    is_looped = bool(bgm.get("loop", True))
    # Nếu kiểm tra file thực tế
    file_path = ctx.clip_dir / bgm_file if not Path(bgm_file).is_absolute() else Path(bgm_file)
    if not file_path.exists():
        # Thử tìm trong audio-library
        kit_lib = ctx.clip_dir.parent.parent / "audio-library"
        if (kit_lib / bgm_file).exists():
            file_path = kit_lib / bgm_file

    if file_path.exists() and not is_looped:
        file_dur = _probe_duration(file_path)
        if file_dur:
            effective_len = file_dur - bgm_offset
            if bgm_start + effective_len < duration - 0.5:
                issues.append(
                    Issue(
                        check="bgm_entry",
                        where=f"cues.json bgm (file dài {file_dur:.1f}s, phủ tới {bgm_start + effective_len:.1f}s)",
                        msg=f"Nhạc nền không phủ hết video ({bgm_start + effective_len:.1f}s < {duration:.1f}s), để lại đuôi lặng.",
                        fix_hint="Bật loop=True hoặc chọn bản nhạc dài hơn độ dài video.",
                    )
                )

    # Kiểm tra 3: Với video loop, fade_in và fade_out phải ngắn để seamless
    sound_plan_file = ctx.clip_dir / "sound_plan.json"
    if sound_plan_file.exists():
        try:
            sp = json.loads(sound_plan_file.read_text(encoding="utf-8"))
            if sp.get("archetype") == "demo-loop" or sp.get("bgm", {}).get("brief", {}).get("is_loop"):
                fi = float(bgm.get("fade_in", 0.5))
                fo = float(bgm.get("fade_out", 2.0))
                if fo > 0.5:
                    issues.append(
                        Issue(
                            check="bgm_entry",
                            where=f"cues.json bgm fade_out={fo:.2f}s",
                            msg=f"Video loop có fade_out dài ({fo:.2f}s), làm đứt đoạn âm thanh khi quay vòng.",
                            fix_hint="Đặt fade_out <= 0.25s (ví dụ 0.15s) để nối vòng liền mạch (seamless loop).",
                            level="warning",
                        )
                    )
        except Exception:
            pass

    return issues
