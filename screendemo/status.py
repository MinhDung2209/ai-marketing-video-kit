"""In chữ của 1 trang (CHỈ ĐỌC) trong Chrome quay video — dùng để lấy số thật (vd kết quả chiến dịch) điền vào clip.json.
python status.py <url> [số ký tự]"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from rec import CDP
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(CDP); pg = b.contexts[0].new_page()
    pg.goto(sys.argv[1], wait_until="domcontentloaded"); pg.wait_for_timeout(4000)
    print(pg.locator("body").inner_text()[: int(sys.argv[2]) if len(sys.argv) > 2 else 900]); pg.close()
