"""Cắt mỗi câu đọc thành các CỤM theo dấu câu, mốc cắt bám vào khoảng lặng thật (speech_segments).
Dùng để đặt từng cụm lời đúng lúc màn hình tới mốc (khoanh số, mở tab…) và hiện phụ đề đúng cụm đang nói.
Xem nhanh cụm của dự án:  python KIT/screendemo/chunks.py <thư mục clip>"""
import json, pathlib, re, subprocess, sys
KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "tools"))
from speech_segments import segments

TAG = re.compile(r"\[[^\]]*\]")
SPLIT = re.compile(r"(?<=[,.:?!…])\s+")


def chunks_of(s):
    s = TAG.sub(" ", s).replace("...", "…")
    return [c.strip() for c in SPLIT.split(re.sub(r"\s+", " ", s).strip()) if c.strip()]


def fdur(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                capture_output=True, text=True).stdout)


def line_chunks(proj, line):
    """→ list dict(text, cap, s, e, a, b): s/e = lúc bắt đầu/kết thúc nói trong file; a/b = mốc cắt an toàn (giữa khoảng lặng)."""
    f = pathlib.Path(proj) / "audio" / line["file"]; D = fdur(f)
    seg = [tuple(x) for x in segments(str(f))]
    spoken = chunks_of(line["text"]); cap = chunks_of(line.get("caption") or line["text"])
    if len(cap) != len(spoken): cap = None
    w = [len(c.split()) for c in spoken]; tot = sum(w)
    act = sum(b - a for a, b in seg)
    def at(frac):                       # thời điểm trong file ứng với tỉ lệ lời đã nói
        need = frac * act
        for a, b in seg:
            if need <= b - a: return a + need
            need -= b - a
        return seg[-1][1]
    gaps = [((seg[i][1] + seg[i + 1][0]) / 2, i) for i in range(len(seg) - 1)]
    bounds, used = [], set()
    cum = 0
    for k in range(len(spoken) - 1):
        cum += w[k]; t = at(cum / tot)
        cand = [(abs(g - t), g, i) for g, i in gaps if i not in used and (not bounds or g > bounds[-1][0])]
        best = min(cand) if cand else None
        if best and best[0] < 0.9: bounds.append((best[1], best[2])); used.add(best[2])
        else: bounds.append((t, None))
    B = [0.0] + [b for b, _ in bounds] + [D]
    out = []
    for k, txt in enumerate(spoken):
        a, b = B[k], B[k + 1]
        inside = [(x, y) for x, y in seg if y > a + 0.02 and x < b - 0.02]
        s = max(a, inside[0][0]) if inside else a; e = min(b, inside[-1][1]) if inside else b
        out.append(dict(text=txt, cap=(cap[k] if cap else txt), s=round(s, 3), e=round(e, 3), a=round(a, 3), b=round(b, 3)))
    return out


def all_chunks(proj):
    proj = pathlib.Path(proj)
    T = json.load(open(proj / "audio/timing.json", encoding="utf-8"))
    V = {l["id"]: l for l in json.load(open(proj / "voice.json", encoding="utf-8"))["lines"]}
    res = {}
    for l in T["lines"]:
        l = {**l, "caption": V[l["id"]].get("caption")}
        res[l["id"]] = line_chunks(proj, l)
    return res


if __name__ == "__main__":
    for k, cs in all_chunks(sys.argv[1] if len(sys.argv) > 1 else ".").items():
        print(k)
        for i, c in enumerate(cs):
            print(f"  {i}  {c['s']:5.2f}-{c['e']:5.2f}  [{c['a']:5.2f}|{c['b']:5.2f}]  {c['text']}")
