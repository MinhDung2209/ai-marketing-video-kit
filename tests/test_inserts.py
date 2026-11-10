"""Tests for motion inserts (screendemo engine API and templates).
Verifies:
- Placement timing and timeline holding
- Overrun error when insert exceeds scene duration
- Vietnamese number formatting
- Delta direction and comparison logic
- Card stack validation
- Headless execution with zero JS console errors (via Playwright / Chrome)
"""
import concurrent.futures, json, os, pathlib, shutil, subprocess, tempfile, pytest
from playwright.sync_api import sync_playwright

import sys
HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parent
sys.path.insert(0, str(KIT / "screendemo"))
import engine
from engine import Story
import inserts as INS


CHROME_PATH = "D:/Apps/Google/Chrome/Application/chrome.exe"
if not pathlib.Path(CHROME_PATH).exists():
    CHROME_PATH = None


def create_dummy_clip(tmpdir, monkeypatch):
    """Tạo một thư mục clip giả lập với cấu trúc tối thiểu và mock all_chunks."""
    clip = pathlib.Path(tmpdir)
    assets = clip / "assets"
    screen = assets / "screen" / "rec1"
    audio = clip / "audio"
    screen.mkdir(parents=True, exist_ok=True)
    audio.mkdir(parents=True, exist_ok=True)

    # marks.json
    marks = {
        "marks": [
            {"name": "start", "t": 0.0},
            {"name": "m1", "t": 1.0, "box": {"x": 100, "y": 100, "w": 200, "h": 50}},
            {"name": "end", "t": 10.0}
        ],
        "events": []
    }
    (screen / "marks.json").write_text(json.dumps(marks), encoding="utf-8")
    (screen / "screen.mp4").write_bytes(b"\x00" * 64)

    (clip / "fonts.css.part").write_text("/* fonts */", encoding="utf-8")
    (clip / "clip.json").write_text(json.dumps({
        "slug": "test-clip",
        "layout": "fullbleed",
        "brand": {"name": "StradeVn", "hl": "#FBBF24", "accent": "#4F46E5"}
    }), encoding="utf-8")

    # Mock all_chunks để không phụ thuộc vào ffprobe trên file âm thanh
    fake_chunks = {
        "V1": [
            {"text": "Hai mươi tư tấn tiêu", "cap": "24 tấn tiêu", "s": 0.2, "e": 1.4, "a": 0.0, "b": 1.5},
            {"text": "đi Chicago ai mua", "cap": "đi Chicago ai mua", "s": 1.6, "e": 2.8, "a": 1.5, "b": 3.0}
        ]
    }
    monkeypatch.setattr(engine, "all_chunks", lambda proj: fake_chunks)
    return clip


def test_fmt_vi_number():
    assert INS.fmt_vi_number(19) == "19"
    assert INS.fmt_vi_number(24) == "24"
    assert INS.fmt_vi_number(9635200) == "9.635.200"
    assert INS.fmt_vi_number(1000) == "1.000"
    assert INS.fmt_vi_number(6.64, 2) == "6,64"
    assert INS.fmt_vi_number(19.48, 2) == "19,48"
    assert INS.fmt_vi_number(0) == "0"


def test_card_stack_validation():
    with pytest.raises(ValueError, match="cần ít nhất 2 thẻ"):
        INS.render_insert("card_stack", "test_id", 0.0, 1.6, cards=[{"title": "Only One"}])

    with pytest.raises(ValueError, match="cần danh sách 'cards'"):
        INS.render_insert("card_stack", "test_id", 0.0, 1.6)


