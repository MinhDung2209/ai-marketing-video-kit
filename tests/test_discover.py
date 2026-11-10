"""tests/test_discover.py — Unit tests for target-uniqueness ranking and inventory JSON shape.

Runs entirely offline with a local static HTML fixture served by http.server.
Uses D:/agent-cache/DISC/ for temporary artifacts and headless Chrome via executable_path.
"""
import functools
import http.server
import json
import os
import pathlib
import sys
import tempfile
import threading
import pytest
from playwright.sync_api import sync_playwright

# Add repo root to sys.path
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "screendemo"))

import discover
import dryrun

CHROME_EXE = "D:/Apps/Google/Chrome/Application/chrome.exe"
CACHE_DIR = pathlib.Path("D:/agent-cache/DISC/test_tmp")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HTML_FIXTURE = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title>StradeVn Fixture App</title>
  <style>
    body { font-family: sans-serif; padding: 20px; }
    .hidden { display: none !important; }
    table { border-collapse: collapse; width: 100%; margin-top: 20px; }
    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
    .stat-card { border: 1px solid #ddd; padding: 12px; margin: 10px 0; border-radius: 8px; }
    .tab { padding: 8px 16px; margin-right: 8px; cursor: pointer; }
  </style>
</head>
<body>
  <h1>Bảng điều khiển StradeVn</h1>

  <!-- Navigation tabs -->
  <nav role="tablist">
    <button role="tab" class="tab" id="tab-overview">Tổng quan</button>
    <button role="tab" class="tab" id="tab-raw">Dữ liệu tờ khai thô</button>
    <button role="tab" class="tab" id="tab-company">Dữ liệu công ty</button>
  </nav>

  <!-- Action buttons: unique, duplicate, and unsafe -->
  <section id="actions" style="margin: 20px 0;">
    <button id="btn-search">Tìm kiếm nhanh</button>
    <!-- Duplicate role + name, distinguished by text or ID -->
    <button class="btn-dup" id="dup-1">Xem chi tiết gói A</button>
    <button class="btn-dup" id="dup-2">Xem chi tiết gói B</button>
    
    <!-- Unsafe action buttons (read-only guard) -->
    <button id="btn-create">Tạo chiến dịch</button>
    <button id="btn-crawl">Bắt đầu truy xuất dữ liệu</button>
    <button id="btn-send">Gửi email</button>
    
    <!-- Hidden element (must be excluded) -->
    <button id="btn-hidden" class="hidden">Nút bị ẩn</button>
  </section>

  <!-- Input after label -->
  <div style="margin: 15px 0;">
    <label for="input-contract">Số hợp đồng</label>
    <input id="input-contract" name="contract_no" placeholder="Nhập số hợp đồng" />
  </div>

  <!-- Stat cards / Metric facts -->
  <div class="stat-card">
    <h3>Thống kê khách hàng</h3>
    <p>Có <strong>19 công ty</strong> tiềm năng trong danh sách.</p>
    <p>Trạng thái: <strong>12/20</strong> công ty đã có email liên hệ.</p>
  </div>

  <!-- Data Table with concrete facts -->
  <table>
    <thead>
      <tr>
        <th>NGÀY KHAI BÁO</th>
        <th>CÔNG TY</th>
        <th>CẢNG ĐẾN</th>
        <th>SỐ LƯỢNG</th>
        <th>GIÁ TRỊ</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>22/7/2026</td>
        <td>HARRIS SPICE ASIA PACIFIC LTD</td>
        <td>CHICAGO</td>
        <td>24000 KGS</td>
        <td>481.760 USD</td>
      </tr>
      <tr>
        <td>23/8/2026</td>
        <td>ST CHARLES TRADING INC</td>
        <td>LOS ANGELES</td>
        <td>17,680 KG</td>
        <td>37.128 USD</td>
      </tr>
    </tbody>
  </table>
</body>
</html>
"""


class StaticHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_FIXTURE.encode("utf-8"))

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="session")
def local_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), StaticHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    yield url
    server.shutdown()


@pytest.fixture(scope="session")
def browser_page(local_server):
    pw = sync_playwright().start()
    browser = pw.chromium.launch(executable_path=CHROME_EXE, headless=True)
    ctx = browser.new_context(viewport={"width": 1080, "height": 1350})
    page = ctx.new_page()
    page.goto(local_server, wait_until="domcontentloaded")
    yield page
    page.close()
    browser.close()
    pw.stop()


def test_is_safe_action():
    """Verify safety guard catches forbidden action labels."""
    assert discover.is_safe_action("Tìm kiếm nhanh", "button") is True
    assert discover.is_safe_action("Xem chi tiết", "button") is True
    assert discover.is_safe_action("Tạo chiến dịch", "button") is False
    assert discover.is_safe_action("Bắt đầu truy xuất", "button") is False
    assert discover.is_safe_action("Gửi email", "button") is False
    assert discover.is_safe_action("Send message", "button") is False
    assert discover.is_safe_action("Xoá dữ liệu", "button") is False
    assert discover.is_safe_action("Delete campaign", "button") is False
    assert discover.is_safe_action("Lưu thay đổi", "button") is False
    assert discover.is_safe_action("Thanh toán", "button") is False
    assert discover.is_safe_action("Submit form", "form") is False
    assert discover.is_safe_action("Submit", "input", {"type": "submit"}) is False


def test_target_uniqueness_ranking_prefers_role_name(browser_page):
    """Verify target ranking prioritizes unique role + accessible name."""
    item = {
        "tag": "button",
        "role": "button",
        "name": "Tìm kiếm nhanh",
        "text": "Tìm kiếm nhanh",
        "id": "btn-search",
        "css_path": "#btn-search"
    }
    target = discover.rank_target_for_element(browser_page, item)
    assert target.get("role") == "button"
    assert target.get("name") == "Tìm kiếm nhanh"
    assert discover.count_visible_target(browser_page, target) == 1


def test_target_uniqueness_ranking_disambiguation(browser_page):
    """Verify target ranking resolves elements with duplicate roles to unique text or CSS."""
    item_dup1 = {
        "tag": "button",
        "role": "button",
        "name": "Xem chi tiết",
        "text": "Xem chi tiết gói A",
        "id": "dup-1",
        "css_path": "#dup-1"
    }
    target1 = discover.rank_target_for_element(browser_page, item_dup1)
    # Since role+name "Xem chi tiết" matches multiple buttons, it should resolve to exact text or ID
    assert discover.count_visible_target(browser_page, target1) == 1


def test_every_extracted_element_has_unique_target(browser_page):
    """Assert that every interactive element extracted from page has count_visible == 1."""
    raw = discover.extract_page_data(browser_page)
    elements = raw["elements"]
    assert len(elements) > 0

    for el in elements:
        t = discover.rank_target_for_element(browser_page, el)
        vis_count = discover.count_visible_target(browser_page, t)
        assert vis_count == 1, f"Target for {el['label']!r} resolved to {vis_count} visible elements: {t}"


def test_inventory_json_shape(local_server, browser_page):
    """Verify inventory JSON schema, exclusion of hidden elements, and presence of concrete facts."""
    out_json = CACHE_DIR / "inventory_test.json"
    inv = discover.discover_site(
        start_url=local_server,
        out_json_path=str(out_json),
        viewport=(1080, 1350),
        page=browser_page
    )

    # Validate top-level keys
    assert "base" in inv
    assert inv["viewport"] == [1080, 1350]
    assert "pages" in inv
    assert len(inv["pages"]) >= 1

    p = inv["pages"][0]
    assert "url" in p
    assert "title" in p
    assert "screenshot" in p
    assert "nav" in p
    assert "elements" in p
    assert "facts" in p
    assert "text_path" in p

    # Assert element kinds and properties
    valid_kinds = {"tab", "button", "link", "input", "table", "number", "heading"}
    kinds_found = {el["kind"] for el in p["elements"]}
    assert kinds_found.issubset(valid_kinds)
    assert "button" in kinds_found
    assert "table" in kinds_found

    # Assert unsafe buttons have safe == False
    create_btn = next((el for el in p["elements"] if "Tạo chiến dịch" in el["label"]), None)
    assert create_btn is not None
    assert create_btn["safe"] is False

    # Assert hidden button is excluded
    hidden_btn = next((el for el in p["elements"] if "Nút bị ẩn" in el["label"]), None)
    assert hidden_btn is None

    # Assert concrete facts are present
    fact_texts = [f["text"] for f in p["facts"]]
    assert any("24000 KGS" in t for t in fact_texts)
    assert any("HARRIS SPICE" in t for t in fact_texts)
    assert any("CHICAGO" in t for t in fact_texts)

    # Check that inventory.md was written
    md_path = CACHE_DIR / "inventory.md"
    assert md_path.exists()
    assert len(md_path.read_text(encoding="utf-8")) > 50


def test_dryrun_verification_on_fixture(local_server, browser_page):
    """Verify dryrun.py asserts target uniqueness and flags invalid selectors or missing text."""
    clip_dir = CACHE_DIR / "test_clip"
    clip_dir.mkdir(parents=True, exist_ok=True)

    shots_data = {
        "viewport": [1080, 1350],
        "shots": {
            "s1": {
                "steps": [
                    {"do": "goto", "url": local_server},
                    {"do": "wait", "sec": 0.5},
                    {"do": "click", "target": {"role": "button", "name": "Tìm kiếm nhanh", "exact": True}},
                    {"do": "focus", "text": "24000 KGS"},
                    {"do": "ink", "text": "HARRIS SPICE ASIA PACIFIC LTD"}
                ]
            }
        }
    }
    (clip_dir / "shots.json").write_text(json.dumps(shots_data, ensure_ascii=False), encoding="utf-8")

    # 1. Valid shot should pass
    res = dryrun.dryrun_clip(str(clip_dir), page=browser_page)
    assert res["ok"] is True
    assert len(res["errors"]) == 0

    # 2. Shot with non-existent selector should fail with check='selector'
    bad_shots_data = {
        "viewport": [1080, 1350],
        "shots": {
            "s1": {
                "steps": [
                    {"do": "goto", "url": local_server},
                    {"do": "click", "target": {"css": "#non-existent-button-xyz"}}
                ]
            }
        }
    }
    (clip_dir / "shots.json").write_text(json.dumps(bad_shots_data, ensure_ascii=False), encoding="utf-8")
    res_bad = dryrun.dryrun_clip(str(clip_dir), page=browser_page)
    assert res_bad["ok"] is False
    assert len(res_bad["errors"]) > 0
    assert res_bad["errors"][0]["check"] == "selector"
    assert "fix_hint" in res_bad["errors"][0]

    # 3. Shot with missing mark text should fail
    bad_mark_data = {
        "viewport": [1080, 1350],
        "shots": {
            "s1": {
                "steps": [
                    {"do": "goto", "url": local_server},
                    {"do": "focus", "text": "CON_SO_KHONG_TON_TAI_9999"}
                ]
            }
        }
    }
    (clip_dir / "shots.json").write_text(json.dumps(bad_mark_data, ensure_ascii=False), encoding="utf-8")
    res_mark = dryrun.dryrun_clip(str(clip_dir), page=browser_page)
    assert res_mark["ok"] is False
    assert any("CON_SO_KHONG_TON_TAI_9999" in e["msg"] for e in res_mark["errors"])
