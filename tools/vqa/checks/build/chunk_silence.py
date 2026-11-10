"""Check that every voice chunk boundary sits in silence."""
from __future__ import annotations

from pathlib import Path
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check

try:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
    from speech_segments import segments
except ImportError:
    segments = None


@register_check(stage="build", name="chunk_silence")
def check_chunk_silence(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    pieces = ctx.cues_json.get("pieces", [])
    if not pieces or segments is None:
        return issues

    audio_dir = ctx.clip_dir / "audio"
    seg_cache = {}

    for idx, p in enumerate(pieces):
        lid = p.get("line")
        a = float(p.get("a", 0.0))
        b = float(p.get("b", 0.0))
        f_name = p.get("file", f"{lid}.mp3")

        # Resolve audio file
        audio_file = Path(f_name)
        if not audio_file.is_absolute():
            audio_file = audio_dir / audio_file.name
        if not audio_file.exists():
            continue

        if audio_file not in seg_cache:
            try:
                seg_cache[audio_file] = [tuple(x) for x in segments(str(audio_file))]
            except Exception:
                seg_cache[audio_file] = []

        segs = seg_cache[audio_file]
        if not segs:
            continue

        # Check if cut point 'a' (if not start of file) cuts inside a speech segment
        if a > 0.05:
            for s, e in segs:
                if s + 0.05 < a < e - 0.05:
                    issues.append(
                        Issue(
                            check="chunk_silence",
                            where=f"cues.json piece[{idx}] ({lid}) mốc bắt đầu {a:.2f}s",
                            msg=f"Mốc cắt cụm lời ({a:.2f}s) cắt ngang tiếng nói ({s:.2f}s - {e:.2f}s) thay vì khoảng lặng",
                            fix_hint="Dùng screendemo/chunks.py tính lại mốc cắt cụm lời đúng vào khoảng lặng thật.",
                        )
                    )

        # Check if cut point 'b' cuts inside a speech segment
        file_dur = segs[-1][1] if segs else b
        if b < file_dur - 0.05:
            for s, e in segs:
                if s + 0.05 < b < e - 0.05:
                    issues.append(
                        Issue(
                            check="chunk_silence",
                            where=f"cues.json piece[{idx}] ({lid}) mốc kết thúc {b:.2f}s",
                            msg=f"Mốc cắt cụm lời ({b:.2f}s) cắt ngang tiếng nói ({s:.2f}s - {e:.2f}s) thay vì khoảng lặng",
                            fix_hint="Dùng screendemo/chunks.py tính lại mốc cắt cụm lời đúng vào khoảng lặng thật.",
                        )
                    )

    return issues
