"""Nghe lại giọng đọc AI: transcribe từng câu (clip_transcribe, Gemini) rồi so với lời kịch bản → bắt lỗi trước khi dựng.

  python <kit>/tools/tts_qa.py <voice.json> <thư mục audio> [--only V3,V5]

Bắt 3 loại lỗi (đã gặp 20/10/2026):
  - thẻ bị ĐỌC THÀNH LỜI: thẻ mô tả tiếng Việt "[ấm, thấu hiểu]" → model đọc to "ấm thấu hiểu" (dùng thẻ tiếng Anh ngắn)
  - đọc LỐ / thiếu: âm tiết/giây ngoài ~2,4–3,9, hoặc nghe được nhiều chữ hơn kịch bản
  - sai chữ: tên riêng ("Lãm Làng" → "lãng làng") — máy nghe cũng có thể nghe nhầm → câu bị cờ thì người nghe lại
Số trong kịch bản viết bằng chữ, máy nghe hay ghi số → bỏ qua khác biệt số↔chữ. Ra: <audio>/tts_qa.json.
Câu lỗi → sửa lời/thẻ rồi: python tts_script.py voice.json audio --only <id>
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import argparse, difflib, json, pathlib, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from clip_transcribe import transcribe

DIGITS = re.compile(r"\d")
NUMWORDS = set("không một mốt hai ba bốn tư năm lăm sáu bảy tám chín mười mươi trăm nghìn ngàn triệu tỷ linh lẻ".split())

def words(s): return re.sub(r"[^\wÀ-ỹ ]", " ", s.lower()).split()

def check(ln, audio):
    f = audio / f"{ln['id']}.mp3"
    spoken_tags = [t for t in re.findall(r"\[([^\]]+)\]", ln["text"])]
    plain = re.sub(r"\[[^\]]*\]", " ", ln["text"])
    d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]))
    heard = " ".join(s["text"] for s in transcribe(str(f)) if s.get("kind", "nói") in ("nói", "speech", "") or True)
    a, b = words(plain), words(heard)
    diffs = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal": continue
        x, y = a[i1:i2], b[j1:j2]
        if all(w in NUMWORDS for w in x) and all(DIGITS.search(w) or w in NUMWORDS for w in y): continue   # số đọc bằng chữ ↔ máy ghi số
        diffs.append(f"{' '.join(x) or '∅'} → {' '.join(y) or '∅'}")
    hw = " ".join(b)
    tag_read = [t for t in spoken_tags if len(words(t)) >= 1 and " ".join(words(t)) in hw and " ".join(words(t)) not in " ".join(a)]
    rate = len(a) / d
    flags = (["thẻ bị đọc: " + ", ".join(tag_read)] if tag_read else []) + \
            ([f"nhịp {rate:.2f} âm tiết/giây"] if not 2.4 <= rate <= 3.9 else []) + \
            ([f"nghe thừa {len(b) - len(a)} chữ"] if len(b) > len(a) * 1.15 + 2 else [])
    return {"id": ln["id"], "dur": round(d, 2), "rate": round(rate, 2), "diffs": diffs, "flags": flags, "heard": heard}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("audio"); ap.add_argument("--only")
    a = ap.parse_args(); sc = json.load(open(a.script, encoding="utf-8")); audio = pathlib.Path(a.audio)
    only = set(a.only.split(",")) if a.only else None
    lines = [ln for ln in sc["lines"] if ln.get("text") and (only is None or ln["id"] in only)]
    with ThreadPoolExecutor(6) as ex: res = list(ex.map(lambda ln: check(ln, audio), lines))
    bad = 0
    for r in res:
        mark = "⚠" if r["flags"] else ("?" if r["diffs"] else "✓")
        bad += mark == "⚠"
        print(f"{mark} {r['id']:<4} {r['dur']:5.1f}s {r['rate']:.2f}/s  {'; '.join(r['flags'])}")
        for d in r["diffs"]: print(f"      {d}")
    json.dump(res, open(audio / "tts_qa.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(res)} câu · {bad} câu cần đọc lại (⚠) · '?' = khác chữ, nghe lại (máy nghe cũng có thể nhầm)")
