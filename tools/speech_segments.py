"""Tách 1 file giọng đọc thành các CỤM NÓI (giữa các khoảng lặng) bằng ffmpeg silencedetect — để canh hoạt ảnh
đúng lúc giọng nói tới 1 cụm từ (chính xác hơn ước lượng theo số ký tự; không cần cài Whisper).

Dùng:  from speech_segments import segments; segs = segments("audio/V2.mp3")  → [(0.28, 1.38), (1.68, 3.17), ...]
       python speech_segments.py audio/V2.mp3            → in danh sách để đối chiếu với lời
Tham số: noise (ngưỡng lặng, mặc định -35 dB), min_gap (khoảng lặng ngắn hơn thì coi là cùng cụm, mặc định 0.2s).
Đo 30/09 (câu V2 video v2): ước lượng theo ký tự lệch ~1,2s; theo khoảng lặng khớp giọng.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import re, subprocess, sys

def segments(path, noise=-35, min_gap=0.2):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", f"silencedetect=noise={noise}dB:d={min_gap}",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                         str(path)]).decode().strip())
    st = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", out)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", out)]
    segs, cur = [], 0.0
    for s, e in zip(st, en):
        if s - cur > 0.05: segs.append((round(cur, 2), round(s, 2)))
        cur = e
    if dur - cur > 0.05: segs.append((round(cur, 2), round(dur, 2)))
    return segs

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for i, (a, b) in enumerate(segments(sys.argv[1])): print(f"{i}: {a:6.2f} → {b:6.2f}")
