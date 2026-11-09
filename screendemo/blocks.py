"""Cảnh thẻ chữ dựng sẵn cho video demo sản phẩm. Mỗi hàm nhận Story + cụm lời, tự lo HTML/hoạt ảnh/SFX/sticker.
Lời đọc phải có đủ số cụm như ghi chú từng hàm (đếm cụm: python KIT/screendemo/chunks.py <clip>)."""
from html import escape
import re
import unicodedata

from engine import IN


def hook_number(st, item, value, kicker, unit, chip, source, bg=None, decimals=2):
    """Mở đầu bằng 1 CON SỐ THẬT đếm lên (không sticker). item: 3 cụm — [kicker] [con số] [câu chốt].
    bg = ảnh nền nhoè (vd ảnh chụp bài báo lúc quay: assets/screen/<rec>/bai-bao.png)."""
    def a(sts, c0):
        n = sts[1]
        return [f"tl.set('#k1,#n1,#c1,#src1',{{opacity:0}},0);",
                f"tl.fromTo('.bg',{{scale:1.12}},{{scale:1.3,duration:9,ease:'none'}},0);",
                IN('#k1', sts[0] - 0.1), IN('#n1', n - 0.1, "scale:.6,opacity:0", "scale:1,opacity:1", .45, "'back.out(2)'"),
                f"const n1={{v:0}}; tl.to(n1,{{v:{value},duration:1.3,ease:'power2.out',onUpdate:()=>document.getElementById('num').textContent=n1.v.toFixed({decimals}).replace('.',',')}},{n - 0.1:.3f});",
                IN('#src1', n + 1.0, "opacity:0", "opacity:1"), IN('#c1', sts[2] + 0.4)]
    zero = "0," + "0" * decimals if decimals else "0"
    bgh = f'<img class="full bg blur" src="{bg}"><div class="dim"></div>' if bg else '<div class="grad"></div>'
    sts = st.card([item], bgh + f'<div class="kicker" id="k1">{kicker}</div>'
                  f'<div class="big" id="n1"><span id="num">{zero}</span><small>{unit}</small></div>'
                  f'<div class="chip1" id="c1">{chip}</div>'
                  f'<div class="src" id="src1">{source}</div>', anim=a, pre=0.3)
    st.sfx += [dict(t=0.05, file="sfx/mixkit/transition/whoosh-fast.mp3", volume=0.45),
               dict(t=sts[1] - 0.1, file="sfx/pixabay/impact-bass-1.mp3", volume=0.7)]
    return sts


def question(st, item, q1, q2, sticker="thinking"):
    """Câu hỏi xoáy. item: 3 cụm — [dẫn] [q1] [q2]. q1/q2 là HTML (dùng <span class="hl">…</span> để tô)."""
    def a(sts, c0):
        return [f"tl.set('#q1,#q2',{{opacity:0}},0);", IN('#q1', sts[1] - 0.1),
                IN('#q2', sts[2], "scale:.7,opacity:0", "scale:1,opacity:1", .35, "'back.out(2.5)'")]
    sts = st.card([item], f'<div class="grad"></div><div class="q" id="q1">{q1}</div><div class="q2" id="q2">{q2}</div>', anim=a)
    if sticker: st.add_sticker(sticker, sts[2] + 0.15, dur=2.2, x=430, y=1010, w=220)
    st.sfx.append(dict(t=sts[2], file="sfx/pixabay/impact-bass-2.mp3", volume=0.5))
    return sts


def clock(st, item, clock_text, title, sub, sub_top=870):
    """Mở bối cảnh "một buổi sáng…". item: 2 cụm."""
    def a(sts, c0):
        return [f"tl.set('#ck,#q3,#s3',{{opacity:0}},0);", IN('#ck', c0 + 0.1, "y:-50,opacity:0"), IN('#q3', sts[1] - 0.2),
                IN('#s3', sts[1] + 0.9, "opacity:0", "opacity:1")]
    return st.card([item], f'<div class="grad"></div><div class="clock" id="ck">{clock_text}</div>'
                   f'<div class="q" id="q3">{title}</div>'
                   f'<div class="sub2" id="s3" style="top:{sub_top}px">{sub}</div>', anim=a)