def test_compare_delta_direction():
    # Khi A < B, direction down (thấp hơn / rẻ hơn)
    h_down, _, _ = INS.render_insert(
        "compare", "cmp_d", 0.0, 1.6,
        before={"label": "Việt Nam", "value": 6.64},
        after={"label": "Mexico", "value": 19.48},
        direction="down"
    )
    assert "ins-compare-delta down" in h_down

    # Khi A > B hoặc chỉ định up
    h_up, _, _ = INS.render_insert(
        "compare", "cmp_u", 0.0, 1.6,
        before={"label": "Việt Nam", "value": 25.0},
        after={"label": "Mexico", "value": 10.0},
        direction="up"
    )
    assert "ins-compare-delta up" in h_up


def test_insert_placement_and_hold(monkeypatch):
    cache_dir = pathlib.Path("D:/agent-cache/MOT/tmp_tests")
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir) as td:
        clip = create_dummy_clip(td, monkeypatch)
        st = Story(clip, variant="full")
        P = st.P

        # Tạo cảnh quay màn hình dài đủ để chứa insert
        st.screen("rec1", "start", "end", [
            P("V1", 0, 1, at="m1")
        ], badge="TEST SCENE", tail=2.5)

        voice_end = st.state["last"]
        assert voice_end > 0

        # Chèn counter
        ret_end = st.insert("counter", value=19, unit="người mua", label="Hồ tiêu Mỹ", dur=1.6)
        
        # Kiểm tra thời điểm đặt: mặc định sau voice_end
        ev = st.insert_events[-1]
        assert ev["kind"] == "counter"
        assert ev["time"] >= voice_end
        assert ev["reveal_time"] == round(ev["time"] + 0.35, 3)
        assert ev["value"] == 19
        assert st.state["last"] >= ret_end  # hold timeline


def test_insert_overrun_error(monkeypatch):
    cache_dir = pathlib.Path("D:/agent-cache/MOT/tmp_tests")
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir) as td:
        clip = create_dummy_clip(td, monkeypatch)
        st = Story(clip, variant="full")
        P = st.P

        # Cảnh kết thúc ở mốc m1 (t=1.0s), voice kết thúc tại ~2.2s, tail=0.1s -> c_end ~2.3s
        st.screen("rec1", "start", ("m1", 0.1), [
            P("V1", 0, 1, at="m1")
        ], badge="SHORT SCENE", tail=0.1)

        # Chèn insert 1.6s -> chắc chắn vượt quá cảnh (2.28 + 1.6 > 2.3)
        with pytest.raises(ValueError, match="vượt quá cảnh kết thúc tại"):
            st.insert("counter", value=19, unit="người mua", dur=1.6)


def _run_chrome_check(index_html, events):
    js_errors = []
    launch_kwargs = {"headless": True}
    if CHROME_PATH:
        launch_kwargs["executable_path"] = CHROME_PATH

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})

        page.on("pageerror", lambda err: js_errors.append(f"JS ERROR: {err}"))
        page.on("console", lambda msg: js_errors.append(f"CONSOLE ERROR: {msg.text}") if msg.type == "error" and "ERR_FILE_NOT_FOUND" not in msg.text and "ERR_FAILED" not in msg.text else None)

        file_url = index_html.as_uri()
        page.goto(file_url, wait_until="load")

        # Tua timeline qua các thời điểm của từng insert để kích hoạt GSAP & onUpdate
        for ev in events:
            mid_t = ev["time"] + ev["dur"] * 0.5
            page.evaluate(f"""() => {{
                if (window.__timelines && window.__timelines.main) {{
                    window.__timelines.main.seek({mid_t}, false);
                }}
            }}""")
            page.wait_for_timeout(50)

        browser.close()
    return js_errors


