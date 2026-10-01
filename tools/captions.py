"""Sinh phụ đề theo cụm từ timing.json (đầu ra của tts_script.py).

Cắt mỗi câu tại thẻ ngắt nghỉ ([short pause]...), cụm dài thì cắt ở dấu phẩy / khoảng trắng gần giữa;
nếu dòng kịch bản có "caption" thì phụ đề dùng chữ đó (vd hiện số "988" trong khi giọng đọc bằng chữ); thời gian mỗi cụm chia theo số
ký tự trong khoảng thời lượng thật của câu. Đây là ƯỚC LƯỢNG (lệch ~0,2–0,5s); muốn khớp từng chữ thì dùng
faster-whisper (xem docs/06-am-thanh-va-phu-de.md).

Dùng trong Python:  from captions import build; caps = build("audio/timing.json", max_chars=46)
→ [{"start": 0.3, "end": 2.1, "text": "..."}]
Dòng lệnh:          python captions.py audio/timing.json [max_chars]
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import json, re, sys

TAG = re.compile(r"\[(short|medium|long) pause\]|\[[a-z ]+\]")

def split_line(text, max_chars):
    parts = [p.strip() for p in re.split(r"\[(?:short|medium|long) pause\]", text)]
    out = []
    for p in parts:
        p = TAG.sub("", p).replace("...", "…").strip()
        if not p: continue
        # chữ VIẾT HOA dùng để nhấn giọng TTS → về chữ thường trên phụ đề (giữ từ viết tắt ≤ 3 ký tự như HS, AI)
        p = " ".join(w.lower() if len(w) >= 4 and w.isupper() else w for w in p.split(" "))
        while len(p) > max_chars:
            mid = len(p) // 2
            commas = [i for i, ch in enumerate(p) if ch == "," and 8 <= i <= len(p) - 8]
            if commas: cut = min(commas, key=lambda i: abs(i - mid))
            else:
                spaces = [i for i, ch in enumerate(p) if ch == " " and 6 <= i <= len(p) - 6]
                if not spaces: break
                cut = min(spaces, key=lambda i: abs(i - mid))
            out.append(p[:cut + 1].strip()); p = p[cut + 1:].strip()
        if p: out.append(p)
    return out

def build(timing_path, max_chars=46):
    t = json.load(open(timing_path, encoding="utf-8"))
    caps = []
    for ln in t["lines"]:
        chunks = split_line(ln.get("caption") or ln["text"], max_chars)
        total = sum(len(c) for c in chunks) or 1
        s = ln["start"]
        for c in chunks:
            d = ln["dur"] * len(c) / total
            caps.append({"start": round(s, 2), "end": round(s + d, 2), "text": c}); s += d
    return caps

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for c in build(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 46):
        print(f'{c["start"]:6.2f} → {c["end"]:6.2f}  {c["text"]}')