def timeskip(st, item, big, sub):
    """Thẻ nhảy thời gian ("8 PHÚT SAU"). item: 1 cụm."""
    def a(sts, c0):
        return [IN('#ts', c0 + 0.05, "scale:1.6,opacity:0", "scale:1,opacity:1", .4, "'back.out(2)'"), IN('#ts2', c0 + 0.5, "opacity:0", "opacity:1")]
    sts = st.card([item], f'<div class="grad"></div><div class="ts" id="ts">{big}</div>'
                  f'<div class="sub2" id="ts2" style="top:1060px">{sub}</div>', anim=a, min_dur=1.6, tail=0.2)
    st.sfx.append(dict(t=st.now - 1.6, file="sfx/mixkit/counter/clock-tick-single.mp3", volume=0.6))
    return sts


def recap(st, items, rows, ask, cta="Bình luận nhé", sticker="point-down"):
    """Tổng kết 3 dòng + câu hỏi kêu gọi bình luận. items: [P(3 cụm = 3 dòng), P(2 cụm = câu hỏi + kêu gọi)].
    rows: 3 chuỗi HTML (dùng <i>…</i> để tô số)."""
    def a(sts, c0):
        return [f"tl.set('#r1,#r2,#r3,#cq,#cq2',{{opacity:0}},0);",
                IN('#r1', sts[0] - 0.1, "x:-80,opacity:0", "x:0,opacity:1"), IN('#r2', sts[1] - 0.1, "x:-80,opacity:0", "x:0,opacity:1"),
                IN('#r3', sts[2] - 0.1, "x:-80,opacity:0", "x:0,opacity:1"),
                f"tl.to('#recap',{{y:-120,scale:.82,opacity:.35,duration:.5,ease:E}},{sts[3] - 0.4:.3f});",
                IN('#cq', sts[3] - 0.1, "scale:.7,opacity:0", "scale:1,opacity:1", .4, "'back.out(2)'"), IN('#cq2', sts[4] - 0.1)]
    body = '<div class="grad"></div><div id="recap">' + "".join(
        f'<div class="row" id="r{n + 1}"><b>{n + 1}</b><span>{r}</span></div>' for n, r in enumerate(rows)) + '</div>' \
        f'<div class="q" id="cq" style="top:880px">{ask}</div><div class="cmt" id="cq2">{cta}</div>'
    sts = st.card(items, body, anim=a, tail=0.4)
    if sticker: st.add_sticker(sticker, sts[4] - 0.1, dur=2.0, x=430, y=1260, w=220)
    return sts


def logo_end(st, item, name, tagline, url, logo="assets/logo.jpg"):
    """Kết bằng logo thật + câu định vị + địa chỉ web. item: 2 cụm."""
    def a(sts, c0):
        return [IN('#lg', c0 + 0.05, "scale:.6,opacity:0", "scale:1,opacity:1", .5, "'back.out(2)'"), IN('#tg', sts[1] - 0.1),
                IN('#url', sts[1] + 0.8, "opacity:0", "opacity:1")]
    sts = st.card([item], '<div class="grad"></div><div class="brand" id="lg" style="position:absolute;top:640px;left:0;right:0">'
                  f'<img src="{logo}"><div class="name">{name}</div></div>'
                  f'<div class="sub" id="tg" style="top:900px">{tagline}</div>'
                  f'<div class="url" id="url">{url}</div>', anim=a, tail=1.6)
    st.sfx.append(dict(t=st.now - 5.0, file="sfx/mixkit/ui/chime-crystal.mp3", volume=0.5))
    return sts


def _block_text(value):
    """Plain text, NFC keeps Vietnamese combining accents together during wipes."""
    return escape(unicodedata.normalize("NFC", str(value)))


def _block_cues(item, cues):
    cues = tuple(cues)
    count = item["j"] - item["i"]
    if (len(cues) != 3 or any(type(c) is not int or not 0 <= c < count for c in cues)
            or not cues[0] < cues[1] < cues[2]):
        raise ValueError("cues must be three increasing chunk indices within item (relative to item.i)")
    return cues