def test_templates_render_without_js_errors(monkeypatch):
    """Dựng một trang index.html hoàn chỉnh với cả 4 loại inserts và kiểm tra không có lỗi JS trong Chrome."""
    cache_dir = pathlib.Path("D:/agent-cache/MOT/tmp_tests")
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir) as td:
        clip = create_dummy_clip(td, monkeypatch)
        st = Story(clip, variant="full")
        P = st.P

        # Cảnh 1: chứa route và counter
        st.screen("rec1", "start", "end", [
            P("V1", 0, 1, at="m1")
        ], badge="CẢNH 1", tail=4.0)

        st.insert("route", from_city="Vũng Tàu", to_city="Chicago", weight="24 TẤN",
                  stat="24.000 KGS · Tiêu đen", dur=1.6, sfx="whoosh")

        st.insert("counter", value=19, unit="người mua", label="Chiến dịch hồ tiêu",
                  sub="19 công ty tiềm năng xếp hạng sẵn", kicker="SỐ LIỆU THẬT", dur=1.6, sfx="ping")

        # Cảnh 2: chứa card_stack và compare
        st.screen("rec1", "start", "end", [
            P("V1", 1, 2, at="m1")
        ], badge="CẢNH 2", tail=4.2)

        st.insert("card_stack", title="Top người mua hồ tiêu", cards=[
            {"rank": 1, "title": "Harris Spice Asia Pacific", "reason": "10 lần nhập · $9,6M", "tag": "White Pepper"},
            {"rank": 2, "title": "St Charles Trading Inc", "reason": "Có email · phản hồi nhanh", "tag": "Chicago"}
        ], dur=1.6)

        st.insert("compare", title="Đơn giá theo nước xuất xứ", subtitle="Trung vị xuất sang Mỹ (USD/kg)",
                  before={"label": "Việt Nam", "value": 6.64, "unit": "$/kg", "sub": "14 dòng"},
                  after={"label": "Mexico", "value": 19.48, "unit": "$/kg", "sub": "11 dòng"},
                  delta="Tiêu Việt rẻ hơn $12,84/kg", direction="down", dur=1.6, sfx="pop")

        # Dựng index.html
        DUR = round(st.state["now"], 2)
        inserts_html = [ins["html"] for ins in st.inserts]
        css = "\n" + (KIT / "screendemo" / "templates" / "style.css").read_text(encoding="utf-8").strip("\n")
        css += "\n" + INS.get_inserts_css()
        hl, acc, bg = "#FBBF24", "#4F46E5", "#0B1020"
        vars_css = f":root{{--hl:{hl};--accent:{acc};--bg:{bg};--font-title:'Be Vietnam Pro';--font-sub:'IBM Plex Sans';--safe-top:150px;--safe-bottom:420px;--safe-right:140px;}}\n"
        tpl = (KIT / "screendemo" / "templates" / "template.html").read_text(encoding="utf-8")
        bands_html = '<div class="band-top"></div><div class="band-bottom"></div>'
        all_sections = [bands_html] + st.html + inserts_html
        fmt_js = (
            "function formatViNumber(n, d) {\n"
            "  if (isNaN(n)) return String(n);\n"
            "  const dec = (d !== undefined && d !== null) ? d : 0;\n"
            "  const parts = Number(n).toFixed(dec).split('.');\n"
            "  parts[0] = parts[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.');\n"
            "  return parts.join(',');\n"
            "}\n"
        )
        full_js = fmt_js + "\n" + "\n".join(st.js)
        out = (tpl.replace("/*FONTS*/", vars_css + css).replace("__W__", "1080").replace("__H__", "1920").replace("__D__", str(DUR))
               .replace("__HL__", hl).replace("__ACCENT__", acc).replace("__CAPTOP__", "auto").replace("__LAYOUT__", "fullbleed")
               .replace("Video marketing", "Test Video")
               .replace("__SECTIONS__", "\n".join(all_sections)).replace("__CAPTIONS__", "").replace("__JS__", full_js))

        index_html = clip / "index.html"
        index_html.write_text(out, encoding="utf-8")
        assert index_html.exists()

        # Chạy Playwright trong thread riêng để tránh xung đột với asyncio event loop từ các test khác
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_chrome_check, index_html, st.insert_events)
            js_errors = future.result()

        # Xác nhận 0 lỗi JS
        assert len(js_errors) == 0, f"Có lỗi JS khi render templates: {js_errors}"
