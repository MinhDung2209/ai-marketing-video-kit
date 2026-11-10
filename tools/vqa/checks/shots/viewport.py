"""Check recording viewport against profile specifications."""
from __future__ import annotations

from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


@register_check(stage="shots", name="viewport")
def check_viewport(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []

    # Determine expected viewport from rules
    layout = ctx.clip_json.get("layout", "fullbleed")
    vp_rules = ctx.rules.get("viewport", {})
    expected_vp = vp_rules.get(layout, [1080, 1350])

    # 1. Check shots.json viewport
    shots_vp = ctx.shots_json.get("viewport")
    if shots_vp and list(shots_vp) != list(expected_vp):
        issues.append(
            Issue(
                check="viewport",
                where="shots.json 'viewport'",
                msg=f"Kích thước viewport trong shots.json {shots_vp} không khớp với profile ({expected_vp})",
                fix_hint=f"Đổi 'viewport': {list(expected_vp)} trong shots.json để khớp chuẩn tràn viền {layout}.",
            )
        )

    # 2. Check marks.json in assets/screen/*/marks.json
    screen_dir = ctx.clip_dir / "assets" / "screen"
    if screen_dir.is_dir():
        for shot_dir in screen_dir.iterdir():
            if not shot_dir.is_dir() or shot_dir.name.startswith(("_", ".")):
                continue
            shot_id = shot_dir.name
            marks = ctx.get_shot_marks(shot_id)
            for mark in marks:
                vw = mark.get("vw")
                vh = mark.get("vh")
                if vw is not None and vh is not None:
                    if [vw, vh] != list(expected_vp):
                        issues.append(
                            Issue(
                                check="viewport",
                                where=f"assets/screen/{shot_id}/marks.json mark '{mark.get('name')}'",
                                msg=f"Kích thước khung hình quay [{vw}, {vh}] không khớp chuẩn [{expected_vp[0]}, {expected_vp[1]}]",
                                fix_hint=f"Quay lại cảnh {shot_id} với kích thước cửa sổ viewport [{expected_vp[0]}, {expected_vp[1]}].",
                            )
                        )
                        break

    return issues