def _block_style(st, sid):
    # Require the actual profile palette instead of silently inventing brand colors.
    colors = {k: st.brand.get(k) for k in ("hl", "accent")}
    colors.update({k: st.brand.get(k, v) for k, v in
                   dict(bg="#0B1020", fg="#FFFFFF", muted="#CBD5E1").items()})
    if any(not isinstance(v, str) or not re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", v)
           for v in colors.values()):
        raise ValueError("Pass profile['brand'] to Story(brand=...); hl/accent (and optional bg/fg/muted) must be hex colors")
    variables = ";".join(f"--{k}:{v}" for k, v in colors.items())
    return (f"#{sid}{{{variables};position:absolute;inset:0;background:var(--bg);color:var(--fg);"
            "font-family:'Be Vietnam Pro',sans-serif;font-weight:800;font-size:44px;line-height:1.35}"
            f"#{sid} *{{box-sizing:border-box}}"
            f"#{sid} .copy{{white-space:pre-line;overflow-wrap:anywhere}}")


def flow_diagram(st, item, nodes, title="", details=None, cues=(0, 1, 2)):
    """Three stacked cards; SVG light reaches each next card on its voice cue.

    item: P(...) with >=3 chunks; cues: three relative chunk indices (default 0,1,2).
    nodes: exactly three plain-text labels; details: optional three plain-text sublabels.
    title: optional plain text. Uses st.brand from profile; returns absolute chunk starts.
    Designed for 1080x1920: 68/44px type (44px matches engine captions).
    """
    cues = _block_cues(item, cues)
    if isinstance(nodes, str) or len(nodes) != 3:
        raise ValueError("flow_diagram needs exactly three node labels")
    if details is None:
        details = ("", "", "")
    if isinstance(details, str) or len(details) != 3:
        raise ValueError("details must contain exactly three sublabels")
    sid = f"flow{len(st.html)}"
    css = _block_style(st, sid) + f"""
#{sid} .heading{{position:absolute;left:100px;top:265px;width:780px;color:var(--muted);opacity:0}}
#{sid} .node{{position:absolute;left:100px;width:780px;height:230px;padding:24px 34px;
border:2px solid var(--accent);border-left:8px solid var(--hl);border-radius:24px;background:var(--bg);
display:flex;flex-direction:column;justify-content:center;gap:8px;opacity:0}}
#{sid} .label{{font-size:68px;line-height:1.3;letter-spacing:-1px}}
#{sid} .detail{{font-size:44px;color:var(--muted)}}
#{sid} .wires{{position:absolute;inset:0;width:1080px;height:1920px;overflow:visible}}
#{sid} .wire{{stroke:var(--hl);stroke-width:6;fill:none;stroke-linecap:round;
stroke-dasharray:100;stroke-dashoffset:100;filter:drop-shadow(0 0 8px var(--hl))}}
"""
    body = [f'<style>{css}</style><div id="{sid}">',
            '<svg class="wires" viewBox="0 0 1080 1920" aria-hidden="true">']
    for n, y in enumerate((630, 960)):
        body.append(f'<path id="{sid}-wire{n}" class="wire" pathLength="100" d="M490 {y} V{y + 100}"/>')
    body.append(f'</svg><div class="heading copy" id="{sid}-title">{_block_text(title)}</div>')
    for n, (label, detail) in enumerate(zip(nodes, details)):
        body.append(f'<div class="node" id="{sid}-node{n}" style="top:{400 + n * 330}px">'
                    f'<div class="label copy">{_block_text(label)}</div>'
                    f'<div class="detail copy">{_block_text(detail)}</div></div>')
    body.append('</div>')

    def anim(starts, c0):
        beats = [starts[c] for c in cues]
        js = [IN(f'#{sid}-title', c0 + .05, "y:18,opacity:0", d=.3, ease="'power3.out'")]
        for n, beat in enumerate(beats):
            js.append(IN(f'#{sid}-node{n}', beat, "y:28,opacity:0", d=.38, ease="'power3.out'"))
            if n:
                t = max(beats[n - 1], beat - .28)
                js.append(IN(f'#{sid}-wire{n - 1}', t, "strokeDashoffset:100", "strokeDashoffset:0",
                             round(beat + .1 - t, 3), "'power3.out'"))
        return js

    return st.card([item], "".join(body), anim=anim, pre=.3, tail=.65)


