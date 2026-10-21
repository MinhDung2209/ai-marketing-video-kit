"""Chép lời + mốc thời gian của clip gốc (TikTok/FB/YouTube/báo) bằng Gemini (Vertex, cùng khoá với TTS)
→ tìm đúng đoạn "đắt" để chèn tiếng gốc (news_video: video {"sound": 1}).

  python tools/clip_transcribe.py <clip.mp4> [<clip2.mp4> ...]   → <clip>.transcript.json + in ra màn hình
  [{"start": 3.2, "end": 6.0, "speaker": "người hát", "text": "...", "kind": "hát|nói|nhạc|ồn"}]
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import base64, json, pathlib, re, subprocess, sys, requests
from gcp import token_and_project, config

MODEL = config().get("transcribe_model", "gemini-2.5-flash")
PROMPT = ("Chép lại TOÀN BỘ âm thanh trong clip tiếng Việt này theo từng cụm ngắn (≤ 6 giây), đúng nguyên văn kể cả nói ngọng/giọng địa phương. "
          "Trả về JSON array, mỗi phần tử {\"start\": giây, \"end\": giây, \"speaker\": mô tả ngắn người nói, "
          "\"text\": lời, \"kind\": \"hát\"|\"nói\"|\"nhạc\"|\"ồn\"}. Đoạn chỉ có nhạc/tiếng ồn cũng ghi (text mô tả ngắn). Chỉ trả JSON.")

def transcribe(clip):
    mp3 = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(clip), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", "-f", "mp3", "-"],
                         capture_output=True, check=True).stdout
    t, p = token_and_project()
    url = f"https://aiplatform.googleapis.com/v1/projects/{p}/locations/global/publishers/google/models/{MODEL}:generateContent"
    r = requests.post(url, headers={"Authorization": f"Bearer {t}"}, timeout=300, json={
        "contents": [{"role": "user", "parts": [{"inlineData": {"mimeType": "audio/mp3", "data": base64.b64encode(mp3).decode()}}, {"text": PROMPT}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0}})
    if not r.ok: raise SystemExit(f"{clip.name}: Gemini lỗi {r.status_code} {r.text[:300]}")
    txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(re.sub(r"^```(?:json)?|```$", "", txt.strip()))

if __name__ == "__main__":
    for f in map(pathlib.Path, sys.argv[1:]):
        segs = transcribe(f)
        f.with_suffix(".transcript.json").write_text(json.dumps(segs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"== {f.name}")
        for s in segs: print(f"  {s['start']:6.1f}–{s['end']:6.1f}  [{s.get('kind', '')}] {s.get('speaker', '')}: {s['text']}")
