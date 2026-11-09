"""Thể loại chung "Demo tính năng" — kịch bản dựng ĐỌC TỪ clip.json (không cần sửa code):
hook con số → câu hỏi → (bối cảnh) → các cảnh quay màn hình theo "scenes" → tổng kết → logo.

clip.json → "story": {
  "hook": {"line": "V1", "value": 3.45, "kicker": "…", "unit": "…", "chip": "…", "source": "Nguồn: …"},   ← 3 cụm lời
  "question": {"line": "V2", "q1": "…", "q2": "…"},                                                      ← 3 cụm
  "clock": {"line": "V3", "text": "8:00 SÁNG", "title": "…", "sub": "…"},                                 ← 2 cụm (bỏ được)
  "scenes": [ {"rec": "h2", "from": ["start", 0.4], "to": "end", "badge": "BƯỚC 1 · …",
               "lines": [ {"line": "V4", "i": 0, "j": 2, "at": ["start", 0.8]},
                          {"line": "V4", "i": 2, "j": 3, "at": ["ten-moc", 0], "hint": 2.0, "meme": "check"} ],
               "only": ["full"] } , … ],                                  ← "only": bản nào mới có cảnh này
  "recap": {"lines": [{"line": "V9", "i": 0, "j": 3}, {"line": "V9", "i": 3, "j": 5}], "rows": ["…", "…", "…"], "ask": "…"},
  "logo": {"line": "V10"} }
Mỗi "at" là tên mốc trong assets/screen/<rec>/marks.json (đặt lúc quay bằng mark/focus/ink trong shots.json)."""
import json, os, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
KIT = pathlib.Path((HERE / ".videokit").read_text(encoding="utf-8").strip()).parent
sys.path.insert(0, str(KIT / "screendemo"))
from engine import Story
import blocks as B

C = json.loads((HERE / "clip.json").read_text(encoding="utf-8")); S = C["story"]; BR = C.get("brand", {})
V = os.environ.get("VARIANT", "full")
st = Story(HERE, variant=V, brand=BR)
P = st.P
at = lambda x: tuple(x) if isinstance(x, list) else x

print("dựng:")
h = S["hook"]
B.hook_number(st, P(h["line"], 0, 3), h["value"], h["kicker"], h["unit"], h["chip"], h["source"],
              bg=h.get("bg") if h.get("bg") and (HERE / h["bg"]).exists() else None, decimals=h.get("decimals", 2))
if S.get("question"): q = S["question"]; B.question(st, P(q["line"], 0, 3), q["q1"], q["q2"], sticker=q.get("sticker", "thinking"))
if S.get("clock"): c = S["clock"]; B.clock(st, P(c["line"], 0, 2), c["text"], c["title"], c["sub"])
for sc in S["scenes"]:
    if sc.get("only") and V not in sc["only"]: continue
    items = []
    for l in sc["lines"]:
        if l.get("only") and V not in l["only"]: continue
        items.append(P(l["line"], l["i"], l["j"], at=at(l["at"]), lead=l.get("lead", 0.0), hint=l.get("hint", 1.0), meme=l.get("meme")))
        for k in l.get("sub", []): items.append(st.Kf(k["chunk"], at(k["at"])))       # mốc phụ trong cùng cụm lời
    st.screen(sc["rec"], at(sc["from"]), at(sc["to"]), items, sc["badge"], tail=sc.get("tail", 0.6),
              tail_hint=sc.get("tail_hint", 1.0), pre=sc.get("pre", 0.35))
r = S["recap"]
B.recap(st, [P(x["line"], x["i"], x["j"]) for x in r["lines"]], r["rows"], r["ask"], cta=r.get("cta", "Bình luận nhé"))
B.logo_end(st, P(S["logo"]["line"], 0, 2), BR.get("name", ""), BR.get("tagline", ""), BR.get("url", ""))
st.finish(title=C.get("title", C["slug"]))