def kinetic_rehook(st, item, value, kicker, unit, payoff, cues=(0, 1, 2)):
    """Mid-clip masked type: kicker → ONE supplied number + unit → payoff.

    item: P(...) with >=3 chunks; cues: relative chunk indices for those three beats.
    value: a single formatted number, e.g. '12' or '17,8'; no count-up/invented values.
    kicker/unit/payoff: plain text, without additional digits. Short copy/newlines work best.
    Profile colors via st.brand. 148/44px type; returns absolute chunk starts.
    """
    cues = _block_cues(item, cues)
    value = unicodedata.normalize("NFC", str(value)).strip()
    if not re.fullmatch(r"[+−-]?\d+(?:[.,\u00a0\u202f]\d+)*", value):
        raise ValueError("value must be ONE formatted number; put its unit in unit")
    if any(char.isnumeric() for text in (kicker, unit, payoff) for char in str(text)):
        raise ValueError("kicker, unit and payoff must not introduce another number")
    sid = f"rehook{len(st.html)}"
    css = _block_style(st, sid) + f"""
#{sid} .kicker{{position:absolute;left:100px;top:320px;width:780px;color:var(--muted);opacity:0}}
#{sid} .rule{{position:absolute;left:100px;top:430px;width:780px;height:8px;background:var(--accent);transform:scaleX(0);transform-origin:left}}
#{sid} .metric{{position:absolute;left:100px;top:470px;width:780px;opacity:0}}
#{sid} .value{{font-size:148px;line-height:1.35;color:var(--hl);letter-spacing:-4px}}
#{sid} .unit{{font-size:44px;color:var(--muted)}}
#{sid} .stack{{position:absolute;left:100px;top:820px;width:780px}}
#{sid} .layer{{font-size:148px;line-height:1.35;letter-spacing:-4px;opacity:0;padding:12px 0}}
#{sid} .echo{{position:absolute;inset:0;color:transparent;-webkit-text-stroke:2px var(--accent)}}
#{sid} .front{{position:relative;color:var(--fg)}}
"""
    body = (f'<style>{css}</style><div id="{sid}">'
            f'<div class="kicker copy" id="{sid}-kicker">{_block_text(kicker)}</div>'
            f'<div class="rule" id="{sid}-rule"></div>'
            f'<div class="metric" id="{sid}-metric"><div class="value copy">{_block_text(value)}</div>'
            f'<div class="unit copy">{_block_text(unit)}</div></div>'
            f'<div class="stack"><div class="layer echo copy" id="{sid}-echo" aria-hidden="true">{_block_text(payoff)}</div>'
            f'<div class="layer front copy" id="{sid}-front">{_block_text(payoff)}</div></div></div>')

    def anim(starts, c0):
        lead, number, punch = (starts[c] for c in cues)
        wipe = "clipPath:'inset(0 100% 0 0)',x:-32,opacity:0"
        shown = "clipPath:'inset(0 0% 0 0)',x:0,opacity:1"
        return [IN(f'#{sid}-kicker', lead, "y:24,opacity:0", d=.32, ease="'power3.out'"),
                IN(f'#{sid}-rule', lead, "scaleX:0", "scaleX:1", .4, "'power3.out'"),
                IN(f'#{sid}-metric', number, wipe, shown, .42, "'power3.out'"),
                IN(f'#{sid}-echo', punch, "x:-30,y:24,opacity:0", "x:16,y:16,opacity:.65", .3, "'power3.out'"),
                IN(f'#{sid}-front', punch + .06, wipe, shown, .42, "'power3.out'"),
                IN(f'#{sid}-echo', punch + .32, "x:16,y:16,opacity:.65", "x:8,y:8,opacity:.25", .3, "'power3.out'")]

    return st.card([item], body, anim=anim, pre=.3, tail=.8)
