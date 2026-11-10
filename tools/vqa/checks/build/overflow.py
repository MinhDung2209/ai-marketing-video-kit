"""Check text overflow and safe band invasion via headless Playwright render."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check

# Import find_chrome helper from tools.render
try:
    from tools.render import find_chrome
except ImportError:
    find_chrome = lambda: None


@register_check(stage="build", name="overflow")
def check_text_overflow(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    index_file = ctx.clip_dir / "index.html"
    if not index_file.exists():
        return issues

    safe_right = ctx.rules.get("safe_zones", {}).get("right", 140)
    safe_right_x = 1080 - safe_right

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        issues.append(
            Issue(
                check="overflow",
                where="index.html",
                msg="Playwright chưa cài đặt trong môi trường Python",
                fix_hint="Cài đặt playwright để kiểm tra text overflow tự động.",
                level="warning",
            )
        )
        return issues

    try:
        with sync_playwright() as pw:
            chrome_path = find_chrome()
            browser = pw.chromium.launch(headless=True, executable_path=chrome_path)
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            file_url = index_file.resolve().as_uri()
            page.goto(file_url, wait_until="domcontentloaded")
            page.wait_for_timeout(300)

            # Evaluate elements in browser
            results = page.evaluate("""(safeRightX) => {
                const issues = [];
                const visited = new Set();
                const selectors = [
                    { sel: '.cap span', kind: 'caption', strictSafe: true },
                    { sel: '.step', kind: 'badge', strictSafe: true },
                    { sel: '#lg', kind: 'logo_card', strictSafe: false },
                    { sel: '#tg', kind: 'logo_card', strictSafe: false },
                    { sel: '#url', kind: 'logo_card', strictSafe: false },
                    { sel: '.sub', kind: 'logo_card', strictSafe: false },
                    { sel: '.cmt', kind: 'cta', strictSafe: true },
                    { sel: '.cta', kind: 'cta', strictSafe: true }
                ];

                for (const item of selectors) {
                    const elements = document.querySelectorAll(item.sel);
                    elements.forEach(el => {
                        if (visited.has(el)) return;
                        visited.add(el);
                        const r = el.getBoundingClientRect();
                        const text = (el.innerText || '').slice(0, 40).replace(/\\n/g, ' ');

                        // 1. Check scroll overflow (text exceeds box)
                        if (el.scrollWidth > el.clientWidth + 2) {
                            issues.push({
                                type: 'scroll_overflow',
                                selector: item.sel,
                                text: text,
                                msg: `Hộp chữ bị tràn (scrollWidth ${el.scrollWidth} > clientWidth ${el.clientWidth})`,
                                level: 'error'
                            });
                        }

                        // 2. Check outside 1080 frame
                        if (r.left < -2 || r.right > 1082) {
                            issues.push({
                                type: 'frame_overflow',
                                selector: item.sel,
                                text: text,
                                msg: `Phần tử vượt ra ngoài khung hình 1080px (left: ${Math.round(r.left)}, right: ${Math.round(r.right)})`,
                                level: 'error'
                            });
                        }

                        // 3. Check right safe band (140px)
                        let textRight = r.right;
                        try {
                            const range = document.createRange();
                            range.selectNodeContents(el);
                            const tr = range.getBoundingClientRect();
                            if (tr.width > 0) textRight = tr.right;
                        } catch(e) {}

                        if (textRight > safeRightX + 2) {
                            issues.push({
                                type: 'safe_band',
                                selector: item.sel,
                                text: text,
                                msg: `Chữ ${text ? '"' + text + '"' : ''} lấn vào safe band phải 140px (mép phải: ${Math.round(textRight)}px > ${safeRightX}px)`,
                                level: item.strictSafe ? 'error' : 'warning'
                            });
                        }
                    });
                }
                return issues;
            }""", safe_right_x)

            browser.close()

            # Deduplicate similar issues per selector
            seen = set()
            for r in results:
                key = (r["type"], r["selector"], r["text"][:20])
                if key in seen:
                    continue
                seen.add(key)

                fix_hint = "Thu nhỏ cỡ chữ, thêm ngắt dòng hoặc chỉnh CSS right/padding để nội dung nằm gọn trong vùng an toàn (right ≤ 940px)."
                if r["type"] == "scroll_overflow":
                    fix_hint = "Tăng kích thước thẻ bọc hoặc giảm font-size / bớt từ để chữ không bị tràn hộp."

                issues.append(
                    Issue(
                        check="overflow",
                        where=f"index.html {r['selector']} ({r['text']!r})",
                        msg=r["msg"],
                        fix_hint=fix_hint,
                        level=r.get("level", "error"),
                    )
                )

    except Exception as exc:
        issues.append(
            Issue(
                check="overflow",
                where="index.html render",
                msg=f"Không thể đo tràn chữ bằng Playwright: {exc}",
                fix_hint="Kiểm tra Playwright và Chrome để chạy headless render.",
                level="warning",
            )
        )

    return issues
