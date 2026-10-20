"""Dựng video tin tức / WHY từ giọng đọc + kế hoạch cảnh (skill news-explainer) — agent chỉ cần viết voice.json + plan.json.

  python <kit>/tools/news_video.py subs   <dự án>   → subs.json + video.srt: phụ đề KHỚP GIỌNG (cụm nói thật, speech_segments)
  python <kit>/tools/news_video.py build  <dự án>   → index.html (motion HTML: templates/news-motion) + audio/sfx.json
  python <kit>/tools/news_video.py snap   <dự án>   → review/scenes.jpg: 1 khung giữa mỗi cảnh để duyệt
  python <kit>/tools/news_video.py render <dự án>   → video.mp4: hình (tools/render.py) + giọng + nhạc nền (duck) + SFX
  python <kit>/tools/news_video.py qa     <dự án>   → QA.json: độ dài, khung đen, âm lượng, khung kiểm tra
  python <kit>/tools/news_video.py publish <dự án>  → YouTube (private do API Testing) + thumbnail + mô tả có chương & nguồn
  python <kit>/tools/news_video.py all    <dự án>   → subs → build → snap → render → qa (không tự đăng)

Đầu vào trong <dự án>:
  audio/timing.json + audio/V*.mp3   ← tools/tts_script.py voice.json audio
  media/...                          ← tools/news_media.py grab (ảnh/video báo) · footage stock
  plan.json:
  {"bug": "WHY · Tin nhanh", "bgm": {"id": "bgm.lyria.news-explainer-100bpm", "volume": 0.08},
   "scenes": [
     {"at": "V01", "fn": "bigtitle", "args": ["15 ngân hàng *giảm lãi*", {"kicker": "19/10"}], "transition": "wipe",
      "over": [{"at": "V01", "phrase": "cùng lúc", "fn": "handwrite", "args": ["cùng lúc!", {"x": 960, "y": 300}]}]},
     {"at": "V02", "phrase": "giảm lãi cho vay", "fn": "photo", "args": ["media/x/img-01.jpg", {"credit": "Ảnh: SBV · Dân trí"}]}]}
  - "at" = id câu thoại; "phrase" = cảnh bắt đầu đúng lúc giọng nói tới cụm chữ này (tìm trong phụ đề của câu đó);
    "shift" = lệch thêm (giây, mặc định -0.15: hình đi trước giọng một chút).
  - Cảnh kéo dài tới cảnh sau; "over" = lớp đè (handwrite, scribble, lowerThird…) — mặc định tới hết cảnh, hoặc "d".
  - "fn"/"args" = hàm Motion (xem templates/news-motion/README.md) bỏ 2 tham số đầu (t, d) — build tự điền.
  - "sfx": [{"at","phrase","shift","name","vol"}] thêm tiếng tuỳ ý; tiếng mặc định theo từng hàm ở AUTO_SFX.
Nguồn: mọi "credit" trên hình + SOURCES.md (từ media/*/media.json) để dán mô tả.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, html, json, math, pathlib, re, shutil, subprocess, sys
KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "tools"))
from speech_segments import segments

LIB = KIT / "audio-library"
SFX = {   # tên ngắn → audio-library (Mixkit/Pixabay: dùng thương mại, không bắt buộc ghi nguồn)
    "whoosh": "sfx/mixkit/transition/whoosh-fast.mp3", "whoosh-short": "sfx/pixabay/whoosh-short.mp3",
    "swoosh": "sfx/mixkit/transition/swoosh-quick.mp3", "pen": "sfx/mixkit/text/pen-write-paper.mp3",
    "pencil": "sfx/mixkit/text/pencil-write-short.mp3", "marker": "sfx/mixkit/text/marker-pen-line.mp3",
    "tick": "sfx/mixkit/counter/clock-tick-single.mp3", "pop": "sfx/pixabay/pop.mp3", "pop-dry": "sfx/mixkit/ui/ui-popup-dry.mp3",
    "hit": "sfx/mixkit/impact/bass-hit-short.mp3", "impact": "sfx/pixabay/impact-bass-1.mp3",
    "shutter": "sfx/mixkit/camera/camera-shutter-hard.mp3", "paper": "sfx/mixkit/paper/paper-slide.mp3",
    "page": "sfx/mixkit/paper/paper-page-turn.mp3"}
VOL = {"whoosh": .3, "whoosh-short": .35, "swoosh": .3, "pen": .4, "pencil": .4, "marker": .4, "tick": .25, "pop": .3, "pop-dry": .3,
       "hit": .4, "impact": .45, "shutter": .3, "paper": .35, "page": .35}
CAP_MAX = 52     # ký tự / dòng phụ đề
FPS = 30

def load(p): return json.load(open(p, encoding="utf-8"))
def save(o, p): json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
def run(cmd, **kw): return subprocess.run([str(c) for c in cmd], check=True, **kw)
def dur(f): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]))

# ------------------------------------------------------------------ phụ đề khớp giọng
def phrases(text):   # cắt sau dấu câu (không cắt "0,5" / "100.000"), giữ dấu
    return [p.strip() for p in re.findall(r"(?:[^,.:;?!]|[,.](?=\d))+[,.:;?!]*", text) if p.strip()]

def assign(ph, segs):
    """Cụm chữ (theo thứ tự) → cụm nói: tâm cụm chữ rơi vào cụm nói chứa cùng tỉ lệ thời gian CÓ tiếng."""
    talk = sum(b - a for a, b in segs); chars = sum(len(p) for p in ph) or 1; out = [[] for _ in segs]; acc = 0
    for p in ph:
        mid = (acc + len(p) / 2) / chars * talk; acc += len(p); t = 0
        for i, (a, b) in enumerate(segs):
            if mid <= t + (b - a) or i == len(segs) - 1: out[i].append(p); break
            t += b - a
    return out

def split_even(text, a, b):   # dòng quá dài → cắt ở khoảng trắng gần giữa, chia thời gian theo ký tự
    if len(text) <= CAP_MAX: return [(a, b, text)]
    sp = [i for i, c in enumerate(text) if c == " "]; cut = min(sp, key=lambda i: abs(i - len(text) / 2))
    m = a + (b - a) * cut / len(text)
    return split_even(text[:cut], a, m) + split_even(text[cut + 1:], m, b)

def cmd_subs(proj):
    tm = load(proj / "audio/timing.json"); subs = []
    for ln in tm["lines"]:
        segs = segments(proj / "audio" / ln["file"]) or [(0, ln["dur"])]
        text = re.sub(r"\[[^\]]*\]", "", ln.get("caption") or ln["text"])
        for (a, b), g in zip(segs, assign(phrases(text), segs)):
            for s, e, t in split_even(" ".join(g), ln["start"] + a, ln["start"] + b) if g else []:
                subs.append({"line": ln["id"], "start": round(s, 2), "end": round(e, 2), "text": t})
    for x, y in zip(subs, subs[1:]):   # giữ chữ tới cụm sau khi nghỉ ngắn (đỡ nháy)
        if y["start"] - x["end"] < 1.2: x["end"] = y["start"]
    save(subs, proj / "subs.json")
    ts = lambda x: f"{int(x // 3600):02}:{int(x // 60 % 60):02}:{int(x % 60):02},{int(round(x % 1 * 1000)) % 1000:03}"
    (proj / "video.srt").write_text("\n".join(f"{i + 1}\n{ts(s['start'])} --> {ts(s['end'])}\n{s['text']}\n" for i, s in enumerate(subs)), encoding="utf-8")
    print(f"phụ đề: {len(subs)} dòng → subs.json, video.srt")

# ------------------------------------------------------------------ dựng
def fold(s): return re.sub(r"\s+", " ", re.sub(r"[^\w\s%]", " ", s.lower())).strip()

def anchor(item, lines, subs):
    """"at" + "phrase" → giây tuyệt đối (lúc giọng nói tới cụm đó) + "shift"."""
    lid = item["at"]
    if lid not in lines: raise SystemExit(f"plan: không có câu {lid}")
    mine = [s for s in subs if s["line"] == lid]
    t = mine[0]["start"] if mine else lines[lid]["start"]
    if item.get("phrase"):
        q = fold(item["phrase"]); hit = None
        for i, s in enumerate(mine):   # cụm có thể vắt qua 2 dòng phụ đề
            if q in fold(s["text"]) or (i + 1 < len(mine) and q in fold(s["text"] + " " + mine[i + 1]["text"]) and q not in fold(mine[i + 1]["text"])):
                hit = s; break
        if hit is None: raise SystemExit(f"plan: không thấy \"{item['phrase']}\" trong phụ đề câu {lid}")
        # vị trí trong dòng: dời theo tỉ lệ ký tự trước cụm
        k = fold(hit["text"]).find(q); full = len(fold(hit["text"])) or 1
        t = hit["start"] + (hit["end"] - hit["start"]) * max(0, k) / full if k > 0 else hit["start"]
    return max(0.0, t + item.get("shift", -0.15))

def glyphs(text): return len(re.sub(r"\s", "", text))

def auto_sfx(fn, t, d, args):
    """Tiếng mặc định khớp thời điểm trong templates/news-motion/motion.js."""
    o = args[-1] if args and isinstance(args[-1], dict) else {}
    if fn == "headline":
        boxes = o.get("boxes") or ([o["box"]] if o.get("box") else [])
        return [("paper", t, None)] + [("marker", t + 1.0 + i * .6, None) for i in range(len(boxes))]
    if fn == "handwrite":
        T = o.get("write") or min(d * .75, .55 + glyphs(args[0]) * .085)
        return [("pen", t, T)]
    if fn == "scribble": return [("pencil", t, None)]
    if fn in ("bigtitle", "chapter"): return [("hit", t + .05, None)]
    if fn == "counter": return [("tick", t + .15, None), ("tick", t + .15 + min(o.get("count", 1.6), d * .6), None)]
    if fn == "compare": return [("pop", t + .4, None), ("swoosh", t + 2.0, None)]
    if fn == "timeline": return [("pop-dry", t + .5 + i * .55, None) for i in range(len(args[0]))]
    if fn == "quote": return [("page", t, None)]
    if fn == "lowerThird": return [("swoosh", t, None)]
    return []

def cap_html(text):   # số/% tô vàng
    return re.sub(r"(\d[\d.,–%/]*(?:\s?(?:tỷ|triệu|nghìn|điểm %|%/năm))?)", r"<b>\1</b>", html.escape(text))

def cmd_build(proj):
    plan = load(proj / "plan.json"); tm = load(proj / "audio/timing.json"); subs = load(proj / "subs.json")
    total = round(tm["total"] + plan.get("tail", 0.6), 2); lines = {l["id"]: l for l in tm["lines"]}
    if not (proj / "motion").exists(): shutil.copytree(KIT / "templates/news-motion", proj / "motion")
    scenes = plan["scenes"]; starts = [0.0 if i == 0 else anchor(s, lines, subs) for i, s in enumerate(scenes)]
    if any(b <= a for a, b in zip(starts, starts[1:])): raise SystemExit(f"plan: cảnh không tăng dần {starts}")
    js, sfx, timeline = [], [], []
    for i, (s, t) in enumerate(zip(scenes, starts)):
        end = starts[i + 1] if i + 1 < len(scenes) else total; d = round(end - t, 3)
        js.append(f"m.{s['fn']}({t:.3f}, {d:.3f}, {', '.join(json.dumps(a, ensure_ascii=False) for a in s.get('args', []))});")
        sfx += auto_sfx(s["fn"], t, d, s.get("args", []))
        timeline.append({"i": i, "fn": s["fn"], "start": round(t, 2), "end": round(end, 2), "at": s["at"], "phrase": s.get("phrase", "")})
        for o in s.get("over", []):
            ot = anchor({"shift": 0, **o}, lines, subs) if o.get("at") else t + o.get("t", .3)
            od = min(o.get("d", end - ot), end - ot)
            if od <= .2: raise SystemExit(f"plan: lớp đè {o['fn']} ở cảnh {i} nằm ngoài cảnh")
            js.append(f"m.{o['fn']}({ot:.3f}, {od:.3f}, {', '.join(json.dumps(a, ensure_ascii=False) for a in o.get('args', []))});")
            sfx += auto_sfx(o["fn"], ot, od, o.get("args", []))
        if s.get("transition") and i + 1 < len(scenes):
            js.append(f"m.transition({end:.3f}, {json.dumps(s['transition'])});")
            sfx.append(("whoosh-short" if s["transition"] != "flash" else "swoosh", end - .25, None))
    for x in plan.get("sfx", []): sfx.append((x["name"], anchor(x, lines, subs), x.get("d")))
    sfx = [{"name": n, "t": round(max(0, t), 3), "d": d and round(d, 3), "vol": VOL.get(n, .3)} for n, t, d in sorted(sfx, key=lambda e: e[1])]
    save({"total": total, "events": sfx}, proj / "audio/sfx.json"); save(timeline, proj / "timeline.json")
    caps = "\n".join(f'<div class="cap" data-start="{c["start"]}" data-duration="{round(c["end"] - c["start"], 3)}"><span>{cap_html(c["text"])}</span></div>'
                     for c in subs)
    page = f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>{html.escape(plan.get('title', proj.name))}</title>
<link rel="stylesheet" href="motion/motion.css">
<script src="motion/gsap.min.js"></script><script src="motion/opentype.min.js"></script>
<script src="motion/fonts/Pangolin.js"></script><script src="motion/fonts/PatrickHand.js"></script><script src="motion/fonts/Itim.js"></script>
<script src="motion/motion.js"></script>
<style>
.cap{{position:absolute;left:0;right:0;bottom:64px;text-align:center;z-index:900;pointer-events:none}}
.cap span{{display:inline-block;max-width:1500px;padding:10px 26px 12px;background:rgba(10,12,16,.82);border-radius:10px;
  font:700 44px/1.3 'Be Vietnam Pro',sans-serif;color:#fff;letter-spacing:-.3px;box-shadow:0 6px 24px rgba(0,0,0,.35)}}
.cap b{{color:#ffc531;font-weight:800}}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{total}">
{caps}
</div>
<script>
Motion.ready(() => {{
  const m = new Motion({{ root: '#root' }});
  {chr(10).join('  ' + x for x in js).strip()}
  {"m.bug(0, %s, %s);" % (total, json.dumps(plan['bug'], ensure_ascii=False)) if plan.get('bug') else ''}
  m.finish({total});
}});
</script>
</body></html>
"""
    (proj / "index.html").write_text(page, encoding="utf-8")
    sources(proj)
    print(f"index.html: {len(scenes)} cảnh · {len(subs)} phụ đề · {len(sfx)} SFX · {total}s")

