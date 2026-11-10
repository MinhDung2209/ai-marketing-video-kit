"""Chuyển 1 bản video đã dựng của kit (index.html + cues.json) thành PROJECT HYPERFRAMES CHUẨN, mở/sửa được trong
HyperFrames Studio (`npx hyperframes preview`) và render bằng `npx hyperframes render` — người và agent cùng sửa 1 nguồn.

  python KIT/tools/to_studio.py <thư mục bản dựng> <thư mục project ra> [--lufs -14]
  vd: python KIT/tools/to_studio.py D:/Projects/stradevn-video/clips/02-ho-tieu-090411 D:/Projects/video-studio/stradevn/02-ho-tieu-full

Khác bản kit:
- video quay màn hình: thời gian/cắt/tốc độ ghi THẲNG trên <video> (data-start/-duration/-media-start/-playback-rate)
  thay cho data-offset/-end/-rate do render.py của kit tự tua;
- tiếng KHÔNG trộn sẵn nữa: mỗi cụm lời là 1 <audio> riêng (track Giọng), nhạc nền có làn hạ nhạc khi có giọng
  (data-automation), mỗi hiệu ứng / meme là 1 <audio> → bỏ, thay, dời từng đoạn ngay trên timeline;
- âm lượng đã tính sẵn để cả bài ≈ -14 LUFS (đo bằng chính bản trộn của kit);
- mỗi phần tử có id + data-track-index (làn trên timeline Studio).
File media được HARD-LINK (không tốn thêm ổ đĩa) nếu cùng ổ, không thì chép."""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import argparse, json, os, pathlib, re, shutil, subprocess

KIT = pathlib.Path(__file__).resolve().parent.parent; LIB = KIT / "audio-library"
sys_path = str(KIT / "tools"); _sys.path.insert(0, sys_path)
from mix_audio_peak import peak_db

# làn timeline (chỉ để Studio hiển thị, không ảnh hưởng thứ tự vẽ)
TRACK = dict(scene=0, screen=1, overlay=2, sticker=3, caption=4, voice=5, sfx=6, bgm=7)


