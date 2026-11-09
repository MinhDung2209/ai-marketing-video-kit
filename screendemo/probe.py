"""Liệt kê chữ + input/nút/tab của 1 trang (CHỈ ĐỌC) trong Chrome quay video — dùng khi viết shots.json cho web mới.
python probe.py <url> [rộng] [cao]"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from rec import CDP
from playwright.sync_api import sync_playwright
W = int(sys.argv[2]) if len(sys.argv) > 2 else 720; H = int(sys.argv[3]) if len(sys.argv) > 3 else 1080
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(CDP); pg = b.contexts[0].new_page()
    pg.set_viewport_size({"width": W, "height": H})
    pg.goto(sys.argv[1], wait_until="domcontentloaded"); pg.wait_for_timeout(5000)
    print(pg.locator("body").inner_text()[:700]); print("-----")
    r = pg.evaluate("""() => [...document.querySelectorAll('input,textarea,select,button,a[href]')].filter(e=>e.offsetParent).slice(0,120).map(e=>{const b=e.getBoundingClientRect();return [e.tagName, e.type||'', e.placeholder||'', (e.innerText||e.value||'').trim().slice(0,40), e.getAttribute('href')||'', Math.round(b.x), Math.round(b.y)]})""")
    for x in r: print(x)
    pg.close()
