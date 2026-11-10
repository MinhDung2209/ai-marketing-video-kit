"""Check seamless loop seam frame parity."""
from __future__ import annotations

import io
from pathlib import Path
from typing import List

from PIL import Image, ImageChops, ImageStat

from tools.vqa.checks.brief.loop import is_loop_clip
from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check

try:
    from tools.render import SEEK_JS, find_chrome
except ImportError:
    SEEK_JS = ""
    find_chrome = lambda: None


def compute_frame_difference(img_bytes1: bytes, img_bytes2: bytes) -> float:
    """Compute mean absolute pixel difference across channels using PIL."""
    im1 = Image.open(io.BytesIO(img_bytes1)).convert("RGB")
    im2 = Image.open(io.BytesIO(img_bytes2)).convert("RGB")
    if im1.size != im2.size:
        im2 = im2.resize(im1.size)
    diff = ImageChops.difference(im1, im2)
    stat = ImageStat.Stat(diff)
    return sum(stat.mean) / len(stat.mean)


@register_check(stage="build", name="loop_seam")
def check_loop_seam(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    if not is_loop_clip(ctx):
        return issues

    index_file = ctx.clip_dir / "index.html"
    if not index_file.exists():
        return issues

    max_diff = float(ctx.rules.get("loop", {}).get("max_seam_pixel_diff", 25.0))

    duration = None
    if ctx.cues_json.get("duration"):
        try:
            duration = float(ctx.cues_json["duration"])
        except Exception:
            pass

    if duration is None:
        import re
        m = re.search(r'data-duration="([^"]+)"', ctx.index_html)
        if m:
            try:
                duration = float(m.group(1))
            except Exception:
                pass

    if not duration or duration <= 1.0:
        return issues

    t_first = 0.05
    t_last = max(0.1, duration - 0.05)

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            chrome_path = find_chrome()
            browser = pw.chromium.launch(headless=True, executable_path=chrome_path)
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            file_url = index_file.resolve().as_uri()
            page.goto(file_url, wait_until="domcontentloaded")
            page.wait_for_timeout(400)

            # Seek to first frame and snap
            if SEEK_JS:
                page.evaluate(SEEK_JS, t_first)
            b1 = page.screenshot()

            # Seek to last frame and snap
            if SEEK_JS:
                page.evaluate(SEEK_JS, t_last)
            b2 = page.screenshot()

            browser.close()

            diff_val = compute_frame_difference(b1, b2)
            if diff_val > max_diff:
                issues.append(
                    Issue(
                        check="loop_seam",
                        where="index.html loop seam (t=0.05 vs t=end-0.05)",
                        msg=f"Độ lệch điểm nối vòng (loop seam) quá lớn: mean pixel diff = {diff_val:.1f} (ngưỡng cho phép ≤ {max_diff:.1f})",
                        fix_hint="Chỉnh khung hình cảnh cuối zoom đúng vào toạ độ và mức zoom của cảnh đầu (dòng 24 tấn) để video lặp mượt mà không bị giật hình.",
                    )
                )

    except Exception as exc:
        issues.append(
            Issue(
                check="loop_seam",
                where="index.html loop seam",
                msg=f"Không thể đo loop seam bằng Playwright: {exc}",
                fix_hint="Kiểm tra Playwright và Chrome để chạy headless render.",
                level="warning",
            )
        )

    return issues
