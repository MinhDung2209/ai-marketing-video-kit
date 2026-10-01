"""Tạo file NGHE THỬ nhiều hiệu ứng âm thanh để người duyệt chọn (người làm video không tự nghe được thì dùng cái này).

Mỗi ứng viên: chuẩn hoá đỉnh về -6 dB × volume, phát `--repeat` lần cách nhau `--step` giây (giống nhịp thật trong
video), rồi nghỉ `--gap` giây trước ứng viên sau. In ra thứ tự + mốc thời gian để người nghe đối chiếu.

Dùng: python sfx_audition.py ra.mp3 sfx/pixabay/click-soft.mp3 sfx/uisfx/soft/check.mp3 ... [--repeat 4 --step 0.5 --gap 1.5 --volume 0.5]
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, pathlib, subprocess
from mix_audio_peak import peak_db  # noqa: E402  (dùng chung hàm đo đỉnh)

LIB = pathlib.Path(__file__).resolve().parent.parent / "audio-library"
ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("files", nargs="+")
ap.add_argument("--repeat", type=int, default=4); ap.add_argument("--step", type=float, default=0.5)
ap.add_argument("--gap", type=float, default=1.5); ap.add_argument("--volume", type=float, default=0.5)
a = ap.parse_args()
args, flt, mix, t, k = [], [], [], 0.5, 0
for n, f in enumerate(a.files, 1):
    p = f if pathlib.Path(f).exists() else str(LIB / f)
    gain = 10 ** ((-6.0 - peak_db(p)) / 20) * a.volume
    print(f"{n}. {t:5.1f}s  {f}")
    for r in range(a.repeat):
        args += ["-i", p]; ms = int((t + r * a.step) * 1000)
        flt.append(f"[{k}:a]volume={gain:.4f},adelay={ms}|{ms}[s{k}]"); mix.append(f"[s{k}]"); k += 1
    t += a.repeat * a.step + a.gap
flt.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,apad,atrim=0:{t},alimiter=limit=0.95[o]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex", ";".join(flt), "-map", "[o]", "-b:a", "192k", a.out], check=True)
print("xong:", a.out)