def link(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists(): dst.unlink()
    try: os.link(src, dst)
    except OSError: shutil.copy2(src, dst)


def find(f, base):
    for p in (pathlib.Path(f), base / f, LIB / f):
        if p.exists(): return p
    raise SystemExit(f"không thấy file âm thanh: {f}")


def lufs(path):
    m = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    v = re.findall(r"I:\s+(-?[\d.]+) LUFS", m); return float(v[-1]) if v else None


def profile_rules(base):
    """Đóng gói luật gốc để project Studio không phụ thuộc đường dẫn về kit."""
    clip_file = base / "clip.json"
    if not clip_file.exists(): return {}
    profile = json.loads(clip_file.read_text(encoding="utf-8")).get("profile")
    if not profile: return {}
    profile_file = KIT / "profiles" / profile / "profile.json"
    if not profile_file.exists():
        raise SystemExit(f"không thấy hồ sơ luật doanh nghiệp: {profile_file}")
    p = json.loads(profile_file.read_text(encoding="utf-8"))
    rules = {key: p.get(key, {} if key == "safety" else []) for key in ("safety", "story_rules")}
    pronunciation = p.get("pronunciation", p.get("voice", {}).get("pronounce"))
    if pronunciation is not None: rules["pronunciation"] = pronunciation
    return rules


def inherit_timing(html):
    """<img> và <div class="sk"> chưa có data-start → lấy data-start/duration của phần tử có giờ gần nhất bao ngoài."""
    from html.parser import HTMLParser
    VOID = {"img", "br", "meta", "link", "input", "source", "hr", "base"}
    lines = html.split("\n"); off = [0]
    for ln in lines: off.append(off[-1] + len(ln) + 1)
    edits = []

    class P(HTMLParser):
        def __init__(self): super().__init__(convert_charrefs=False); self.st = []
        def handle_starttag(self, tag, attrs):
            a = dict(attrs); ln, col = self.getpos(); pos = off[ln - 1] + col
            timed = next((s for s in reversed(self.st) if s), None)
            want = (tag == "img" or (tag == "div" and "sk" in (a.get("class") or "").split())) and "data-start" not in a
            if want and timed and a.get("id") != "root":
                end = html.index(">", pos); edits.append((end, f' data-start="{timed[0]}" data-duration="{timed[1]}"'))
            if tag not in VOID:
                cur = (a["data-start"], a["data-duration"]) if "data-start" in a and "data-composition-id" not in a else None
                self.st.append(cur)
        def handle_endtag(self, tag):
            if tag not in VOID and self.st: self.st.pop()
    P().feed(html)
    for end, ins in sorted(edits, reverse=True):
        cut = end - 1 if html[end - 1] == "/" else end
        html = html[:cut] + ins + html[cut:]
    # sticker: khung .sk (bọc ngoài không giờ) lấy giờ của chính video meme bên trong
    return re.sub(r'(<div class="sk"(?![^>]*data-start)[^>]*?)(>\s*<video[^>]*data-start="([\d.]+)" data-duration="([\d.]+)")',
                  r'\1 data-start="\3" data-duration="\4"\2', html)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("build"); ap.add_argument("out")
    ap.add_argument("--lufs", type=float, default=-14.0)
    a = ap.parse_args()
    d = pathlib.Path(a.build).resolve(); out = pathlib.Path(a.out).resolve()
    html = (d / "index.html").read_text(encoding="utf-8"); cues = json.loads((d / "cues.json").read_text(encoding="utf-8"))
    if "pieces" not in cues: raise SystemExit("cues.json chưa có 'pieces' — dựng lại bản này bằng kit mới (produce.py --build)")
    base = d.parent if '<base href="../">' in html else d          # bản phụ (demo/) trỏ asset về thư mục clip
    rules = profile_rules(base)  # kiểm trước khi ghi project hay xử lý tiếng
    html = html.replace('<base href="../">', "")
    out.mkdir(parents=True, exist_ok=True); D = float(cues["duration"])

    # ---- 1. asset hình / font: link vào project, giữ nguyên đường dẫn tương đối
    for rel in sorted(set(re.findall(r'(?:src="|url\(\')(assets/[^"\']+)', html))):
        link(base / rel, out / rel)

    # ---- 2. video: thời gian + cắt + tốc độ lên chính thẻ <video>
    n = [0]
    def vid(m):
        s, dur, inner = m.group(1), m.group(2), m.group(3)
        def fix(v):
            at = dict(re.findall(r'(data-[a-z]+)="([^"]*)"', v.group(0)))
            extra = f' data-start="{s}" data-duration="{dur}" data-media-start="{at.get("data-offset", "0")}"'
            if at.get("data-rate", "1.000") not in ("1", "1.0", "1.000"): extra += f' data-playback-rate="{at["data-rate"]}"'
            tag = re.sub(r'\s*data-(offset|end|rate)="[^"]*"', "", v.group(0))
            loop = " loop" if 'data-loop="1"' in tag else ""
            tag = tag.replace(' data-loop="1"', "")
            n[0] += 1; tr = TRACK["sticker"] if "assets/meme/" in tag else TRACK["screen"]
            return tag[:-1] + f' id="v{n[0]}"{extra} data-track-index="{tr}"{loop}>'
        # khung bọc KHÔNG có thời gian (HyperFrames lấy thời gian từ chính <video>; bọc cũng có giờ → lệch khung)
        return '<div class="clip">' + re.sub(r"<video[^>]*>", fix, inner)
    html = re.sub(r'<div class="clip(?: stk)?" data-start="([\d.]+)" data-duration="([\d.]+)">(\s*(?:<div[^>]*>\s*)?<video[^>]*>)',
                  lambda m: vid(m).replace('<div class="clip">', '<div class="clip stk">', 1) if 'class="clip stk"' in m.group(0) else vid(m), html)

    # ---- 3. id + làn cho cảnh / phụ đề / lớp phủ
    k = {"scene": 0, "cap": 0, "ov": 0}
    def tag_ids(m):
        t = m.group(0)
        if " id=" in t.split(">")[0] and "data-track-index" in t: return t
        if t.startswith("<section"): k["scene"] += 1; idn, tr = f'scene{k["scene"]}', TRACK["scene"]
        elif 'class="cap"' in t: k["cap"] += 1; idn, tr = f'cap{k["cap"]}', TRACK["caption"]
        else: k["ov"] += 1; idn, tr = f'el{k["ov"]}', TRACK["overlay"]
        idattr = "" if re.search(r'\sid="', t) else f' id="{idn}"'
        return t[:-1] + f'{idattr} data-track-index="{tr}">'
    html = re.sub(r'<(?:section|div)\b[^>]*data-start="[^"]*"[^>]*>', lambda m: tag_ids(m) if 'data-composition-id' not in m.group(0) else m.group(0), html)

    # ---- 4. tiếng: hệ số chung để cả bài ≈ -14 LUFS (đo trên bản trộn kit nếu có, không thì trộn tạm để đo)
    mix = d / "final_audio.mp3"
    if not mix.exists():
        subprocess.run([_sys.executable, str(KIT / "tools/mix_audio.py"), str(d / "cues.json"), str(mix)], check=True, cwd=base)
    L = lufs(mix); g = 10 ** ((a.lufs - L) / 20) if L is not None else 1.0
    print(f"  bản trộn kit {L} LUFS → nhân {g:.3f} để ≈ {a.lufs} LUFS")
    au = []
    vol = lambda x: f"{min(3.98, x):.4f}"
    # giọng: mỗi cụm 1 đoạn
    for i, p in enumerate(cues["pieces"]):
        src = pathlib.Path(p["file"]); rel = f"assets/voice/{src.name}"; link(src, out / rel)
        au.append(f'<audio id="vo{i + 1}" class="voice" data-line="{p["line"]}" src="{rel}" data-start="{p["t"]:.3f}" '
                  f'data-duration="{p["b"] - p["a"]:.3f}" data-media-start="{p["a"]:.3f}" data-volume="{vol(cues["voice"].get("volume", 1) * g)}" '
                  f'data-fade-in="0.02" data-fade-out="0.04" data-track-index="{TRACK["voice"]}"></audio>')
    # nhạc nền: lặp, fade, hạ khi có giọng (làn volume; t tính từ đầu đoạn nhạc)
    b = cues.get("bgm")
    if b:
        src = find(b["file"], base); rel = f"assets/audio/bgm{src.suffix}"; link(src, out / rel)
        st = float(b.get("start", 0)); spans = []
        for p in cues["pieces"]:
            s0, s1 = p["t"] - st, p["t"] + p["b"] - p["a"] - st
            if spans and s0 - spans[-1][1] < 0.6: spans[-1][1] = max(spans[-1][1], s1)
            else: spans.append([s0, s1])
        pts = [{"t": 0, "v": 1}]
        for s0, s1 in spans:
            pts += [{"t": round(max(0, s0 - 0.05), 3), "v": 1}, {"t": round(max(0, s0 + 0.03), 3), "v": 0.35},
                    {"t": round(s1 + 0.05, 3), "v": 0.35}, {"t": round(s1 + 0.4, 3), "v": 1}]
        lanes = [{"target": "volume", "points": pts[:512]}]
        fx_attr = ""
        if b.get("carve", False):
            carve_pts = [{"t": 0, "v": 0}]
            for s0, s1 in spans:
                carve_pts += [{"t": round(max(0, s0 - 0.05), 3), "v": 0}, {"t": round(max(0, s0 + 0.03), 3), "v": -4.0},
                              {"t": round(s1 + 0.05, 3), "v": -4.0}, {"t": round(s1 + 0.4, 3), "v": 0}]
            lanes.append({"target": "fx.carve.gain", "points": carve_pts[:512]})
            fx_chain = {
                "version": 1,
                "nodes": [
                    {"type": "peaking", "id": "carve", "label": "Voice carve", "params": {"frequency": 2500, "gain": 0, "q": 0.7}}
                ]
            }
            fx_attr = f' data-fx-chain="{json.dumps(fx_chain).replace(chr(34), "&quot;")}"'
        auto = json.dumps({"version": 1, "lanes": lanes}).replace('"', "&quot;")
        au.append(f'<audio id="bgm" src="{rel}" loop data-start="{st:.3f}" data-duration="{D - st:.3f}" data-media-start="{float(b.get("offset", 0)):.3f}" '
                  f'data-volume="{vol(float(b.get("volume", 0.2)) * g)}" data-fade-in="{b.get("fade_in", 0.8)}" data-fade-out="{b.get("fade_out", 2.5)}"'
                  f'{fx_attr} data-automation="{auto}" data-track-index="{TRACK["bgm"]}"></audio>')
    # hiệu ứng + meme tiếng: chuẩn đỉnh như mix_audio.py (-6 dB) rồi nhân volume
    for i, s in enumerate(cues.get("sfx", [])):
        src = find(s["file"], base); rel = f"assets/sfx/{src.name}"; link(src, out / rel)
        gain = 10 ** ((-6.0 - peak_db(str(src))) / 20) * float(s.get("volume", 0.7)) * g
        dur = float(s["dur"]) if s.get("dur") else float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)], capture_output=True, text=True).stdout or 1)
        is_riser = s.get("kind") == "riser" or "riser" in str(s.get("file", "")).lower()
        fo = ' data-fade-out="0.25"' if (s.get("dur") and not is_riser) else ""
        mo = f' data-media-start="{float(s.get("offset", 0)):.3f}"' if s.get("offset") else ""
        au.append(f'<audio id="sfx{i + 1}" class="sfx" src="{rel}" data-start="{float(s["t"]):.3f}" data-duration="{min(dur, D - float(s["t"])):.3f}" '
                  f'data-volume="{vol(gain)}"{fo}{mo} data-track-index="{TRACK["sfx"]}"></audio>')
    # làn: đoạn tiếng chồng nhau (đệm đầu/cuối cụm lời, nhiều hiệu ứng cùng lúc) phải nằm khác làn
    groups = {"voice": [], "sfx": [], "bgm": []}
    for x in au:
        groups["voice" if 'class="voice"' in x else "sfx" if 'class="sfx"' in x else "bgm"].append(x)
    lane0, packed = TRACK["voice"], []
    for grp in ("voice", "sfx", "bgm"):
        ends = []
        for x in groups[grp]:
            s0 = float(re.search(r'data-start="([\d.]+)"', x).group(1)); s1 = s0 + float(re.search(r'data-duration="([\d.]+)"', x).group(1))
            i = next((i for i, e in enumerate(ends) if e <= s0 + 1e-3), None)
            if i is None: ends.append(s1); i = len(ends) - 1
            else: ends[i] = s1
            packed.append(re.sub(r'data-track-index="\d+"', f'data-track-index="{lane0 + i}"', x))
        lane0 += max(1, len(ends))
    au = packed
    html = html.replace('\n</div>\n<script>', "\n" + "\n".join(au) + '\n</div>\n<script>', 1)

    # ---- 4a. ảnh / sticker nằm trong cảnh mà không có giờ riêng → Studio vẽ thành dải chạy SUỐT video (dù thực tế chỉ
    # hiện trong cảnh của nó) → gán đúng giờ của cảnh chứa nó cho timeline khớp với lúc xem
    html = inherit_timing(html)

    # ---- 4b. phụ đề: gắn câu lời (data-line) theo thời gian + class clip → doi_loi.py thay đúng phụ đề của câu
    P = cues["pieces"]
    def capline(m):
        s0 = float(m.group(1))
        hit = [p for p in P if p["t"] - 0.4 <= s0 <= p["t"] + p["b"] - p["a"]]
        ln = hit[0]["line"] if hit else ""
        return m.group(0).replace('<div class="cap"', f'<div class="cap clip" data-line="{ln}"', 1)
    html = re.sub(r'<div class="cap" data-start="([\d.]+)"[^>]*>', capline, html)

    # ---- 5. runtime: HyperFrames tự tạo window.__timelines
    html = html.replace('window.__timelines["main"] = tl;', 'window.__timelines = window.__timelines || {}; window.__timelines["main"] = tl;')
    (out / "index.html").write_text(html, encoding="utf-8")
    # kịch bản giọng (giọng, hồ sơ, lời đạo diễn từng câu) — doi_loi.py đọc lại câu bằng đúng giọng này
    if (base / "voice.json").exists(): shutil.copy2(base / "voice.json", out / "voice.json")
    meta = {"from": str(d), "duration": D, "lufs_target": a.lufs, "voice_gain": round(cues["voice"].get("volume", 1) * g, 4),
            "lines": sorted({p["line"] for p in cues["pieces"]}, key=lambda x: (len(x), x)), "rules": rules}
    (out / "studio.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"xong: {out / 'index.html'} · {D}s · {len(cues['pieces'])} đoạn giọng · {len(cues.get('sfx', []))} hiệu ứng · nhạc {'có' if b else 'không'}")


if __name__ == "__main__":
    main()
