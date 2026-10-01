"""Render trang HTML + GSAP (định dạng giống HyperFrames) thành MP4 bằng Chrome trên máy + FFmpeg.

Không dùng gói npm hyperframes (bị chặn quyền chạy code ngoài) — tự làm phần runtime tối thiểu:
- window.__timelines["main"] là GSAP timeline paused; mỗi khung hình: tl.seek(t)
- phần tử có data-start/data-duration chỉ hiện trong cửa sổ thời gian của nó (như runtime HyperFrames)

Dùng:
  python render.py <thư mục dự án> --snap 1,5,12      # chụp vài khung hình PNG để kiểm tra
  python render.py <thư mục dự án> --fps 30           # render đủ ra out.mp4 (kèm assets/narration.mp3)
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, os, pathlib, shutil, subprocess, sys
from playwright.sync_api import sync_playwright

def find_chrome():
    """Chrome trên máy: biến VIDEOKIT_CHROME → chỗ cài thường gặp (Windows/macOS/Linux) → None = Chromium của Playwright."""
    env = os.environ.get("VIDEOKIT_CHROME")
    if env:
        if not pathlib.Path(env).exists(): raise SystemExit(f"VIDEOKIT_CHROME trỏ tới file không tồn tại: {env}")
        return env
    for c in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]:
        if pathlib.Path(c).exists(): return c
    for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if shutil.which(n): return shutil.which(n)
    return None   # cần: python -m playwright install chromium
SEEK_JS = """async (t) => {
  const tl = window.__timelines && window.__timelines.main;
  if (!tl) return 'no timeline';
  tl.seek(t, false);
  document.querySelectorAll('[data-start]').forEach(el => {
    if (el.id === 'root' || el.tagName === 'AUDIO') return;
    const s = parseFloat(el.dataset.start), d = parseFloat(el.dataset.duration);
    el.style.visibility = (t >= s && t < s + d) ? 'visible' : 'hidden';
  });
  // Video trong cảnh: tua tới đúng khung. data-rate = tốc độ phát (0.75 = chậm); data-offset / data-end = đoạn được dùng;
  // hết clip thì giữ khung cuối.
  const waits = [];
  document.querySelectorAll('video').forEach(v => {
    const host = v.closest('[data-start]'); if (!host) return;
    const s = parseFloat(host.dataset.start), rate = parseFloat(v.dataset.rate || '1');
    const off = parseFloat(v.dataset.offset || '0');                                        // data-offset: bắt đầu từ giây này của clip
    const end = Math.min((v.duration || 0) - 0.05, parseFloat(v.dataset.end || '1e9'));   // data-end: bỏ đoạn lỗi cuối clip
    const local = Math.max(off, Math.min(end, off + (t - s) * rate));
    if (Math.abs(v.currentTime - local) > 0.001) {
      waits.push(new Promise(r => { v.addEventListener('seeked', r, { once: true }); setTimeout(r, 3000); }));
      v.currentTime = local;
    }
  });
  await Promise.all(waits);
  return 'ok';
}"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--snap", default=""); ap.add_argument("--out", default="out.mp4")
    ap.add_argument("--audio", default="assets/narration.mp3", help="file âm thanh cuối (tương đối với thư mục dự án)")
    a = ap.parse_args()
    proj = pathlib.Path(a.project).resolve(); html = proj / "index.html"
    src = html.read_text(encoding="utf-8")
    W = int(src.split('data-width="')[1].split('"')[0]); H = int(src.split('data-height="')[1].split('"')[0])
    DUR = float(src.split('data-composition-id="main"')[1].split('data-duration="')[1].split('"')[0])
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=find_chrome(), headless=True)
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.add_init_script("window.__timelines = {};")
        pg.goto(html.as_uri(), wait_until="networkidle")
        # như runtime HyperFrames: gán kích thước pixel cho khung gốc (data-width/height)
        pg.evaluate("""() => { const r = document.querySelector('[data-composition-id="main"]');
          r.style.width = r.dataset.width + 'px'; r.style.height = r.dataset.height + 'px'; }""")
        pg.evaluate("document.fonts.ready")
        # chờ mọi <video> tải xong metadata (để biết duration)
        pg.evaluate("""() => Promise.all([...document.querySelectorAll('video')].map(v => v.readyState >= 1 ? 0 :
            new Promise(r => { v.addEventListener('loadedmetadata', r, { once: true }); v.load(); setTimeout(r, 8000); })))""")
        pg.wait_for_timeout(500)
        if a.snap:
            for t in [float(x) for x in a.snap.split(",")]:
                print(t, pg.evaluate(SEEK_JS, t))
                pg.screenshot(path=str(proj / f"_snap_{t:05.1f}.png"))
            b.close(); return
        n = int(DUR * a.fps)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(a.fps), "-i", "-",
                               "-i", str(proj / a.audio), "-map", "0:v", "-map", "1:a",
                               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                               "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(proj / a.out)],
                              stdin=subprocess.PIPE)
        for i in range(n):
            pg.evaluate(SEEK_JS, i / a.fps)
            ff.stdin.write(pg.screenshot(type="jpeg", quality=95))
            if i % (a.fps * 5) == 0: print(f"{i / a.fps:.0f}s / {DUR:.0f}s", flush=True)
        ff.stdin.close(); ff.wait(); b.close()
        print("xong:", proj / a.out)

if __name__ == "__main__":
    sys.exit(main())