def sources(proj):
    """SOURCES.md: báo + tác giả ảnh/video thực sự dùng trong plan (để dán mô tả, trả lời khiếu nại)."""
    used = (proj / "index.html").read_text(encoding="utf-8")
    rows = []
    for mj in sorted((proj / "media").rglob("media.json")) if (proj / "media").exists() else []:
        m = load(mj); rel = mj.parent.relative_to(proj).as_posix()
        items = [it for it in m.get("items", []) if f"{rel}/{it['file']}" in used]
        if items: rows.append(f"- {m['outlet']} ({m.get('published', '')[:10]}): [{m['title']}]({m['url']}) — "
                              + "; ".join(f"{it['kind']} {it['file']}" + (f" (Ảnh/Video: {it['credit']})" if it.get("credit") else "") for it in items))
    # media/inventory.json (clip đã chuyển đổi, b-roll stock): {file, outlet, url, published, title, credit}
    seen, other = {r.split("](")[1].split(")")[0] for r in rows}, []
    for x in load(proj / "media/inventory.json") if (proj / "media/inventory.json").exists() else []:
        if x["file"] in used and x["url"] not in seen:
            seen.add(x["url"]); other.append(f"- {x['outlet']} ({(x.get('published') or '')[:10] or 'stock'}): [{x.get('title') or x['file']}]({x['url']})"
                                             + (f" — {x['credit']}" if x.get("credit") else ""))
    (proj / "SOURCES.md").write_text("# Nguồn hình ảnh / video\n\n" + "\n".join(rows + other) + "\n", encoding="utf-8")

