"""Build video v2: đọc audio/timing.json → tính mốc cảnh / hoạt ảnh / hiệu ứng âm thanh → sinh index.html + cues.json.

Chạy (ở thư mục ad-v2):
  python build.py                      # sinh index.html + cues.json
  python <kit>/tools/mix_audio.py cues.json assets/final_audio.mp3
  python <kit>/tools/render.py . --fps 30 --audio assets/final_audio.mp3 --out stradevn-ad-v2-9x16.mp4
(<kit> = thư mục kit; build.py tự tìm tools, 2 lệnh sau cần đường dẫn đúng tới kit/tools.)
Mọi mốc đều suy ra từ giọng đọc thật → đổi giọng / sửa lời chỉ cần chạy lại 3 lệnh trên.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import json, pathlib, sys
def _find_tools():
    """Tìm thư mục tools của kit: đi ngược lên tới khi gặp kit/tools/captions.py hoặc tools/captions.py."""
    for up in pathlib.Path(__file__).resolve().parents:
        for cand in (up / "kit" / "tools", up / "tools"):
            if (cand / "captions.py").exists(): return cand
    raise SystemExit("Không tìm thấy kit/tools — đặt dự án bên trong thư mục kit hoặc cạnh nó.")
TOOLS = _find_tools()
sys.path.insert(0, str(TOOLS))
from captions import build as build_captions
from speech_segments import segments

HERE = pathlib.Path(__file__).resolve().parent
tm = json.load(open(HERE / "audio/timing.json", encoding="utf-8"))
L = {l["id"]: l for l in tm["lines"]}
s = lambda i: L[i]["start"]; e = lambda i: round(L[i]["start"] + L[i]["dur"], 2)
cut = lambda a, b: round((e(a) + s(b)) / 2, 2)

def at(line_id, word):
    """Ước lượng lúc giọng đọc tới 'word' trong câu (theo vị trí ký tự)."""
    ln = L[line_id]; txt = ln["text"]; i = txt.find(word)
    return round(ln["start"] + ln["dur"] * (i / max(1, len(txt))), 2) if i >= 0 else ln["start"]

D = round(tm["total"], 2)
T = {"D": D, "c2": cut("V1", "V2"), "c3": cut("V2", "V3"), "c4": cut("V3", "V4"), "c5": cut("V4", "V5"),
     "c6": cut("V5", "V6"), "c7": cut("V6", "V7"), "c8": cut("V7", "V8"), "c9": cut("V8", "V9")}
T["tear"] = round(2.4 / 1.1, 2)                                  # clip P-C1 xé giấy ở ~2,4s nguồn, phát 1.1x
# Thẻ nỗi đau bám CỤM NÓI THẬT của câu V2 (đo khoảng lặng — speech_segments.py), không ước lượng theo ký tự.
# Cụm của V2 (đo 01/10): 3 = "lật tờ khai" · 4 = "copy từng cái tên" · 5 = "rồi…" · 6 = "đoán mò".
# Đọc lại V2 thì chạy: python ../../../kit/tools/speech_segments.py audio/V2.mp3  rồi sửa 3 chỉ số dưới nếu lệch.
_s2 = segments(HERE / "audio/V2.mp3"); v2 = s("V2")
_pick = [_s2[3], _s2[4], _s2[6]] if len(_s2) >= 7 else [(at("V2", w) - v2, at("V2", w) - v2 + 0.8) for w in ("lật tờ khai", "copy", "đoán mò")]
T["chip"] = [round(v2 + a - 0.1, 2) for a, _ in _pick]          # thẻ bật lên ngay khi giọng bắt đầu nói cụm đó
T["strike"] = [round(v2 + b + 0.05, 2) for _, b in _pick]        # gạch ngay khi nói xong cụm đó
T["logo"] = at("V3", "StradeVn")
T["typeStep"] = 0.1
T["typeHs"] = round(T["c4"] + 0.7, 2); T["typeKw"] = round(T["typeHs"] + 6 * 0.1 + 0.35, 2)
T["click"] = round(T["typeKw"] + 9 * 0.1 + 0.25, 2)
T["mapIn"] = round(T["c5"] + 0.6, 2)
T["reason"] = at("V6", "lý do")
T["cardIn"] = round(T["c7"] + 0.4, 2); T["ticks"] = [round(T["cardIn"] + 0.9 + i * 0.5, 2) for i in range(4)]
T["noMore"] = at("V8", "không cần"); T["close"] = at("V8", "chỉ việc")
T["cta"] = at("V9", "Nhắn Zalo")

# ---- hiệu ứng âm thanh (đường dẫn trong kit/audio-library) ----
sfx = [
    {"t": 0.0, "file": "sfx/pixabay/whoosh-short.mp3", "volume": 0.5},
    {"t": T["tear"], "file": "sfx/mixkit/paper/paper-slice-quick.mp3", "volume": 1.0},
    {"t": T["tear"] + 0.1, "file": "sfx/mixkit/paper/paper-crumple-quick.mp3", "volume": 0.7},
]
sfx += [{"t": round(T["c2"] + 0.5 + i * 1.0, 2), "file": "sfx/mixkit/counter/clock-tick-single.mp3", "volume": 0.25} for i in range(4)]
sfx += [{"t": t, "file": "sfx/pixabay/pop.mp3", "volume": 0.55} for t in T["chip"]]
sfx += [{"t": t, "file": "sfx/mixkit/text/marker-pen-line.mp3", "volume": 0.6} for t in T["strike"]]
sfx += [
    {"t": round(T["c3"] - 1.3, 2), "file": "sfx/pixabay/riser.mp3", "volume": 0.5},
    {"t": T["logo"] + 0.3, "file": "sfx/pixabay/impact-bass-1.mp3", "volume": 0.85},
    {"t": T["logo"] + 0.4, "file": "sfx/mixkit/light/shimmer-sparkle-sweep.mp3", "volume": 0.4},
]
sfx += [{"t": round(T["typeHs"] + i * T["typeStep"], 2), "file": "sfx/uisfx/mechanical/typing.mp3", "volume": 0.7} for i in range(6)]
sfx += [{"t": round(T["typeKw"] + i * T["typeStep"], 2), "file": "sfx/uisfx/mechanical/typing.mp3", "volume": 0.7} for i in range(9)]
sfx += [
    {"t": T["click"], "file": "sfx/mixkit/ui/ui-select-click.mp3", "volume": 0.8},
    {"t": T["mapIn"], "file": "sfx/mixkit/transition/swoosh-quick.mp3", "volume": 0.7},
    {"t": T["mapIn"] + 1.0, "file": "sfx/mixkit/data/data-scan.mp3", "volume": 0.25},
    {"t": T["c6"] + 0.4, "file": "sfx/mixkit/camera/zoom-swipe-fast.mp3", "volume": 0.6},
    {"t": T["reason"], "file": "sfx/mixkit/text/marker-pen-line.mp3", "volume": 0.6},
    {"t": T["cardIn"], "file": "sfx/pixabay/whoosh-short.mp3", "volume": 0.6},
]
TICK_SFX = "sfx/pixabay/click-soft.mp3"   # tạm — chờ người phụ trách chọn từ nghe-thu-tich-xanh.mp3
sfx += [{"t": t, "file": TICK_SFX, "volume": 0.4} for t in T["ticks"]]
sfx += [
    {"t": T["c8"] + 0.3, "file": "sfx/pixabay/notification.mp3", "volume": 0.35},
    {"t": T["close"], "file": "sfx/pixabay/pop.mp3", "volume": 0.6},
    {"t": T["cta"], "file": "sfx/mixkit/ui/ui-confirm-tone.mp3", "volume": 0.35},
]
for f in [T["c3"], T["c5"], T["c8"], T["c9"]]:
    sfx.append({"t": f, "file": "sfx/mixkit/transition/whoosh-fast.mp3", "volume": 0.45})

cues = {"duration": D,
        "voice": {"file": "audio/narration.mp3", "volume": 1.0},
        "bgm": {"file": "bgm/lyria-110.wav", "volume": 0.2, "start": T["c2"], "fade_in": 1.5, "fade_out": 2.5, "duck": True},
        "sfx": sorted(sfx, key=lambda x: x["t"])}
json.dump(cues, open(HERE / "cues.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- index.html ----
caps = build_captions(HERE / "audio/timing.json", 46)
cap_html = "\n  ".join(
    f'<div class="cap clip" id="cap{i}" data-start="{c["start"]}" data-duration="{round(c["end"] - c["start"], 2)}" data-track-index="5"><span>{c["text"]}</span></div>'
    for i, c in enumerate(caps))
src = (HERE / "index.src.html").read_text(encoding="utf-8")
starts = [0, T["c2"], T["c3"], T["c4"], T["c5"], T["c6"], T["c7"], T["c8"], T["c9"], D]
for k in range(1, 10):
    src = src.replace(f"__C{k}S__", str(starts[k - 1])).replace(f"__C{k}D__", str(round(starts[k] - starts[k - 1], 2)))
c9a = round(4.2 / 0.8, 2)                                        # clip v1 0–4,2s phát 0.8x
src = (src.replace("__C9AD__", str(c9a)).replace("__C9BS__", str(round(T["c9"] + c9a, 2)))
          .replace("__C9BD__", str(round(D - T["c9"] - c9a, 2))))
src = (src.replace("__D__", str(D)).replace("__TIMES__", json.dumps(T)).replace("__CAPTIONS__", cap_html)
          .replace("/*FONTS*/", (HERE / "fonts.css.part").read_text(encoding="utf-8")))
(HERE / "index.html").write_text(src, encoding="utf-8")
print("cảnh:", {k: v for k, v in T.items() if k.startswith("c")}, "| tổng", D, "s |", len(sfx), "hiệu ứng |", len(caps), "phụ đề")
