"""Bộ dựng video demo sản phẩm (screendemo): lời đọc ↔ bản quay màn hình ↔ camera ↔ phụ đề ↔ sticker ↔ SFX.

Ý tưởng (làm chuẩn từ clip StradeVn sầu riêng 0810.60, 04/11/2026):
- Lời đọc: mỗi câu (audio/V*.mp3) được cắt thành CỤM theo dấu câu, mốc cắt nằm ở khoảng lặng thật (chunks.py).
- Cảnh quay màn hình: mỗi cụm lời gắn vào 1 MỐC trong marks.json của bản quay (vd "ve-178" = lúc khoanh 17,8%).
  Bộ dựng tự tính tốc độ phát từng đoạn bản quay để mốc hiện đúng lúc giọng nói tới (đoạn gõ/chờ thì tua nhanh,
  có nhãn "⏩ tua nhanh"; đoạn nói dài hơn thao tác thì đứng hình ở 0.8×), camera phóng sát vào khung chữ ở mốc.
- Khoanh mực chỉ ở con số chính (rec.mark_text); chỗ khác chỉ phóng camera (rec.focus). Sticker ≤ 1/10–15 s.

Dùng trong story.py của clip (xem KIT/screendemo/templates/genres/*/story.py):
    from engine import Story
    st = Story(HERE, variant=os.environ.get("VARIANT", "full"))
    P, Kf = st.P, st.Kf
    st.screen("h2", ("start", 0.4), "end", [P("V4", 0, 2, at=("start", 0.8)), ...], badge="BƯỚC 1 · …")
    st.finish(title="…")
"""
import json, os, pathlib, re, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from chunks import all_chunks

IN = lambda sel, t, frm="y:60,opacity:0", to="y:0,opacity:1", d=.45, ease="E": \
    f"tl.fromTo('{sel}',{{{frm}}},{{{to},duration:{d},ease:{ease},immediateRender:false}},{t:.3f});"

SFX = dict(whoosh="sfx/pixabay/whoosh-short.mp3", pop="sfx/pixabay/pop.mp3", ink="sfx/mixkit/ui/ui-option-select.mp3")