def description(proj):
    """Mô tả YouTube: tóm tắt (plan.summary) + chương (cảnh chapter) + nguồn dữ kiện/hình."""
    plan = load(proj / "plan.json"); tl = load(proj / "timeline.json"); scenes = plan["scenes"]
    mmss = lambda t: f"{int(t) // 60:02}:{int(t) % 60:02}"
    ch = [("Mở đầu", 0)] + [(re.sub(r"[*~]", "", scenes[s["i"]]["args"][1]), s["start"]) for s in tl if s["fn"] == "chapter" and s["start"] > 10]
    out = [plan.get("summary", plan.get("title", "")), "", *[f"{mmss(t)} {name}" for name, t in ch], "",
           "Nguồn hình ảnh / video (bản quyền thuộc các tòa soạn, tác giả):",
           *[l for l in (proj / "SOURCES.md").read_text(encoding="utf-8").splitlines() if l.startswith("- ")],
           "", "Nhạc nền: tự tạo bằng Google Lyria. Giọng đọc: AI (Gemini TTS)."]
    if plan.get("facts"): out[1:1] = ["", "Dữ kiện chính:", *[f"- {f}" for f in plan["facts"]]]
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 \2", "\n".join(out))[:4900]

def cmd_publish(proj):
    """Đăng YouTube (API ở chế độ Testing → khoá private: đổi 'Không công khai' trong Studio) + thumbnail; lưu youtube-upload.json."""
    import types, youtube_upload as yt
    plan = load(proj / "plan.json"); rec = proj / "youtube-upload.json"
    if rec.exists() and load(rec).get("video_id"): print("đã đăng:", load(rec)["url"]); return
    (proj / "youtube-description.txt").write_text(description(proj), encoding="utf-8")
    th = plan.get("thumb", {}); thumb = proj / "thumbnail.jpg"
    yt.thumb(types.SimpleNamespace(video=str(proj / "video.mp4"), out=str(thumb), t=th.get("t", 1.5), text=th.get("text", "")))
    vid = yt.upload(types.SimpleNamespace(video=str(proj / "video.mp4"), title=plan["title"], desc=str(proj / "youtube-description.txt"),
                                          chapters=None, credits=None, thumb=str(thumb), tags=plan.get("tags", ""),
                                          privacy=plan.get("privacy", "private"), category="25"))
    save({"video_id": vid, "url": f"https://youtu.be/{vid}", "studio": f"https://studio.youtube.com/video/{vid}/edit",
          "privacy": plan.get("privacy", "private")}, rec)
    print("đăng xong:", f"https://youtu.be/{vid}")

