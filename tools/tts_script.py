"""Đọc file kịch bản giọng (JSON) bằng Gemini-TTS → mỗi câu 1 mp3 + narration.mp3 ghép sẵn + timing.json.

Dùng: python tts_script.py <kich-ban.json> <thư mục ra> [--voice Kore] [--model gemini-2.5-pro-tts]
Kịch bản: xem kich-ban-giong-v1.json (profile + direction từng câu + thẻ [short pause]... trong text).
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import sys, os, json, base64, subprocess, argparse, requests
from gcp import token_and_project, config

ap = argparse.ArgumentParser()
ap.add_argument("script"); ap.add_argument("out"); ap.add_argument("--voice"); ap.add_argument("--model")
ap.add_argument("--only", help="chỉ đọc lại các câu này (vd V5,V7); câu khác dùng lại mp3 đã có")
a = ap.parse_args()
sc = json.load(open(a.script, encoding="utf-8"))
cfg = config()
model = a.model or sc.get("model") or cfg.get("tts_model", "gemini-3.1-flash-tts-preview")
voice = a.voice or sc.get("voice") or cfg.get("tts_voice", "Kore")
gap = float(sc.get("gap_seconds", 0.35)); os.makedirs(a.out, exist_ok=True)
t, p = token_and_project(); H = {"Authorization": f"Bearer {t}", "x-goog-user-project": p}

def dur(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", f]).decode().strip())

meta, start = [], 0.3
only = set(a.only.split(",")) if a.only else None
for ln in sc["lines"]:
    f = os.path.join(a.out, f"{ln['id']}.mp3")
    if only is not None and ln["id"] not in only and os.path.exists(f):   # giữ nguyên câu đã duyệt
        d = round(dur(f), 2); meta.append({"id": ln["id"], "file": os.path.basename(f), "start": round(start, 2), "dur": d, "text": ln["text"], **({"caption": ln["caption"]} if ln.get("caption") else {})})
        print(f"{ln['id']}  {start:5.2f}s  +{d:.2f}s  (giữ)", flush=True); start += d + gap; continue
    prompt = sc["profile"] + " " + ln.get("direction", "")
    # Bộ lọc an toàn của Google đôi khi chặn nhầm ngẫu nhiên (400 "violates ... usage guidelines",
    # gặp 30/09 ở câu L4 dù 2 lần trước đọc được) → thử lại tối đa 3 lần.
    # Chuỗi thử khi bộ lọc chặn nhầm: 2 lần hồ sơ chính → 2 lần profile_fallback → 1 lần KHÔNG kèm lời đạo diễn
    # (không prompt thì luôn qua, nhưng mất cảm xúc đạo diễn — nghe lại câu đó, nếu cần thì đổi vài chữ và đọc lại --only).
    for attempt in range(5):
        if attempt in (2, 3) and sc.get("profile_fallback"):
            prompt = sc["profile_fallback"] + " " + ln.get("direction", "")
        inp = {"prompt": prompt, "text": ln["text"]} if attempt < 4 else {"text": ln["text"]}
        r = requests.post("https://texttospeech.googleapis.com/v1/text:synthesize", headers=H, json={
            "input": inp,
            "voice": {"languageCode": sc.get("language") or cfg.get("tts_language", "vi-VN"), "name": voice, "modelName": model},
            "audioConfig": {"audioEncoding": "MP3", "sampleRateHertz": 44100}})
        if r.ok or "usage guidelines" not in r.text:
            if r.ok and attempt == 4: print(f"  {ln['id']}: ⚠ đọc KHÔNG kèm lời đạo diễn (bộ lọc chặn) — nghe lại câu này", flush=True)
            break
        print(f"  {ln['id']}: bộ lọc chặn nhầm, thử lại ({attempt + 1}/5)", flush=True)
    if not r.ok:
        hint = (" → Bộ lọc an toàn của Google chặn câu này. Đổi vài chữ trong câu (vd bỏ tên riêng, đổi từ nhấn mạnh) "
                "rồi chạy lại với --only " + ln["id"]) if "usage guidelines" in r.text else ""
        sys.exit(f"{ln['id']}: lỗi {r.status_code} {r.text[:300]}{hint}")
    f = os.path.join(a.out, f"{ln['id']}.mp3"); open(f, "wb").write(base64.b64decode(r.json()["audioContent"]))
    d = round(dur(f), 2); meta.append({"id": ln["id"], "file": os.path.basename(f), "start": round(start, 2), "dur": d, "text": ln["text"], **({"caption": ln["caption"]} if ln.get("caption") else {})})
    print(f"{ln['id']}  {start:5.2f}s  +{d:.2f}s", flush=True); start += d + gap

total = round(start + 1.0, 2)
inp, flt = [], []
for i, m in enumerate(meta):
    inp += ["-i", os.path.join(a.out, m["file"])]; ms = int(m["start"] * 1000); flt.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
flt.append("".join(f"[a{i}]" for i in range(len(meta))) + f"amix=inputs={len(meta)}:normalize=0,apad=whole_dur={total}[o]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inp, "-filter_complex", ";".join(flt), "-map", "[o]", "-t", str(total),
                "-ar", "44100", "-b:a", "192k", os.path.join(a.out, "narration.mp3")], check=True)
json.dump({"model": model, "voice": voice, "total": total, "lines": meta},
          open(os.path.join(a.out, "timing.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"xong: {a.out}/narration.mp3 — tổng {total}s · {model} · {voice}")