class Story:
    GAP = 0.22                      # nghỉ tối thiểu giữa 2 cụm lời
    W, H = 1080, 1920
    CW, CHH, CX, CY = 780, 1170, 110, 250     # khung quay màn hình (tỉ lệ 2:3 như bản quay 720×1080)
    REC_W = 720
    STK_POS = dict(x=830, y=150, w=220)

    def __init__(self, proj, variant="full", variants_out=None, brand=None):
        """proj = thư mục clip. variant = tên bản ("full" → xuất ngay thư mục clip; bản khác → <clip>/<variant>/ với
        <base href="../"> dùng chung assets/audio). brand = dict(hl, accent) đổi màu nhấn của style.css."""
        self.proj = pathlib.Path(proj).resolve(); self.variant = variant
        self.out = self.proj if variant == "full" else self.proj / variant
        self.brand = brand or {}
        self.K = self.CW / self.REC_W
        self.CH = all_chunks(self.proj)
        self.REC = {}
        self.pieces, self.caps, self.stickers, self.sfx, self.html, self.js = [], [], [], [], [], []
        self.state = dict(now=0.0, last=0.0)
        self.screens = []           # [(rec, clips)] — để dựng lớp phủ theo thời gian THẬT của bản quay (vd đồng hồ bấm giờ)

    # ------------------------------------------------------------ mốc bản quay
    def marks(self, h):
        if h not in self.REC:
            m = json.load(open(self.proj / f"assets/screen/{h}/marks.json", encoding="utf-8"))["marks"]
            self.REC[h] = {x["name"]: x for x in m}; self.REC[h]["__list"] = m
        return self.REC[h]

    def M(self, h, at):
        name, dt = at if isinstance(at, tuple) else (at, 0.0)
        if isinstance(name, (int, float)): return float(name) + dt
        try: return self.marks(h)[name]["t"] + dt
        except KeyError: raise SystemExit(f"bản quay {h} không có mốc {name!r} — xem assets/screen/{h}/marks.json")

    # ------------------------------------------------------------ hạng mục
    @staticmethod
    def P(line, i, j, at=None, lead=0.0, hint=1.0, meme=None, after=None):
        """Cụm lời line[i:j]. at = mốc bản quay (tên, ±giây) mà lời bắt đầu nói; hint >1 = cho phép tua nhanh tới mốc;
        meme = id sticker hiện lúc bắt đầu nói; after = giây nghỉ thêm trước cụm (cảnh thẻ)."""
        return dict(k="P", line=line, i=i, j=j, at=at, lead=lead, hint=hint, meme=meme, after=after)

    @staticmethod
    def Kf(chunk, at):
        """Mốc phụ: cụm thứ `chunk` của cụm lời vừa đặt phải trùng mốc bản quay `at`."""
        return dict(k="K", chunk=chunk, at=at)

    def is_gap(self, line, b):      # mốc cắt b (chỉ số cụm) có nằm ở khoảng lặng thật không
        cs = self.CH[line]
        return b == 0 or b == len(cs) or cs[b]["s"] - cs[b - 1]["e"] > 0.12

    def place(self, item, onset):
        """Đặt cụm lời sao cho tiếng nói bắt đầu ở `onset` (giây tuyệt đối). Trả về lúc nói xong."""
        line, i, j = item["line"], item["i"], item["j"]
        if line not in self.CH: raise SystemExit(f"chưa có câu {line} trong audio/timing.json — đọc giọng trước (tts_script.py)")
        cs = self.CH[line]
        if not (0 <= i < j <= len(cs)):
            raise SystemExit(f"{line} chỉ có {len(cs)} cụm (cắt theo dấu , . : ? !) mà story.py đòi cụm {i}–{j} — "
                             f"sửa dấu câu trong voice.json cho đủ cụm, hoặc sửa chỉ số trong story.py (xem: python KIT/screendemo/chunks.py <clip>)")
        for b in (i, j):
            if not self.is_gap(line, b): raise SystemExit(f"{line}: mốc cắt trước cụm {b} không nằm ở khoảng lặng — gộp cụm lại")
        a, b = cs[i]["a"], cs[j - 1]["b"]
        t0 = onset - (cs[i]["s"] - a)
        self.pieces.append(dict(line=line, a=a, b=b, t=round(t0, 3), s=cs[i]["s"], e=cs[j - 1]["e"]))
        for k in range(i, j):
            c = cs[k]; self.caps.append(dict(s=t0 + c["s"] - a, e=t0 + c["e"] - a, text=c["cap"], piece=len(self.pieces)))
        end = t0 + cs[j - 1]["e"] - a
        if item.get("meme"): self.add_sticker(item["meme"], onset)
        self.state["last"] = end
        return end

    def chunk_onset(self, line, k):
        p = self.pieces[-1]; return p["t"] + self.CH[line][k]["s"] - p["a"]

    def add_sticker(self, mid, t, dur=2.4, **pos):
        p = {**self.STK_POS, **pos}
        self.stickers.append(dict(id=mid, t=round(t, 2), dur=dur, **p))
        self.sfx.append(dict(t=t, file=SFX["pop"], volume=0.45))

    def add_sfx(self, t, file, volume=0.5, dur=None):
        """file = đường dẫn SFX, hoặc "meme:<id>" = tiếng meme trong meme-library/web.json (tải lúc finish)."""
        self.sfx.append(dict(t=t, file=file, volume=volume, **({"dur": dur} if dur else {})))

    def add_meme_sound(self, mid, t, volume=0.7, dur=None):
        """Meme chỉ có tiếng (vd vn-10-diem, vine-boom): không hiện hình, chỉ phát tiếng ở giây t."""
        self.add_sfx(t, f"meme:{mid}", volume, dur)

    @property
    def now(self): return self.state["now"]

    @property
    def last(self): return self.state["last"]

    # ------------------------------------------------------------ cảnh quay màn hình
    def screen(self, rec, r0, r1, items, badge, tail=0.6, tail_hint=1.0, pre=0.35):
        """Cảnh bản quay `rec` (assets/screen/<rec>/) từ mốc r0 tới r1, khớp các cụm lời `items` vào mốc."""
        M = lambda at: self.M(rec, at)
        c_start = self.state["now"]; a0 = M(r0); a_end = M(r1)
        anchors = [(a0, c_start)]; last_item = None
        for it in items:
            pa, pc = anchors[-1]
            if it["k"] == "K":
                line = last_item["line"]; a = M(it["at"]); c = self.chunk_onset(line, it["chunk"])
                if c <= pc or a <= pa: raise SystemExit(f"mốc phụ {it} lệch thứ tự")
                anchors.append((a, c)); continue
            a = M(it["at"]); lead = it["lead"]
            onset = max(pc + (a - pa) / it["hint"] + lead, self.state["last"] + self.GAP, c_start + pre)
            c = onset - lead
            if a < pa: raise SystemExit(f"mốc {it['at']} đi lùi")
            anchors.append((a, c)); self.place(it, onset); last_item = it
        pa, pc = anchors[-1]
        c_end = max(pc + (a_end - pa) / tail_hint, self.state["last"] + tail)
        anchors.append((a_end, c_end))
        clips = []
        for (ra, ca), (rb, cb) in zip(anchors, anchors[1:]):
            if cb - ca < 0.02: continue
            rate = (rb - ra) / (cb - ca) if rb > ra else 0.0
            clips.append(dict(c0=ca, c1=cb, r0=ra, r1=rb, rate=max(rate, 0.8) if rb > ra else 1.0))
        def cmap(t):
            for cl in clips:
                if cl["r0"] - 1e-6 <= t <= cl["r1"] + 1e-6:
                    return min(cl["c1"], cl["c0"] + (t - cl["r0"]) / cl["rate"])
            return None
        sid = f"s{len(self.html)}"; CW, CHH, K = self.CW, self.CHH, self.K
        body = [f'<div class="step">{badge}</div><div class="card" id="{sid}c"><div class="cam" id="{sid}m">']
        for cl in clips:
            body.append(f'<div class="clip" data-start="{cl["c0"]:.3f}" data-duration="{cl["c1"] - cl["c0"]:.3f}">'
                        f'<video src="assets/screen/{rec}/screen.mp4" muted playsinline preload="auto" data-offset="{cl["r0"]:.3f}" '
                        f'data-end="{cl["r1"]:.3f}" data-rate="{cl["rate"]:.3f}"></video></div>')
        body.append('</div>')
        for cl in clips:
            if cl["rate"] >= 1.8 and cl["c1"] - cl["c0"] > 1.2:
                body.append(f'<div class="clip ff" data-start="{cl["c0"]:.3f}" data-duration="{cl["c1"] - cl["c0"]:.3f}">'
                            f'<span>⏩ tua nhanh ×{cl["rate"]:.1f}</span></div>')
        body.append('</div>')
        self.html.append(f'<section class="clip" data-start="{c_start:.3f}" data-duration="{c_end - c_start:.3f}">{"".join(body)}</section>')
        self.js.append(f"tl.fromTo('#{sid}c',{{y:70,opacity:0}},{{y:0,opacity:1,duration:.45,ease:E}},{c_start:.3f});")
        self.sfx.append(dict(t=c_start, file=SFX["whoosh"], volume=0.35))
        # camera: phóng vào khung chữ ở mỗi mốc có box; mốc chuyển trang (không box) → lùi ra
        ev = []
        for m in self.marks(rec)["__list"]:
            if not (a0 <= m["t"] <= a_end): continue
            t = cmap(m["t"])
            if t is None: continue
            if "box" in m:
                ev.append((t, "in", m))
                if m.get("ink", True): self.sfx.append(dict(t=t + 0.35, file=SFX["ink"], volume=0.3))
            elif m["name"] not in ("start", "end"): ev.append((t, "out", m))
        zoomed = False
        for n, (t, kind, m) in enumerate(ev):
            nxt = ev[n + 1][0] if n + 1 < len(ev) else c_end
            if kind == "in":
                b = m["box"]; s = min(1.9, max(1.3, 0.62 * CW / (b["w"] * K + 90)))
                cx, cy = (b["x"] + b["w"] / 2) * K, (b["y"] + b["h"] / 2) * K
                tx = min(0, max(CW - s * CW, CW / 2 - s * cx)); ty = min(0, max(CHH - s * CHH, CHH * 0.45 - s * cy))
                self.js.append(f"tl.to('#{sid}m',{{x:{tx:.1f},y:{ty:.1f},scale:{s:.3f},duration:.6,ease:'power2.inOut'}},{max(c_start, t - 0.3):.3f});")
                zoomed = True
                if nxt - t > 4.5:
                    self.js.append(f"tl.to('#{sid}m',{{x:0,y:0,scale:1,duration:.6,ease:'power2.inOut'}},{t + 2.8:.3f});"); zoomed = False
            elif zoomed:
                self.js.append(f"tl.to('#{sid}m',{{x:0,y:0,scale:1,duration:.5,ease:'power2.inOut'}},{max(c_start, t - 0.25):.3f});"); zoomed = False
        self.state["now"] = c_end; self.screens.append((rec, clips))
        print(f"  {rec:4s} {c_start:6.2f}–{c_end:6.2f}  " + " ".join(f"{cl['rate']:.2f}" for cl in clips))
        return sid

    # ------------------------------------------------------------ cảnh thẻ chữ
    def card(self, items, body, tail=0.35, pre=0.15, cls="", anim=None, min_dur=0):
        """items: cụm lời đọc nối tiếp; body: HTML; anim(starts, c0) → danh sách lệnh GSAP (starts = lúc bắt đầu nói từng cụm)."""
        c0 = self.state["now"]; starts = []
        for it in items:
            onset = max(c0 + pre, self.state["last"] + self.GAP) + (it["after"] or 0)
            starts.append(onset); self.place(it, onset)
            starts.extend(self.chunk_onset(it["line"], k) for k in range(it["i"] + 1, it["j"]))
        c1 = max(self.state["last"] + tail, c0 + min_dur)
        self.html.append(f'<section class="clip {cls}" data-start="{c0:.3f}" data-duration="{c1 - c0:.3f}">{body}</section>')
        if anim: self.js.extend(anim(starts, c0))
        self.sfx.append(dict(t=c0, file=SFX["whoosh"], volume=0.35))
        self.state["now"] = c1
        print(f"  card {c0:6.2f}–{c1:6.2f}")
        return starts

    # ------------------------------------------------------------ xuất
    @staticmethod
    def fmt_caption(t):
        t = re.sub(r"(\d[\d.,]*\s?(%|tỷ USD|USD/kg|USD)?)", r"<b>\1</b>", t)
        return t.replace("BẠN", "<b>BẠN</b>")

    def finish(self, title="Video", css_extra="", bgm="bgm/mixkit/house-vibez.mp3", bgm_volume=0.14):
        """Ghi <out>/index.html + audio/narration_<variant>.wav + <out>/cues.json."""
        DUR = round(self.state["now"], 2)
        groups = []
        for c in self.caps:              # phụ đề: gộp cụm ngắn trong cùng cụm lời
            g = groups[-1] if groups else None
            if g and g["piece"] == c["piece"] and (len(g["text"].split()) < 4 or len(g["text"].split()) + len(c["text"].split()) <= 8) \
                    and len(g["text"]) + len(c["text"]) < 52:
                g["text"] += " " + c["text"]; g["e"] = c["e"]
            else:
                groups.append(dict(c))
        cap_html = []
        for n, g in enumerate(groups):
            nxt = groups[n + 1]["s"] if n + 1 < len(groups) else DUR
            e = min(g["e"] + 0.35, nxt - 0.02) if nxt - g["e"] < 1.2 else g["e"] + 0.35
            cap_html.append(f'<div class="cap" data-start="{g["s"] - 0.05:.3f}" data-duration="{e - g["s"] + 0.05:.3f}"><span>{self.fmt_caption(g["text"])}</span></div>')
        # meme web (meme-library/web.json): chỉ có link → ffmpeg tải đúng đoạn, tách nền vào assets/meme; tiếng meme thay SFX pop
        try:
            sys.path.insert(0, str(HERE.parent / "tools")); import meme_web
            web = meme_web.catalog()
        except Exception as e:
            web = {}; print(f"  ⚠ meme web: {e}")
        snd = [x for x in self.sfx if str(x["file"]).startswith("meme:")]
        # sticker trỏ tới meme chỉ có tiếng → đổi thành tiếng (không có hình để hiện)
        for s in [s for s in self.stickers if web.get(s["id"], {}).get("kind") == "sound"]:
            self.stickers.remove(s)
            self.sfx = [x for x in self.sfx if not (x["file"] == SFX["pop"] and abs(x["t"] - s["t"]) < 0.01)]
            snd.append(dict(t=s["t"], file=f"meme:{s['id']}", volume=s.get("volume", 0.7))); self.sfx.append(snd[-1])
        need = sorted({s["id"] for s in self.stickers if s["id"] in web} | {x["file"][5:] for x in snd if x["file"][5:] in web})
        got = meme_web.fetch(self.proj, need) if need else {}
        for x in snd:
            a = (got.get(x["file"][5:]) or {}).get("audio")
            if a: x["file"] = a
            else: print(f"  ⚠ không có tiếng meme {x['file']}"); self.sfx.remove(x)
        for s in self.stickers:
            g = got.get(s["id"])
            if not g: continue
            if g.get("audio") and web[s["id"]].get("sound", True):
                self.sfx = [x for x in self.sfx if not (x["file"] == SFX["pop"] and abs(x["t"] - s["t"]) < 0.01)]
                self.sfx.append(dict(t=s["t"], file=g["audio"], volume=s.get("volume", 0.6), dur=s["dur"]))
        stk_html = []
        for n, s in enumerate(self.stickers):
            stk_html.append(f'<div class="clip stk" data-start="{s["t"]:.3f}" data-duration="{s["dur"]:.3f}">'
                            f'<div class="sk" id="sk{n}" style="left:{s["x"]}px;top:{s["y"]}px;width:{s["w"]}px">'
                            f'<video src="assets/meme/{s["id"]}.webm" muted playsinline preload="auto" data-loop="1"></video></div></div>')
            self.js.append(f"tl.fromTo('#sk{n}',{{scale:0,rotation:-25}},{{scale:1,rotation:0,duration:.45,ease:'back.out(2.2)'}},{s['t']:.3f});")
            self.js.append(f"tl.to('#sk{n}',{{scale:0,duration:.25,ease:'power2.in'}},{s['t'] + s['dur'] - 0.28:.3f});")
        css = "\n" + (HERE / "templates/style.css").read_text(encoding="utf-8").strip("\n") + "\n" + css_extra
        hl, acc = self.brand.get("hl", "#FBBF24"), self.brand.get("accent", "#4F46E5")
        css = css.replace("#FBBF24", hl).replace("#4F46E5", acc)
        tpl = (HERE / "templates/template.html").read_text(encoding="utf-8")
        fonts = (self.proj / "fonts.css.part").read_text(encoding="utf-8")
        out = (tpl.replace("/*FONTS*/", fonts + css).replace("__W__", str(self.W)).replace("__H__", str(self.H)).replace("__D__", str(DUR))
               .replace("__HL__", hl).replace("__ACCENT__", acc).replace("__CAPTOP__", "1440").replace("Video marketing", title)
               .replace("__SECTIONS__", "\n".join(self.html + stk_html)).replace("__CAPTIONS__", "\n".join(cap_html)).replace("__JS__", "\n".join(self.js)))
        if self.out != self.proj: out = out.replace("<head>", '<head><base href="../">', 1)
        self.out.mkdir(exist_ok=True); (self.out / "index.html").write_text(out, encoding="utf-8")
        # giọng đọc: ghép các cụm vào đúng chỗ
        A = self.proj / "audio"; args, flt = [], []
        for n, p in enumerate(self.pieces):
            args += ["-i", str(A / f"{p['line']}.mp3")]
            ms = int(round(p["t"] * 1000)); d = p["b"] - p["a"]
            flt.append(f"[{n}:a]atrim={p['a']:.3f}:{p['b']:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,"
                       f"afade=t=out:st={max(0, d - 0.04):.3f}:d=0.04,adelay={ms}|{ms}[p{n}]")
        flt.append("".join(f"[p{n}]" for n in range(len(self.pieces))) + f"amix=inputs={len(self.pieces)}:normalize=0,apad,atrim=0:{DUR}[o]")
        fc = A / f"_narration_{self.variant}.filter"; fc.write_text(";".join(flt), encoding="utf-8")
        wav = A / f"narration_{self.variant}.wav"
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", *args, "-/filter_complex", str(fc), "-map", "[o]", "-ar", "44100", str(wav)], check=True)
        ps = sorted(self.pieces, key=lambda p: p["t"])
        for x, y in zip(ps, ps[1:]):     # chỉ tính phần CÓ TIẾNG (bỏ khoảng lặng đệm 2 đầu cụm)
            if x["t"] + (x["e"] - x["a"]) > y["t"] + (y["s"] - y["a"]) + 0.02:
                print(f"  ⚠ chồng tiếng: {x['line']} → {y['line']} @ {y['t']:.2f}")
        cues = {"duration": DUR, "voice": {"file": str(wav), "volume": 1.0},
                # từng cụm lời (file, đoạn cắt a–b trong file, đặt ở giây t) — để tools/to_studio.py tách thành
                # từng đoạn tiếng sửa được trong HyperFrames Studio
                "pieces": [dict(line=p["line"], file=str(A / f"{p['line']}.mp3"), a=round(p["a"], 3), b=round(p["b"], 3),
                                t=round(p["t"], 3)) for p in sorted(self.pieces, key=lambda p: p["t"])],
                "bgm": {"file": bgm, "volume": bgm_volume, "start": 0, "fade_in": 0.5, "fade_out": 2.5, "duck": True},
                "sfx": sorted(({**s, "t": round(s["t"], 3)} for s in self.sfx), key=lambda s: s["t"])}
        (self.out / "cues.json").write_text(json.dumps(cues, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"xong: index.html · {DUR}s · {len(self.pieces)} cụm lời · {len(groups)} phụ đề · {len(self.stickers)} sticker · {len(self.sfx)} SFX")
        return DUR