# ------------------------------------------------------------------ duyệt / render
def render_py(proj, *args):
    run([sys.executable, KIT / "tools/render.py", proj, *args])

def cmd_snap(proj):
    from PIL import Image, ImageDraw, ImageFont
    tl = load(proj / "timeline.json"); ts = [round((s["start"] + s["end"]) / 2 + .6, 1) for s in tl]
    for f in proj.glob("_snap_*.png"): f.unlink()
    render_py(proj, "--snap", ",".join(map(str, ts)))
    (proj / "review").mkdir(exist_ok=True); font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
    W, H, n = 480, 290, len(ts); sheet = Image.new("RGB", (W * 4, math.ceil(n / 4) * H), "#111"); d = ImageDraw.Draw(sheet)
    for i, (s, t) in enumerate(zip(tl, ts)):
        im = Image.open(proj / f"_snap_{t:05.1f}.png"); im.thumbnail((W - 6, H - 30)); x, y = i % 4 * W, i // 4 * H
        sheet.paste(im, (x + 3, y + 3)); d.text((x + 6, y + H - 26), f"{i} {s['fn']} {s['at']} {t}s", font=font, fill="#ffc531")
    sheet.save(proj / "review/scenes.jpg", quality=88)
    for f in proj.glob("_snap_*.png"): f.unlink()
    print(proj / "review/scenes.jpg")

