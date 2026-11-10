"""Check that each referenced SFX audio file exists on disk."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Set

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="build", name="sfx_exist")
def check_sfx_exist(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    referenced_files: Set[str] = set()

    # 1. From index.html: <audio class="sfx" src="..."> or any audio/sfx
    if ctx.index_html:
        matches = re.findall(r'<audio[^>]+class=[\'"][^\'"]*sfx[^\'"]*[\'"][^>]+src=[\'"]([^\'"]+)[\'"]', ctx.index_html)
        referenced_files.update(matches)
        matches2 = re.findall(r'<audio[^>]+src=[\'"]([^\'"]+)[\'"][^>]+class=[\'"][^\'"]*sfx[^\'"]*[\'"]', ctx.index_html)
        referenced_files.update(matches2)

    # 2. From story.py
    story_py = ctx.clip_dir / "story.py"
    if story_py.exists():
        try:
            content = story_py.read_text(encoding="utf-8")
            sfx_calls = re.findall(r'add_sfx\([^,]+,\s*([^,\)]+)', content)
            for sc in sfx_calls:
                clean_sc = sc.strip().strip("'\"")
                # Look for S("name") pattern -> assets/src/sfx-name.mp3
                s_match = re.search(r'S\([\'"](\w+)[\'"]\)', clean_sc)
                if s_match:
                    referenced_files.add(f"assets/src/sfx-{s_match.group(1)}.mp3")
                elif clean_sc.endswith((".mp3", ".wav")):
                    referenced_files.add(clean_sc)
        except Exception:
            pass

    # 3. Check assets/src directory for any sfx
    src_dir = ctx.clip_dir / "assets" / "src"
    if src_dir.is_dir():
        for f in src_dir.glob("sfx-*.mp3"):
            referenced_files.add(str(f.relative_to(ctx.clip_dir).as_posix()))

    # Verify each referenced file
    for ref in referenced_files:
        ref_path = Path(ref)
        if not ref_path.is_absolute():
            resolved = ctx.clip_dir / ref_path
        else:
            resolved = ref_path

        if not resolved.exists() or resolved.stat().st_size == 0:
            issues.append(
                Issue(
                    check="sfx_exist",
                    where=f"audio sfx {ref!r}",
                    msg=f"File hiệu ứng âm thanh (SFX) không tồn tại hoặc rỗng: {resolved}",
                    fix_hint=f"Tải hoặc chép file SFX vào {ref}; có thể dùng tools/audio_web.py hoặc audio-library/sfx/pixabay/.",
                )
            )

    return issues
