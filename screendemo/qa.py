"""Frame QA từ timeline đã dựng; học cách cắt khung của sheet.py, không quay/TTS/dựng lại.

MP4 có sẵn: FFmpeg lấy đúng khung (không Chrome). Chưa có MP4: dùng SEEK_JS của tools/render.py.
Chỉ ghi vào <bản>/qa/. Checklist là việc kiểm bằng mắt, không tự đánh dấu đạt.
"""
import io
import json
import math
import pathlib
import subprocess
import sys
from html.parser import HTMLParser

from PIL import Image, ImageDraw, ImageFont


class Timeline(HTMLParser):
    """Đọc section + thời gian của video bao trong, giữ cả đoạn tua nhanh/đứng hình."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, html):
        super().__init__()
        self.stack = []
        self.scenes = []
        self.size = (1080, 1920)
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("data-composition-id") == "main":
            self.size = (int(a["data-width"]), int(a["data-height"]))
        scene = next((item[2] for item in reversed(self.stack) if item[2] is not None), None)
        if tag == "section" and "data-start" in a:
            scene = {"s": float(a["data-start"]), "d": float(a["data-duration"]), "videos": []}
            self.scenes.append(scene)
        if tag == "video" and scene is not None and "/screen/" in a.get("src", ""):
            host = a if "data-start" in a else next(
                (item[1] for item in reversed(self.stack) if "data-start" in item[1]), None)
            if host:
                scene["videos"].append({"src": a["src"], "s": float(host["data-start"]),
                                        "d": float(host["data-duration"]),
                                        "r0": float(a.get("data-offset", a.get("data-media-start", 0))),
                                        "r1": float(a.get("data-end", "inf")),
                                        "rate": float(a.get("data-rate", a.get("data-playback-rate", 1)))})
        if tag not in self.VOID: self.stack.append((tag, a, scene))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def cue_samples(timeline, base):
    """Quy đổi mốc bản quay → giờ bản dựng bằng offset/rate của từng đoạn, không ước lượng theo lời."""
    samples = {}
    marks = {}

    def add(t, label):
        samples.setdefault(round(t, 4), []).append(label)

    for i, scene in enumerate(timeline.scenes, 1):
        start, dur = scene["s"], scene["d"]
        if dur <= 0: continue
        end = start + dur
        inset = min(0.5, dur / 4)
        add(start + inset, f"scene {i} first second")
        add(end - inset, f"scene {i} last second")
        seen = set()
        for v in scene["videos"]:
            path = (base / v["src"]).parent / "marks.json"
            if path not in marks:
                marks[path] = json.loads(path.read_text(encoding="utf-8"))["marks"]
            for m in marks[path]:
                if "box" not in m: continue
                if v["rate"] <= 0: raise ValueError("tốc độ video phải lớn hơn 0 để quy đổi mốc QA")
                rt = float(m["t"])
                # data-end tạo khoảng giữ khung: không đưa các mốc đã bị cắt vào QA.
                last = min(v["r1"], v["r0"] + v["d"] * v["rate"])
                if not v["r0"] - 1e-6 <= rt <= last + 1e-6: continue
                t = max(start, min(end - 0.001, v["s"] + (rt - v["r0"]) / v["rate"]))
                key = (str(path), m["name"], rt)
                if key in seen: continue
                seen.add(key)
                kind = "ink" if m.get("ink", True) else "focus"
                label = f"scene {i} {kind} {path.parent.name}/{m['name']}"
                add(t, label)
                # Cả khung tại mốc lẫn khi camera/mực đã hiện; không bỏ lỗi lúc chuyển động.
                add(min(end - 0.001, t + 0.35), label + " settled")
    if not samples: raise ValueError("index.html không có cảnh <section> có thời gian để soát")
    return sorted(samples.items())


def video_frames(video, samples, env):
    """Giống sheet.py: seek trực tiếp FFmpeg từng mốc, trả ảnh qua RAM để không rải file tạm."""
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                           check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env)
    duration = float(probe.stdout.strip())
    if samples[-1][0] >= duration:
        raise ValueError(f"MP4 chỉ dài {duration:.3f}s, mốc QA cuối {samples[-1][0]:.3f}s; dùng --qa-source build")
    for t, _ in samples:
        p = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(t), "-i", str(video),
                            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                           check=True, capture_output=True, stdin=subprocess.DEVNULL, env=env)
        with Image.open(io.BytesIO(p.stdout)) as im: yield im.convert("RGB")


def build_frames(build, timeline, samples, env):
    """Tái dùng runtime snapshot, không gọi story.py và không xuất video."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
    from render import SEEK_JS, find_chrome
    from playwright.sync_api import sync_playwright
    # find_chrome đọc env tiến trình; cấu hình của produce đã có trong env riêng.
    chrome = env.get("VIDEOKIT_CHROME") or find_chrome()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome, headless=True)
        try:
            page = browser.new_page(viewport=dict(zip(("width", "height"), timeline.size)), device_scale_factor=1)
            page.add_init_script("window.__timelines = {};")
            page.goto((build / "index.html").as_uri(), wait_until="networkidle")
            page.evaluate("""() => { const r = document.querySelector('[data-composition-id="main"]');
                r.style.width = r.dataset.width + 'px'; r.style.height = r.dataset.height + 'px'; }""")
            page.evaluate("document.fonts.ready")
            page.evaluate("""() => Promise.all([...document.querySelectorAll('video')].map(v => v.readyState >= 1 ? 0 :
                new Promise(r => { v.addEventListener('loadedmetadata', r, {once:true}); v.load(); setTimeout(r,8000); })))""")
            page.wait_for_timeout(500)
            for t, _ in samples:
                result = page.evaluate(SEEK_JS, t)
                if result == "no timeline": raise ValueError("index.html không có timeline GSAP main")
                with Image.open(io.BytesIO(page.screenshot(type="png"))) as im: yield im.convert("RGB")
        finally:
            browser.close()


