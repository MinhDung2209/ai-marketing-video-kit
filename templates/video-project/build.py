"""Khung dự án video — DỰNG TỰ ĐỘNG từ scenes.json + giọng đọc (không cần viết HTML).

Quy trình (chạy ở thư mục dự án):
  1. python <kit>/tools/tts_script.py voice.json audio              # đọc lời → audio/*.mp3 + timing.json
  2. python build.py                                                # sinh index.html + cues.json
  3. python <kit>/tools/mix_audio.py cues.json assets/final_audio.mp3
  4. python <kit>/tools/render.py . --snap 1,5,10                   # xem thử vài khung (_snap_*.png)
  5. python <kit>/tools/render.py . --fps 30 --audio assets/final_audio.mp3 --out video.mp4

scenes.json: mỗi phần tử = 1 cảnh, gắn với 1 câu trong voice.json (theo "line"). Kiểu cảnh:
  - "media":      nền ảnh/clip (+ Ken Burns), tiêu đề 2 dòng, tuỳ chọn "chips" (thẻ bật lên rồi gạch chéo)
  - "screenshot": nền mờ + ảnh chụp sản phẩm bay lên (nghiêng 3D → phẳng), tiêu đề
  - "logo":       nền tối, logo + tên thương hiệu bùng lên, dòng phụ
  - "cta":        ảnh/clip nửa trên, logo, dòng phụ, nút kêu gọi đập nhịp, dòng liên hệ
Muốn cảnh đặc biệt hơn (vd tờ giấy xé đôi, gõ phím từng ký tự): xem ví dụ đầy đủ ở kit/examples/stradevn-ad-v2.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import json, pathlib, sys, html

def _find_tools():
    # 1) biến VIDEOKIT_TOOLS (make_video.py tự đặt)  2) file .videokit do new_project.py ghi  3) dò thư mục cha
    import os
    env = os.environ.get("VIDEOKIT_TOOLS")
    if env and (pathlib.Path(env) / "captions.py").exists(): return pathlib.Path(env)
    mark = pathlib.Path(__file__).resolve().parent / ".videokit"
    if mark.exists():
        cand = pathlib.Path(mark.read_text(encoding="utf-8").strip())
        if (cand / "captions.py").exists(): return cand
    for up in pathlib.Path(__file__).resolve().parents:
        for cand in (up / "kit" / "tools", up / "tools"):
            if (cand / "captions.py").exists(): return cand
    raise SystemExit("Không tìm thấy kit/tools — chạy bằng make_video.py, hoặc ghi đường dẫn <kit>/tools vào file .videokit cạnh build.py.")
sys.path.insert(0, str(_find_tools()))
from captions import build as build_captions

HERE = pathlib.Path(__file__).resolve().parent
cfg = json.load(open(HERE / "scenes.json", encoding="utf-8"))
tm = json.load(open(HERE / "audio/timing.json", encoding="utf-8"))
L = {l["id"]: l for l in tm["lines"]}
D = round(tm["total"], 2)
B = cfg["brand"]; W, H = cfg.get("width", 1080), cfg.get("height", 1920)
# vùng an toàn theo nền tảng (TikTok/Reels che trên ~240px, dưới ~660px, cột nút bên phải) — mặc định = bố cục cũ
S = {"title_top": 200, "chips_top": 520, "shot_top": 700, "shot_left": 40, "shot_right": 40, "tag_top": 1260,
     "cta_shift": 0, "cap_top": 1480, "cap_chars": 46, **cfg.get("safe", {})}
esc = lambda s: html.escape(str(s))

# ---- mốc cảnh: cắt giữa 2 câu liên tiếp ----
sc = cfg["scenes"]
ends = [round(L[x["line"]]["start"] + L[x["line"]]["dur"], 2) for x in sc]
starts = [0.0] + [round((ends[i] + L[sc[i + 1]["line"]]["start"]) / 2, 2) for i in range(len(sc) - 1)]
bounds = list(zip(starts, starts[1:] + [D]))

def media_tag(src, extra=""):
    if not src: return ""
    if src.endswith((".mp4", ".webm", ".mov")):
        return f'<video class="full" src="{esc(src)}" muted playsinline preload="auto" {extra}></video>'
    return f'<img class="full" src="{esc(src)}" alt="" />'

def headline(x, top=None, size=96):
    top = S["title_top"] if top is None else top
    l1, l2 = esc(x.get("title", "")), esc(x.get("title2", ""))
    return (f'<h1 class="h headline" style="top:{top}px;font-size:{x.get("title_size", size)}px"><span style="display:block">{l1}</span>'
            f'<span class="hl" style="display:block">{l2}</span></h1>') if (l1 or l2) else ""

sections, js, sfx = [], [], []
for i, (x, (s0, s1)) in enumerate(zip(sc, bounds)):
    sid, d = f"s{i}", round(s1 - s0, 2); ln = L[x["line"]]; typ = x["type"]
    vid = f'data-rate="{x.get("rate", 1)}" data-offset="{x.get("offset", 0)}" data-end="{x.get("end", 1e9)}"'
    if typ == "media":
        chips = "".join(f'<div class="chip" id="{sid}k{j}">{esc(c)}<div class="strike" id="{sid}x{j}"></div></div>' for j, c in enumerate(x.get("chips", [])))
        body = (f'<div id="{sid}bg" class="full">{media_tag(x.get("media"), vid)}</div><div class="shade-top"></div>'
                f'{headline(x)}<div class="chips" style="top:{S["chips_top"]}px">{chips}</div>')
        js.append(f'tl.fromTo("#{sid}bg",{{scale:1.02}},{{scale:1.14,duration:{d},ease:"none"}},{s0});')
        n = len(x.get("chips", []))
        for j in range(n):   # thẻ rải đều trong 70% câu, gạch ngay sau
            t = round(ln["start"] + ln["dur"] * (0.15 + 0.7 * j / max(1, n)), 2)
            js.append(f'tl.fromTo("#{sid}k{j}",{{x:-120,opacity:0}},{{x:0,opacity:1,duration:0.4,ease:"back.out(2)"}},{t});')
            if x.get("strike_chips", True):
                js.append(f'tl.fromTo("#{sid}x{j}",{{scaleX:0}},{{scaleX:1,duration:0.3}},{t + 0.6});')
                sfx.append({"t": t + 0.6, "file": "sfx/mixkit/text/marker-pen-line.mp3", "volume": 0.5})
            sfx.append({"t": t, "file": "sfx/pixabay/pop.mp3", "volume": 0.5})
    elif typ == "screenshot":
        body = (f'<div id="{sid}bg" class="full" style="filter:blur(12px) brightness(.45)">{media_tag(x.get("background"), vid)}</div>'
                f'{headline(x)}<div id="{sid}shot" class="shot" style="left:{S["shot_left"]}px;right:{S["shot_right"]}px;top:{S["shot_top"]}px"><img src="{esc(x["screenshot"])}" alt="" /></div>'
                + (f'<div class="tag" style="left:{S["shot_left"] + 20}px;top:{S["tag_top"]}px">{esc(x["tag"])}</div>' if x.get("tag") else ""))
        js.append(f'tl.fromTo("#{sid}shot",{{y:500,opacity:0,rotationX:35,transformPerspective:1400}},{{y:0,opacity:1,rotationX:0,duration:1.0,ease:E}},{s0 + 0.4});')
        sfx += [{"t": s0 + 0.4, "file": "sfx/mixkit/transition/swoosh-quick.mp3", "volume": 0.6},
                {"t": s0 + 1.4, "file": "sfx/mixkit/data/data-scan.mp3", "volume": 0.25}]
    elif typ == "logo":
        body = (f'<div class="full" style="background:radial-gradient(circle at 50% 45%,{B.get("glow", "#1E1B4B")} 0%,#0B1020 70%)"></div>'
                f'<div id="{sid}brand" class="brand" style="position:absolute;left:0;right:0;top:760px"><img src="{esc(B["logo"])}" alt="" /><div class="name">{esc(B["name"])}</div></div>'
                f'<div id="{sid}sub" class="sub" style="top:990px">{esc(x.get("subtitle", B.get("tagline", "")))}</div>')
        t = round(ln["start"] + ln["dur"] * 0.4, 2)
        js.append(f'tl.fromTo("#{sid}brand",{{scale:0.6,opacity:0}},{{scale:1,opacity:1,duration:0.45,ease:"back.out(2.5)"}},{t});')
        js.append(f'tl.fromTo("#{sid}sub",{{opacity:0,y:20}},{{opacity:1,y:0,duration:0.5,ease:E}},{t + 0.5});')
        sfx += [{"t": round(s0 - 1.2, 2), "file": "sfx/pixabay/riser.mp3", "volume": 0.4},
                {"t": t + 0.3, "file": "sfx/pixabay/impact-bass-1.mp3", "volume": 0.8},
                {"t": t + 0.4, "file": "sfx/mixkit/light/shimmer-sparkle-sweep.mp3", "volume": 0.35}]
    elif typ == "cta":
        body = (f'<div class="full" style="background:#F7F8FB"></div>'
                f'<div id="{sid}bg" style="position:absolute;left:0;top:0;width:100%;height:{1000 - S["cta_shift"]}px;overflow:hidden">{media_tag(x.get("media"), vid)}</div>'
                f'<div style="position:absolute;left:0;right:0;top:{640 - S["cta_shift"]}px;height:360px;background:linear-gradient(180deg,rgba(247,248,251,0),#F7F8FB)"></div>'
                f'<div class="brand" style="position:absolute;left:0;right:0;top:{950 - S["cta_shift"]}px"><img src="{esc(B["logo"])}" alt="" style="width:130px;height:130px" /><div class="name" style="font-size:104px;color:#101828">{esc(B["name"])}</div></div>'
                f'<div class="sub" style="top:{1110 - S["cta_shift"]}px;color:#344054">{esc(x.get("subtitle", B.get("tagline", "")))}</div>'
                f'<div id="{sid}cta" class="cta" style="top:{1210 - S["cta_shift"]}px">{esc(x["button"])}</div>'
                f'<div class="sub" style="top:{1380 - S["cta_shift"]}px;font-size:42px;color:{B.get("accent", "#4F46E5")}">{esc(x.get("contact", ""))}</div>')
        t = round(ln["start"] + ln["dur"] * 0.55, 2)
        js.append(f'tl.fromTo("#{sid}cta",{{y:40,opacity:0,scale:0.9}},{{y:0,opacity:1,scale:1,duration:0.6,ease:"back.out(2)"}},{t});')
        js.append(f'tl.to("#{sid}cta",{{scale:1.05,duration:0.5,yoyo:true,repeat:5,ease:"sine.inOut"}},{t + 0.8});')
        sfx.append({"t": t, "file": "sfx/uisfx/soft/success.mp3", "volume": 0.4})
    else:
        raise SystemExit(f"Kiểu cảnh không hỗ trợ: {typ}")
    sections.append(f'<section id="{sid}" class="clip" data-start="{s0}" data-duration="{d}"><div id="{sid}w" class="full">{body}</div></section>')
    if i > 0:
        js.append(f'tl.fromTo("#{sid}w",{{opacity:0,scale:1.06}},{{opacity:1,scale:1,duration:0.45,ease:E}},{s0});')
        sfx.append({"t": s0, "file": "sfx/mixkit/transition/whoosh-fast.mp3", "volume": 0.4})

caps = build_captions(HERE / "audio/timing.json", S["cap_chars"])
cap_html = "".join(f'<div class="cap clip" data-start="{c["start"]}" data-duration="{round(c["end"] - c["start"], 2)}"><span>{esc(c["text"])}</span></div>' for c in caps)
fonts_css = (HERE / "fonts.css.part").read_text(encoding="utf-8") if (HERE / "fonts.css.part").exists() else ""
tpl = (HERE / "template.html").read_text(encoding="utf-8")
page = (tpl.replace("__W__", str(W)).replace("__H__", str(H)).replace("__D__", str(D)).replace("/*FONTS*/", fonts_css)
           .replace("__CAPTOP__", str(S["cap_top"])).replace("__ACCENT__", B.get("accent", "#4F46E5")).replace("__HL__", B.get("highlight", "#FBBF24"))
           .replace("__SECTIONS__", "\n".join(sections)).replace("__CAPTIONS__", cap_html).replace("__JS__", "\n".join(js)))
(HERE / "index.html").write_text(page, encoding="utf-8")

bgm = cfg.get("bgm")
cues = {"duration": D, "voice": {"file": "audio/narration.mp3", "volume": 1.0}, "sfx": sorted(sfx, key=lambda z: z["t"])}
if bgm: cues["bgm"] = {"volume": 0.2, "fade_in": 1.0, "fade_out": 2.5, "duck": True, **bgm}
json.dump(cues, open(HERE / "cues.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"xong: index.html + cues.json — {len(sc)} cảnh, {len(caps)} phụ đề, {len(sfx)} hiệu ứng, {D}s")
