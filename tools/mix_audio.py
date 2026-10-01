"""Trộn âm thanh cuối cho video: giọng đọc + nhạc nền (tự lặp, fade, tự hạ khi có giọng) + hiệu ứng theo mốc.

Dùng: python mix_audio.py <cues.json> <ra.mp3>
cues.json (mẫu: kit/templates/audio-cues.template.json):
{
  "duration": 45,
  "voice": {"file": "audio/narration.mp3", "volume": 1.0},                     # có thể bỏ (video không lời)
  "bgm":   {"file": "bgm/mixkit/house-vibez.mp3", "volume": 0.22, "offset": 0, "start": 0,
            "fade_in": 0.8, "fade_out": 2.5, "duck": true},                      # duck = tự hạ nhạc khi có giọng
  "sfx":   [{"t": 7.1, "file": "sfx/mixkit/transition/swoosh-quick.mp3", "volume": 0.7}, ...]
}
SFX tự chuẩn hoá đỉnh về -6 dB trước khi nhân "volume" (0.3 = nhẹ, 0.6 = rõ, 1.0 = mạnh).
Đường dẫn file: tuyệt đối, hoặc tương đối với thư mục chứa cues.json, hoặc tương đối với kit/audio-library/.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import json, sys, pathlib, subprocess

LIB = pathlib.Path(__file__).resolve().parent.parent / "audio-library"
cues_path, out = pathlib.Path(sys.argv[1]).resolve(), sys.argv[2]
c = json.load(open(cues_path, encoding="utf-8")); D = float(c["duration"])

def find(f):
    for base in (pathlib.Path(), cues_path.parent, LIB):
        p = (base / f) if base != pathlib.Path() else pathlib.Path(f)
        if p.exists(): return str(p)
    raise SystemExit(f"không thấy file âm thanh: {f}")

PEAK_TARGET = -6.0   # dB: mọi SFX được đưa về cùng đỉnh này TRƯỚC khi nhân "volume" (tránh file gốc quá to)
from mix_audio_peak import peak_db   # đo đỉnh (dùng chung với sfx_audition.py)

flt, mix = [], []
idx = 0; args = []
v = c.get("voice")
if v:
    args += ["-i", find(v["file"])]; vi = idx; idx += 1
    flt.append(f"[{vi}:a]volume={v.get('volume', 1.0)},apad,atrim=0:{D},asplit=2[vo][vsc]"); mix.append("[vo]")
b = c.get("bgm")
if b:
    args += ["-stream_loop", "-1", "-i", find(b["file"])]; bi = idx; idx += 1
    off = float(b.get("offset", 0)); fi, fo = float(b.get("fade_in", 0.8)), float(b.get("fade_out", 2.5))
    st = float(b.get("start", 0)); L = D - st; ms = int(st * 1000)   # "start": nhạc vào muộn (giây)
    chain = (f"[{bi}:a]atrim={off}:{off + L},asetpts=PTS-STARTPTS,volume={b.get('volume', 0.2)},"
             f"afade=t=in:d={fi},afade=t=out:st={max(0, L - fo)}:d={fo},adelay={ms}|{ms},apad,atrim=0:{D}")
    if v and b.get("duck", True):
        flt.append(chain + "[bg0]")
        flt.append("[bg0][vsc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[bg]")
    else:
        flt.append(chain + "[bg]")
        if v: flt.append("[vsc]anullsink")
    mix.append("[bg]")
elif v:
    flt.append("[vsc]anullsink")
for k, s in enumerate(c.get("sfx", [])):
    fp = find(s["file"]); args += ["-i", fp]; si = idx; idx += 1
    ms = int(float(s["t"]) * 1000)
    gain = 10 ** ((PEAK_TARGET - peak_db(fp)) / 20) * float(s.get("volume", 0.7))   # chuẩn hoá đỉnh rồi mới nhân volume
    flt.append(f"[{si}:a]volume={gain:.4f},adelay={ms}|{ms}[s{k}]"); mix.append(f"[s{k}]")
if not mix: raise SystemExit("cues.json không có voice / bgm / sfx")
flt.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{D},alimiter=limit=0.95[out]")
cmd = ["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex", ";".join(flt), "-map", "[out]",
       "-ar", "44100", "-ac", "2", "-b:a", "192k", out]
subprocess.run(cmd, check=True)
print(f"xong: {out} — {len(c.get('sfx', []))} hiệu ứng, nhạc: {'có' if b else 'không'}, giọng: {'có' if v else 'không'}")
