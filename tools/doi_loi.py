"""Đổi lời 1 câu trong project HyperFrames Studio (tạo bởi to_studio.py) — KHÔNG cần agent:
đọc lại câu bằng đúng giọng/hồ sơ trong voice.json (Gemini TTS) → thay các đoạn giọng của câu đó → thay phụ đề.

  python KIT/tools/doi_loi.py <project> <câu> "<lời mới>" [--caption "<phụ đề, mặc định = lời>"] [--direction "..."]
  python KIT/tools/doi_loi.py <project> --list              # xem các câu + lời hiện tại

vd: python KIT/tools/doi_loi.py D:/Projects/video-studio/stradevn/02-ho-tieu-full V6 "Hệ thống truy xuất dữ liệu xuất nhập khẩu toàn cầu..."

- Lời đọc: số viết bằng CHỮ ("mười hai") cho giọng đọc đúng; phụ đề (--caption) có thể viết số ("12").
- Câu mới dài hơn câu cũ → báo số giây lấn sang đoạn sau: mở Studio kéo các đoạn sau ra, hoặc rút gọn lời.
- Bản cũ của index.html được lưu ở .hf-versions/ trước khi ghi (hoàn tác: chép lại)."""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import argparse, json, pathlib, re, shutil, subprocess, tempfile, time

TOOLS = pathlib.Path(__file__).resolve().parent


def dur(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]).decode())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("line", nargs="?"); ap.add_argument("text", nargs="?")
    ap.add_argument("--caption"); ap.add_argument("--direction"); ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    pj = pathlib.Path(a.project).resolve(); idx = pj / "index.html"; html = idx.read_text(encoding="utf-8")
    V = json.loads((pj / "voice.json").read_text(encoding="utf-8")); meta = json.loads((pj / "studio.json").read_text(encoding="utf-8"))
    lines = {l["id"]: l for l in V["lines"]}
    if a.list or not a.line:
        for k, l in lines.items(): print(f"{k:5} {l.get('text', '')}")
        return
    if a.line not in lines: raise SystemExit(f"không có câu {a.line} — xem --list")
    if not a.text: raise SystemExit("thiếu lời mới")

    # 1. đọc lại câu bằng đúng giọng (tts_script.py với kịch bản 1 câu)
    ln = dict(lines[a.line], text=a.text, **({"direction": a.direction} if a.direction else {}))
    ln.pop("caption", None)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="doiloi_")); vj = tmp / "voice.json"
    vj.write_text(json.dumps({**{k: v for k, v in V.items() if k != "lines"}, "lines": [ln]}, ensure_ascii=False), encoding="utf-8")
    subprocess.run([_sys.executable, "-X", "utf8", str(TOOLS / "tts_script.py"), str(vj), str(tmp / "out")], check=True)
    n = 1
    while (pj / f"assets/voice/{a.line}-r{n}.mp3").exists(): n += 1
    rel = f"assets/voice/{a.line}-r{n}.mp3"; shutil.copy2(tmp / "out" / f"{a.line}.mp3", pj / rel)
    nd = dur(pj / rel)

    # 2. thay các đoạn giọng của câu
    olds = re.findall(rf'<audio [^>]*data-line="{re.escape(a.line)}"[^>]*></audio>\n?', html)
    if not olds: raise SystemExit(f"index.html không có đoạn giọng nào của {a.line} (đã bị xoá trong Studio?)")
    span = lambda t: (float(re.search(r'data-start="([\d.]+)"', t).group(1)),
                      float(re.search(r'data-start="([\d.]+)"', t).group(1)) + float(re.search(r'data-duration="([\d.]+)"', t).group(1)))
    t0 = min(span(t)[0] for t in olds); t1 = max(span(t)[1] for t in olds)
    track = re.search(r'data-track-index="(\d+)"', olds[0]).group(1)
    new = (f'<audio id="vo-{a.line}-r{n}" class="voice" data-line="{a.line}" src="{rel}" data-start="{t0:.3f}" data-duration="{nd:.3f}" '
           f'data-volume="{meta.get("voice_gain", 1.0)}" data-fade-in="0.02" data-fade-out="0.04" data-track-index="{track}"></audio>\n')
    html = html.replace(olds[0], new, 1)
    for t in olds[1:]: html = html.replace(t, "", 1)

    # 3. phụ đề: bỏ phụ đề cũ của câu, chia lời mới thành cụm theo dấu câu, rải theo độ dài chữ
    caps = re.findall(rf'<div class="cap clip" data-line="{re.escape(a.line)}"[^>]*>.*?</span></div>\n?', html, re.S)
    first = caps[0] if caps else None
    cap_text = re.sub(r"\[[^\]]*\]\s*", "", a.caption or a.text).strip()
    parts = [p.strip() for p in re.findall(r"[^,.:;!?…]+[,.:;!?…]*", cap_text) if p.strip()]
    merged = []
    for p in parts:   # gộp cụm quá ngắn
        if merged and (len(merged[-1].split()) < 3 or len(p.split()) < 2) and len(merged[-1]) + len(p) < 52: merged[-1] += " " + p
        else: merged.append(p)
    total = sum(len(p) for p in merged) or 1; out = []
    starts = [t0 + nd * sum(len(q) for q in merged[:i]) / total for i in range(len(merged))]
    for i, p in enumerate(merged):
        s0 = max(0, starts[i] - 0.05)
        e = starts[i + 1] - 0.07 if i + 1 < len(merged) else t0 + nd + 0.3   # dòng sau hiện thì dòng trước tắt (không đè)
        body = re.sub(r"(\d[\d.,]*)", r"<b>\1</b>", p)
        out.append(f'<div class="cap clip" data-line="{a.line}" data-start="{s0:.3f}" data-duration="{e - s0:.3f}" '
                   f'id="cap-{a.line}-r{n}-{i + 1}" data-track-index="4"><span>{body}</span></div>\n')
    if first: html = html.replace(first, "".join(out), 1)
    for c in caps[1:]: html = html.replace(c, "", 1)
    if not first:   # không còn phụ đề cũ → chèn trước khối tiếng
        html = html.replace('<audio ', "".join(out) + '<audio ', 1)

    # 4. lưu (giữ bản cũ)
    bk = pj / ".hf-versions"; bk.mkdir(exist_ok=True); shutil.copy2(idx, bk / f"index.{time.strftime('%Y%m%d-%H%M%S')}.before-{a.line}.html")
    idx.write_text(html, encoding="utf-8")
    delta = nd - (t1 - t0)
    print(f"✅ {a.line}: {t1 - t0:.2f}s → {nd:.2f}s ({'+' if delta >= 0 else ''}{delta:.2f}s) · {len(merged)} dòng phụ đề · {rel}")
    if delta > 0.3:
        print(f"⚠ câu mới dài hơn {delta:.1f}s — lấn sang đoạn sau ở {t1:.1f}s. Mở Studio kéo các đoạn sau ra, hoặc rút gọn lời.")


if __name__ == "__main__":
    main()
