"""Tạo nhạc nền (không lời) bằng Google Lyria trên Vertex AI (model lyria-002, ~32 giây/lần).

Dùng: python lyria_bgm.py "<mô tả nhạc bằng tiếng Anh>" <ra.wav> [--negative "vocals, ..."] [--seed 42]
Muốn dài hơn 32s: dùng mix_audio.py (tự lặp + fade), hoặc tạo 2 đoạn rồi nối.
Đo 30/09/2026: gọi thành công bằng service account dự án, ra WAV 32,8s.
Mẹo prompt: thể loại + nhạc cụ + cảm xúc + BPM + "instrumental, no vocals".
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, base64, requests
from gcp import token_and_project

ap = argparse.ArgumentParser()
ap.add_argument("prompt"); ap.add_argument("out")
ap.add_argument("--negative", default="vocals, singing, speech, heavy distortion")
ap.add_argument("--seed", type=int)
a = ap.parse_args()
t, p = token_and_project()
inst = {"prompt": a.prompt, "negative_prompt": a.negative}
if a.seed is not None: inst["seed"] = a.seed
r = requests.post(f"https://us-central1-aiplatform.googleapis.com/v1/projects/{p}/locations/us-central1/publishers/google/models/lyria-002:predict",
                  headers={"Authorization": f"Bearer {t}"}, json={"instances": [inst], "parameters": {}}, timeout=300)
if not r.ok: raise SystemExit(f"{r.status_code} {r.text[:400]}")
open(a.out, "wb").write(base64.b64decode(r.json()["predictions"][0]["bytesBase64Encoded"]))
print("đã tạo", a.out)
