"""Chạy cả luồng hậu kỳ 1 clip demo sản phẩm: dựng (story.py) → trộn tiếng → chuẩn -14 LUFS → render → kiểm.

  python KIT/screendemo/produce.py <clip>                       # mọi bản trong clip.json → final/<slug>-<hậu tố>.mp4
  python KIT/screendemo/produce.py <clip> --only demo           # 1 bản
  python KIT/screendemo/produce.py <clip> --snap 3,40,120       # chỉ dựng + chụp khung để soát (không render)
  python KIT/screendemo/produce.py <clip> --build               # chỉ dựng index.html + cues (xem độ dài từng cảnh)
  python KIT/screendemo/produce.py <clip> --qa                  # soát mọi mốc trên bản đã dựng, không dựng lại

Render LẦN LƯỢT từng bản (render tốn RAM — máy yếu thì đóng bớt app / tab Chrome), ghi ra file tạm rồi mới đổi tên,
nên lỡ bị dừng giữa chừng thì bản cũ vẫn còn nguyên. Xong mỗi bản in độ dài + âm lượng đo lại."""
import argparse, json, os, pathlib, re, shutil, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent; KIT = HERE.parent; TOOLS = KIT / "tools"
sys.path.insert(0, str(HERE))
from config import cfg as _cfg


def run(*a, **kw):
    print("  $", " ".join(str(x) for x in a)[:160], flush=True)
    return subprocess.run([str(x) for x in a], check=True, stdin=subprocess.DEVNULL, **kw)   # ffmpeg chạy nền mà đọc stdin → treo


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("clip"); ap.add_argument("--only", default="")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--snap", default=""); mode.add_argument("--build", action="store_true")
    mode.add_argument("--qa", "--snap-cues", action="store_true", help="contact sheet + checklist từ bản đã dựng; không chạy story/TTS")
    ap.add_argument("--qa-source", choices=("auto", "video", "build"), default="auto",
                    help="QA: auto dùng MP4 có sẵn, nếu chưa có thì chụp HTML; video không mở Chrome; build soát HTML hiện tại")
    ap.add_argument("--fps", type=int, default=30); ap.add_argument("--lufs", type=float, default=-14)
    a = ap.parse_args()
    clip = pathlib.Path(a.clip).resolve(); cfg = json.loads((clip / "clip.json").read_text(encoding="utf-8"))
    env = dict(os.environ); c = _cfg()
    if c.get("chrome"): env.setdefault("VIDEOKIT_CHROME", c["chrome"])
    if c.get("ffmpeg"): env["PATH"] = str(pathlib.Path(c["ffmpeg"]).parent) + os.pathsep + env.get("PATH", "")
    py = sys.executable
    variants = cfg.get("variants", {"full": "full"})
    names = [v for v in variants if not a.only or v in a.only.split(",")]
    if not names: raise SystemExit(f"không có bản {a.only!r} — clip.json có: {', '.join(variants)}")
    if a.qa:
        from qa import review
        for v in names:
            d = clip if v == "full" else clip / v
            video = clip / "final" / f"{cfg['slug']}-{variants[v]}.mp4"
            review(d, clip, video, source=a.qa_source, env=env)
        return
    (clip / "final").mkdir(exist_ok=True)
    for v in names:
        d = clip if v == "full" else clip / v
        print(f"\n=== bản {v}")
        run(py, "-X", "utf8", clip / "story.py", env={**env, "VARIANT": v}, cwd=clip)
        if a.build: continue
        if a.snap:
            run(py, "-X", "utf8", TOOLS / "render.py", d, "--snap", a.snap, env=env); continue
        run(py, "-X", "utf8", TOOLS / "mix_audio.py", d / "cues.json", d / "final_audio.mp3", env=env, cwd=clip)
        loud = d / "final_audio_14lufs.mp3"
        run("ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", d / "final_audio.mp3", "-af", f"loudnorm=I={a.lufs}:TP=-1.5:LRA=11",
            "-ar", "44100", "-b:a", "192k", loud, env=env)
        out = clip / "final" / f"{cfg['slug']}-{variants[v]}.mp4"; tmp = out.with_suffix(".tmp.mp4")
        run(py, "-X", "utf8", TOOLS / "render.py", d, "--fps", a.fps, "--audio", loud, "--out", tmp, env=env)
        shutil.move(tmp, out)
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                             capture_output=True, text=True, env=env).stdout.strip()
        m = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", str(out), "-af", "ebur128=peak=true", "-f", "null", "-"],
                           capture_output=True, text=True, env=env).stderr
        i = re.findall(r"I:\s+(-?[\d.]+) LUFS", m); p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", m)
        print(f"✅ {out} · {float(dur):.1f}s · {i[-1] if i else '?'} LUFS · đỉnh {p[-1] if p else '?'} dB")


if __name__ == "__main__":
    main()
