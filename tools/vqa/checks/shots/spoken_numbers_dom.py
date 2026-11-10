"""Check that numbers and proper nouns spoken in voice.json match captured DOM text."""
from __future__ import annotations

import re
from typing import Dict, List, Set

from tools.vqa.context import VQAContext
from tools.vqa.number_parser import (
    check_presence_in_dom,
    extract_numbers_from_voice_text,
    extract_proper_nouns,
)
from tools.vqa.registry import Issue, register_check


def get_shot_to_lines_mapping(ctx: VQAContext) -> Dict[str, Set[str]]:
    """Map shot IDs (s1, s2...) to voice line IDs (V1, V2...) tied to that scene."""
    mapping: Dict[str, Set[str]] = {}

    # 1. Parse from story.py if available
    story_py = ctx.clip_dir / "story.py"
    if story_py.exists():
        try:
            content = story_py.read_text(encoding="utf-8")
            # Match screen("s1", ..., [P("V1", ...), ...])
            blocks = re.findall(r'screen\(\s*[\'"](\w+)[\'"].*?\[(.*?)\]', content, re.DOTALL)
            for shot_id, p_block in blocks:
                lines = re.findall(r'P\(\s*[\'"](V\d+)[\'"]', p_block)
                mapping.setdefault(shot_id, set()).update(lines)
        except Exception:
            pass

    # 2. Parse from index.html if story.py didn't map all
    if not mapping and ctx.index_html:
        # Sections with screen video
        sec_re = re.compile(r'<section[^>]*data-start="([^"]+)"[^>]*data-duration="([^"]+)"[^>]*>.*?assets/screen/(\w+)/screen\.mp4.*?</section>', re.DOTALL)
        for s_match in sec_re.finditer(ctx.index_html):
            s_start = float(s_match.group(1))
            s_dur = float(s_match.group(2))
            s_end = s_start + s_dur
            shot_id = s_match.group(3)

            # Match caps overlapping this section
            cap_re = re.compile(r'<div class="cap"[^>]*data-start="([^"]+)"[^>]*data-duration="([^"]+)"[^>]*><span>(.*?)</span></div>', re.DOTALL)
            for c_match in cap_re.finditer(ctx.index_html):
                c_start = float(c_match.group(1))
                if s_start - 0.5 <= c_start < s_end:
                    cap_text = c_match.group(3)
                    # Find which voice line has this caption
                    for line in ctx.voice_json.get("lines", []):
                        if line.get("caption") and line["caption"] in cap_text:
                            mapping.setdefault(shot_id, set()).add(line["id"])

    # 3. Fallback based on shots.json notes or sequential 1-to-1 if still empty
    if not mapping:
        shots = ctx.shots_json.get("shots", {})
        for shot_id, shot_info in shots.items():
            note = str(shot_info.get("note", ""))
            found_v = re.findall(r"\bV(\d+)\b", note)
            for fv in found_v:
                mapping.setdefault(shot_id, set()).add(f"V{fv}")

    return mapping


@register_check(stage="shots", name="spoken_numbers_dom")
def check_spoken_numbers_dom(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    mapping = get_shot_to_lines_mapping(ctx)
    lines_by_id = {line["id"]: line for line in ctx.voice_json.get("lines", []) if "id" in line}

    # Also collect global DOM text and clip vars as fallback
    all_dom_text = []
    for shot_id in ctx.shots_json.get("shots", {}):
        all_dom_text.append(ctx.get_captured_dom_text(shot_id))
    global_text = "\n".join(all_dom_text)

    for shot_id, line_ids in mapping.items():
        dom_text = ctx.get_captured_dom_text(shot_id)
        if not dom_text:
            dom_text = global_text

        for lid in line_ids:
            line = lines_by_id.get(lid)
            if not line:
                continue

            voice_text = line.get("text", "")

            # 1. Check numbers
            numbers = extract_numbers_from_voice_text(voice_text)
            for num_info in numbers:
                raw_num = num_info["raw"]
                if not check_presence_in_dom(num_info, dom_text):
                    # Check if present in global text
                    if not check_presence_in_dom(num_info, global_text):
                        issues.append(
                            Issue(
                                check="spoken_numbers_dom",
                                where=f"assets/screen/{shot_id} (khớp với {lid})",
                                msg=f"Số liệu nói trong {lid} ({raw_num!r} → {num_info['val']}) không tìm thấy trong DOM bản quay {shot_id}",
                                fix_hint=f"Kiểm tra con số {raw_num!r} trên màn hình quay hoặc điền đúng biến trong clip.json để khớp số thật.",
                            )
                        )

            # 2. Check proper nouns
            nouns = extract_proper_nouns(voice_text)
            for noun in nouns:
                # Exclude brand name or generic terms
                if noun.lower() in ("stradevn", "sales", "google", "hs", "email"):
                    continue
                if not check_presence_in_dom(noun, dom_text):
                    if not check_presence_in_dom(noun, global_text):
                        issues.append(
                            Issue(
                                check="spoken_numbers_dom",
                                where=f"assets/screen/{shot_id} (khớp với {lid})",
                                msg=f"Tên riêng nói trong {lid} ({noun!r}) không tìm thấy trong DOM bản quay {shot_id}",
                                fix_hint=f"Đảm bảo từ khoá/tên riêng {noun!r} hiển thị trên giao diện lúc quay hoặc đổi lời đọc.",
                            )
                        )

    return issues