def cmd_render(proj):
    plan = load(proj / "plan.json"); ev = load(proj / "audio/sfx.json"); total = ev["total"]
    pic = proj / "picture.mp4"   # hình mới hơn index.html → chỉ trộn lại tiếng (sửa nhạc/SFX không phải render lại ~10 phút)
    if not (pic.exists() and pic.stat().st_mtime > (proj / "index.html").stat().st_mtime):
        render_py(proj, "--no-audio", "--out", "picture.mp4", "--fps", str(FPS))
    cat = {c["id"]: c for c in load(LIB / "catalog.json")}; b = plan.get("bgm", {})
    bgm = LIB / cat[b.get("id", "bgm.lyria.news-explainer-100bpm")]["path"]
    inp = ["-i", proj / "picture.mp4", "-i", proj / "audio/narration.mp3", "-stream_loop", "-1", "-i", bgm]
    fx, mix = [], []
    for k, e in enumerate(ev["events"]):
        inp += (["-stream_loop", "-1"] if e["d"] else []) + ["-i", LIB / SFX[e["name"]]]
        ms = int(e["t"] * 1000); trim = f"atrim=0:{e['d']},afade=t=out:st={max(0, e['d'] - 0.15):.3f}:d=0.15," if e["d"] else ""   # ffmpeg 8: "d=.15" lỗi
        fx.append(f"[{k + 3}:a]{trim}aformat=sample_rates=44100:channel_layouts=stereo,volume={e['vol']},adelay={ms}|{ms}[s{k}]"); mix.append(f"[s{k}]")
    v = b.get("volume", .08)
    graph = ";".join([f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,apad,asplit=2[v][key]",
        f"[2:a]aformat=sample_rates=44100:channel_layouts=stereo,volume={v},afade=t=in:d=1.5,afade=t=out:st={max(0, total - 4)}:d=4[bed]",
        "[bed][key]sidechaincompress=threshold=0.025:ratio=6:attack=15:release=450[duck]", *fx,
        f"[v][duck]{''.join(mix)}amix=inputs={2 + len(mix)}:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100,alimiter=limit=0.89:level=false[a]"])
    run(["ffmpeg", "-y", "-loglevel", "error", *inp, "-filter_complex", graph, "-map", "0:v", "-map", "[a]", "-t", total,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", proj / "video.mp4"])
    print("xong:", proj / "video.mp4")

def cmd_qa(proj):
    f = proj / "video.mp4"; total = load(proj / "audio/sfx.json")["total"]
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(f), "-vf", "blackdetect=d=0.5:pix_th=0.05",
                        "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr); peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p.stderr)
    q = {"duration": round(dur(f), 2), "expected": total, "size_mb": round(f.stat().st_size / 1e6, 1), "decode": "ok" if p.returncode == 0 else "LỖI",
         "black_over_0.5s": re.findall(r"black_start:\S+ black_end:\S+", p.stderr), "loudness_lufs": lufs[-1] if lufs else None,
         "true_peak_dbfs": peak[-1] if peak else None, "human_review": "chưa nghe/xem"}
    (proj / "review").mkdir(exist_ok=True)
    for i, t in enumerate([1.5, total * .25, total * .5, total * .75, total - 3]):
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", round(t, 2), "-i", f, "-frames:v", 1, proj / f"review/final-{i}.jpg"])
    save(q, proj / "QA.json"); print(json.dumps(q, ensure_ascii=False, indent=1))
    if abs(q["duration"] - total) > .5 or q["decode"] != "ok" or q["black_over_0.5s"]: raise SystemExit("QA không đạt — xem QA.json")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Dựng video tin tức từ voice + plan.json")
    ap.add_argument("cmd", choices=["subs", "build", "snap", "render", "qa", "publish", "all"]); ap.add_argument("project")
    a = ap.parse_args(); proj = pathlib.Path(a.project).resolve()
    steps = ["subs", "build", "snap", "render", "qa"] if a.cmd == "all" else [a.cmd]
    for s in steps: globals()[f"cmd_{s}"](proj)
