"""Đo đỉnh âm lượng (dB) của 1 file bằng ffmpeg volumedetect — dùng chung cho mix_audio.py và sfx_audition.py."""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import subprocess
_cache = {}
def peak_db(path, default=-6.0):
    if path not in _cache:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        m = [l for l in out.splitlines() if "max_volume" in l]
        _cache[path] = float(m[0].split("max_volume:")[1].split("dB")[0]) if m else default
    return _cache[path]
