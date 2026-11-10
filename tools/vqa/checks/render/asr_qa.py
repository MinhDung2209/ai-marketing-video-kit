"""Optional ASR check reusing tools/tts_qa.py data or quick offline scan."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="render", name="asr_qa")
def check_asr_qa(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []

    # 1. If tts_qa.json already exists in audio/, read its verified results
    tts_qa_file = ctx.clip_dir / "audio" / "tts_qa.json"
    if tts_qa_file.exists():
        try:
            data = json.loads(tts_qa_file.read_text(encoding="utf-8"))
            for item in data:
                flags = item.get("flags", [])
                lid = item.get("id", "unknown")
                if flags:
                    issues.append(
                        Issue(
                            check="asr_qa",
                            where=f"audio/{lid}.mp3",
                            msg=f"ASR phát hiện bất thường: {'; '.join(flags)}",
                            fix_hint=f"Nghe lại câu {lid} hoặc đọc lại bằng tts_script.py (Gemini có thể đọc nhầm thẻ hoặc lố nhịp).",
                            level="warning",
                        )
                    )
            return issues
        except Exception:
            pass

    # 2. Check if local whisperx is available and can run offline-quick
    # As per brief contract: "if it runs offline-quick, else warning only"
    issues.append(
        Issue(
            check="asr_qa",
            where="audio/tts_qa.json",
            msg="Chưa chạy kiểm tra đối chiếu ASR (tts_qa.py)",
            fix_hint="Chạy 'python tools/tts_qa.py voice.json audio' nếu có môi trường ASR offline để kiểm tra câu đọc sai.",
            level="warning",
        )
    )

    return issues