def overlay(frame):
    """Vùng chết phải 170 / dưới 300 tính theo khung chuẩn 1080×1920."""
    layer = Image.new("RGBA", frame.size)
    draw = ImageDraw.Draw(layer)
    w, h = frame.size
    right, bottom = round(w * 170 / 1080), round(h * 300 / 1920)
    draw.rectangle((w - right, 0, w - 1, h - 1), fill=(255, 30, 30, 55), outline=(255, 50, 50, 220), width=3)
    draw.rectangle((0, h - bottom, w - 1, h - 1), fill=(255, 140, 0, 55), outline=(255, 150, 0, 220), width=3)
    return Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")


def review(build, base, video, source="auto", env=None, output=None):
    """output phục vụ kiểm thử; CLI luôn chỉ ghi vào thư mục qa/ của bản đang soát."""
    html_path = build / "index.html"
    html = html_path.read_text(encoding="utf-8")
    timeline = Timeline(html)
    samples = cue_samples(timeline, base)
    use_video = source == "video" or (source == "auto" and video.exists())
    if use_video and not video.exists(): raise FileNotFoundError(f"chưa có MP4: {video}; dùng --qa-source build")
    frames = video_frames(video, samples, env) if use_video else build_frames(build, timeline, samples, env or {})
    cols, tw, th, footer = 5, 270, 480, 42
    sheet = Image.new("RGB", (cols * tw, math.ceil(len(samples) / cols) * (th + footer)), "#161b22")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=14)
    for i, (frame, (t, labels)) in enumerate(zip(frames, samples, strict=True)):
        if frame.size != timeline.size: raise ValueError(f"khung MP4 {frame.size} khác bản dựng {timeline.size}")
        tile = overlay(frame).resize((tw, th), Image.Resampling.LANCZOS)
        x, y = (i % cols) * tw, (i // cols) * (th + footer)
        sheet.paste(tile, (x, y))
        draw.text((x + 5, y + th + 2), f"{i + 1:02d} | {t:.3f}s", font=font, fill="white")
        draw.text((x + 5, y + th + 21), labels[0][:34], font=font, fill="#b8c3d1")
    notes = []
    if timeline.size != (1080, 1920): notes.append(f"Khung {timeline.size}; lớp phủ được đổi tỉ lệ từ 1080×1920.")
    if use_video:
        inputs = [html_path, *(base / "assets/screen").glob("*/marks.json")]
        newest = max(path.stat().st_mtime for path in inputs)
        if newest > video.stat().st_mtime:
            notes.append("CẢNH BÁO: HTML/mốc quay mới hơn MP4. Ảnh đang soát MP4 cũ; chạy --qa-source build để soát sửa đổi.")
    lines = ["# Frame QA", "", f"Nguồn: `{video if use_video else html_path}`", "",
             f"{len(samples)} khung; {len(timeline.scenes)} cảnh. Đỏ = phải 170px; cam = dưới 300px (1080×1920).",
             "Ảnh nhỏ để rà toàn cảnh; dùng --snap tại mốc nghi ngờ để đọc chữ ở kích thước đầy đủ.",
             "Checklist để người/agent mở ảnh kiểm; chưa tự động chứng nhận đạt.", "", *notes, "",
             "- [ ] Chữ/email/con số không bị cắt ở mép khung 1080×1920 hoặc mép camera phóng.",
             "- [ ] Phụ đề .cap không che con số đang khoanh hoặc CTA.",
             "- [ ] Nội dung quan trọng không lọt vùng chết TikTok/Reels: phải 170px / dưới 300px (đã phủ màu).",
             "- [ ] Không trùng logo góc trên phải (#logo-goc) với logo_end ở cảnh kết.", "",
             "| Ô | Giây bản dựng | Cảnh / mốc |", "| --- | --- | --- |"]
    for i, (t, labels) in enumerate(samples, 1):
        lines.append(f"| {i} | {t:.4f} | {'; '.join(labels).replace('|', '/')} |")
    out = output if output is not None else build / "qa"
    out.mkdir(parents=True, exist_ok=True)
    sheet.save(out / "contact-sheet.jpg", quality=92)
    (out / "checklist.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"QA: {len(samples)} frames / {len(timeline.scenes)} scenes · {'MP4 (no Chrome)' if use_video else 'HTML snapshots'}", flush=True)
    for note in notes: print(note, flush=True)
    print(out / "contact-sheet.jpg", flush=True)
    print(out / "checklist.md", flush=True)
    return out
