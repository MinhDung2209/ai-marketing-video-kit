"""Chạy TOÀN BỘ quy trình của 1 dự án video bằng 1 lệnh: giọng → dựng → trộn âm → xem thử → render → kiểm tra.

Dùng (đứng ở bất kỳ đâu):
  python <kit>/tools/make_video.py <thư mục dự án>                    # chạy hết, ra <tên dự án>.mp4
  python <kit>/tools/make_video.py <dự án> --from mix                 # chỉ chạy lại từ bước trộn âm
  python <kit>/tools/make_video.py <dự án> --only snap --snap 1,8,20  # chỉ chụp vài khung xem thử
  python <kit>/tools/make_video.py <dự án> --redo-voice               # đọc lại TOÀN BỘ giọng (tốn tiền + phải nghe duyệt lại)

Các bước: voice · build · mix · snap · render · check
- voice: chỉ chạy khi chưa có audio/timing.json — giọng đã duyệt KHÔNG bị đọc lại ngầm. Đọc lại 1 câu: tts_script.py --only V3.
- check: in thời lượng, kích thước, độ to; cắt vài khung từ chính file MP4 ra _check_*.png để mở xem.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, os, pathlib, re, subprocess, sys, time

TOOLS = pathlib.Path(__file__).resolve().parent
STEPS = ["voice", "build", "mix", "snap", "render", "check"]

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--from", dest="start", choices=STEPS, default="voice", help="bắt đầu từ bước này")
ap.add_argument("--only", choices=STEPS, help="chỉ chạy đúng 1 bước")
ap.add_argument("--redo-voice", action="store_true", help="đọc lại toàn bộ giọng dù đã có")
ap.add_argument("--snap", default="1,5,12,25", help="các giây chụp xem thử")
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--out", help="tên file MP4 (mặc định <tên thư mục>.mp4)")
a = ap.parse_args()

P = pathlib.Path(a.project).resolve()
if not (P / "voice.json").exists() or not (P / "build.py").exists():
    sys.exit(f"Không phải thư mục dự án (thiếu voice.json / build.py): {P}\nTạo mới: python {TOOLS}/new_project.py <thư mục>")
out = a.out or f"{P.name}.mp4"
todo = [a.only] if a.only else STEPS[STEPS.index(a.start):]

def run(label, cmd):
    print(f"\n▶ {label}\n  {' '.join(str(c) for c in cmd)}", flush=True)
    t = time.time()
    r = subprocess.run([str(c) for c in cmd], cwd=P, env={**os.environ, "VIDEOKIT_TOOLS": str(TOOLS)})
    if r.returncode:
        sys.exit(f"✗ {label} lỗi (mã {r.returncode}) — sửa rồi chạy tiếp: make_video.py {a.project} --from {step}")
    print(f"  ✓ {time.time() - t:.0f}s")

for step in todo:
    if step == "voice":
        if (P / "audio" / "timing.json").exists() and not a.redo_voice:
            print("\n• voice: đã có audio/timing.json → giữ giọng đã duyệt (đọc lại: --redo-voice hoặc tts_script.py --only Vx)")
            continue
        run("Giọng đọc (Gemini-TTS)", [sys.executable, TOOLS / "tts_script.py", "voice.json", "audio"])
        print("  ⚠ Nghe lại audio/*.mp3 trước khi đăng — máy không tự đánh giá được giọng.")
    elif step == "build":
        run("Dựng cảnh + phụ đề + mốc hiệu ứng", [sys.executable, "build.py"])
    elif step == "mix":
        run("Trộn âm (giọng + nhạc + hiệu ứng)", [sys.executable, TOOLS / "mix_audio.py", "cues.json", "assets/final_audio.mp3"])
    elif step == "snap":
        run("Chụp khung xem thử", [sys.executable, TOOLS / "render.py", ".", "--snap", a.snap])
        print("  → mở các file _snap_*.png trong thư mục dự án để xem")
    elif step == "render":
        run(f"Render MP4 ({a.fps} fps)", [sys.executable, TOOLS / "render.py", ".", "--fps", a.fps,
                                          "--audio", "assets/final_audio.mp3", "--out", out])
    elif step == "check":
        mp4 = P / out
        if not mp4.exists(): sys.exit(f"✗ chưa có {mp4} — chạy bước render trước")
        info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,codec_name",
                               "-of", "compact=p=0:nk=0", str(mp4)], capture_output=True, text=True).stdout.strip()
        vol = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        peak = re.search(r"max_volume: (-?[\d.]+)", vol); mean = re.search(r"mean_volume: (-?[\d.]+)", vol)
        dur = float(re.search(r"duration=([\d.]+)", info).group(1))
        for t in [1, dur * 0.25, dur * 0.5, dur * 0.75, dur - 1]:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.1f}", "-i", str(mp4), "-frames:v", "1",
                            "-vf", "scale=360:-2", str(P / f"_check_{t:05.1f}.png")])
        print(f"\n▶ Kiểm tra {mp4.name}\n  {info.replace(chr(10), ' | ')}")
        if peak:
            pk = float(peak.group(1))
            print(f"  âm lượng: đỉnh {pk} dB, trung bình {mean.group(1)} dB" + ("  ⚠ đỉnh > -1 dB, dễ vỡ tiếng" if pk > -1 else "  ✓"))
        print("  → mở _check_*.png (cắt từ chính file MP4) + xem trên điện thoại thật — checklist: docs/08")

print(f"\n✅ Xong: {P / out}" if "render" in todo else "\n✅ Xong các bước đã chọn")
