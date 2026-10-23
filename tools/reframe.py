"""Cắt clip ngang thành dọc mà chủ thể luôn ở GIỮA khung + cắt đúng ranh giới cảnh.

  python tools/reframe.py shots SRC [--sheet out.jpg]
      → danh sách cảnh (giây bắt đầu–kết thúc) + ảnh lưới khung đầu mỗi cảnh
  python tools/reframe.py cut SRC OUT --ss 12.4 --to 19 [--mode auto|track|fit] [--snap] [--class 0]
      → 1080x1920; track = khung 9:16 bám chủ thể; fit = giữ nguyên khung ngang trên nền mờ;
        auto = từng cảnh tự chọn (chủ thể quá rộng / không thấy chủ thể → fit)
        --snap: kéo ss/to về ranh giới cảnh gần nhất (≤0.6 s) để không cắt giữa động tác
  python tools/reframe.py batch SRC cuts.json OUTDIR
      → cuts.json: [{"name": "b_door", "ss": 5, "to": 12, "mode": "auto", "focus": [0.35, 0.8]?}, ...]
  Khung bám hành động: chủ thể + chỗ nó chạm vào xe (đá cửa, nhấc xe) đều nằm trong khung.

Chủ thể = người (COCO class 0; robot hình người cũng nhận là người) bằng YOLOv10n ONNX,
tự tải về ~/.cache/stradevn/ lần đầu (9 MB, chạy CPU).
"""
import argparse, json, os, subprocess, sys, urllib.request
import numpy as np
from PIL import Image, ImageFilter

MODEL_URL = "https://huggingface.co/onnx-community/yolov10n/resolve/main/onnx/model.onnx"
MODEL = os.path.expanduser("~/.cache/stradevn/yolov10n.onnx")
OW, OH = 1080, 1920
AFPS = 8          # tần số phân tích
AW = 640          # bề ngang khung phân tích


def probe(src):
    o = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate:format=duration", "-of", "json", src],
                                  capture_output=True, text=True, check=True).stdout)
    s = o["streams"][0]; n, d = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(n) / float(d), float(o["format"]["duration"])


def frames(src, ss, to, w, h, fps=None):
    vf = f"scale={w}:{h}" + (f",fps={fps}" if fps else "")
    p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(ss), "-to", str(to), "-i", src, "-vf", vf,
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n = w * h * 3
    try:
        while (b := p.stdout.read(n)) and len(b) == n:
            yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    finally:
        p.kill(); p.wait()


_sess = None
def detect(img, cls):
    """img: HxWx3 → [(x1,y1,x2,y2,score,lớp)] theo toạ độ img, chỉ các lớp trong cls."""
    global _sess
    if _sess is None:
        import onnxruntime as ort
        if not os.path.exists(MODEL):
            os.makedirs(os.path.dirname(MODEL), exist_ok=True)
            print("  tải YOLOv10n…", file=sys.stderr); urllib.request.urlretrieve(MODEL_URL, MODEL)
        _sess = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    h, w = img.shape[:2]; sc = 640 / max(w, h); nw, nh = int(w * sc), int(h * sc)
    px, py = (640 - nw) // 2, (640 - nh) // 2
    im = np.full((640, 640, 3), 114, np.uint8); im[py:py + nh, px:px + nw] = np.asarray(Image.fromarray(img).resize((nw, nh)))
    out = _sess.run(None, {"images": im.transpose(2, 0, 1)[None].astype(np.float32) / 255})[0][0]
    return [((x1 - px) / sc, (y1 - py) / sc, (x2 - px) / sc, (y2 - py) / sc, s, int(c)) for x1, y1, x2, y2, s, c in out
            if s >= .3 and int(c) in cls]


def sig(f):
    """Chữ ký khung để dò cắt cảnh: (histogram màu 3x32 chuẩn hoá, ảnh xám 64x36)."""
    h = np.concatenate([np.histogram(f[..., c], 32, (0, 256))[0] for c in range(3)]).astype(float)
    return h / h.sum() * 3, np.asarray(Image.fromarray(f).convert("L").resize((64, 36)), np.int16)


def shot_bounds(sigs):
    """sigs: chữ ký mỗi khung (AFPS) → chỉ số khung bắt đầu cảnh mới.
    Cắt = histogram đổi mạnh VÀ điểm ảnh đổi; nháy sáng/tia lửa trong 0.7 s gộp thành 1 cắt."""
    cand = []
    for i in range(1, len(sigs)):
        dh = np.abs(sigs[i][0] - sigs[i - 1][0]).sum() / 2; dp = np.abs(sigs[i][1] - sigs[i - 1][1]).mean()
        if dh > .35 and dp > 20: cand.append((i, dh))
    cuts, grp = [0], []
    for c in cand + [(10 ** 9, 0)]:
        if grp and c[0] - grp[0][0] > AFPS * .7:
            cuts.append(max(grp, key=lambda g: g[1])[0]); grp = []
        grp.append(c)
    return sorted({c for c in cuts if c < len(sigs)})


VEHICLES = (2, 3, 5, 7)   # ô tô, xe máy, buýt, tải: vật chủ thể hay đá/nhấc/va vào


def analyse(src, ss, to, cls=0, props=VEHICLES):
    """→ W, H, ranh giới cảnh, [(chủ thể, đồ vật)] mỗi khung phân tích."""
    W, H, _, _ = probe(src); ah = int(AW * H / W) // 2 * 2
    small, dets = [], []
    for f in frames(src, ss, to, AW, ah, AFPS):
        small.append(sig(f))
        ds = [(x1 * W / AW, y1 * H / ah, x2 * W / AW, y2 * H / ah, s, c) for x1, y1, x2, y2, s, c in detect(f, {cls, *props})]
        dets.append(([d[:5] for d in ds if d[5] == cls], [d[:5] for d in ds if d[5] != cls and d[4] > .35]))
    return W, H, shot_bounds(small), dets


def contact(b, props, margin):
    """Chủ thể đang chạm vật (đá cửa, nhấc xe) → nới vùng (x1, x2) sang phía vật thêm `margin` để thấy chỗ va."""
    x1, x2 = b[0], b[2]; pad = (b[2] - b[0]) * .08
    for p in props:
        if p[0] > b[2] + pad or p[2] < b[0] - pad or p[1] > b[3] or p[3] < b[1]: continue   # không chạm
        if (p[0] + p[2]) / 2 > (b[0] + b[2]) / 2: x2 = max(x2, min(p[2], max(b[2], p[0]) + margin))
        else: x1 = min(x1, max(p[0], min(b[0], p[2]) - margin))
    return x1, x2


def gauss(x, sigma):
    if sigma <= 0 or len(x) < 3: return x
    r = int(3 * sigma); k = np.exp(-np.arange(-r, r + 1) ** 2 / (2 * sigma ** 2)); k /= k.sum()
    return np.convolve(np.pad(x, r, mode="edge"), k, mode="valid")


def plan_shot(dets, W, H, cw, mode):
    """→ (chế độ, mảng tâm x theo khung phân tích, bề ngang vùng cắt).
    Khung bám HÀNH ĐỘNG: chủ thể + chỗ nó chạm vào vật (cửa xe bị đá, đầu xe bị nhấc).
    Rộng hơn khung 9:16 (đá ngang, cảnh toàn) → nới vùng cắt vừa đủ, phần thừa là nền mờ."""
    n = len(dets); cx = np.full(n, np.nan); widths = []; prev = None
    for i, (ds, props) in enumerate(dets):
        if not ds: continue
        def cost(b):
            c = (b[0] + b[2]) / 2; a = (b[2] - b[0]) * (b[3] - b[1]) * b[4]
            return a / (1 + (abs(c - prev) / W * 4 if prev is not None else 0))
        b = max(ds, key=cost)
        ux1, ux2 = min(d[0] for d in ds if d[4] > .45) if any(d[4] > .45 for d in ds) else b[0], \
                   max(d[2] for d in ds if d[4] > .45) if any(d[4] > .45 for d in ds) else b[2]
        x1, x2 = (min(ux1, b[0]), max(ux2, b[2])) if max(ux2, b[2]) - min(ux1, b[0]) <= cw * 1.5 else (b[0], b[2])
        a1, a2 = contact(b, props, cw * .45); x1, x2 = min(x1, a1), max(x2, a2)
        cx[i] = prev = (x1 + x2) / 2; widths.append(x2 - x1)
    seen = ~np.isnan(cx)
    if mode == "fit" or seen.sum() < max(1, n * .3): return "fit", None, W
    crop = cw if mode == "track" else float(np.clip(np.percentile(widths, 85) * 1.15, cw, W))
    if crop > W * .8: return "fit", None, W
    idx = np.arange(n); cx = np.interp(idx, idx[seen], cx[seen])
    cx = gauss(cx, AFPS * .45)
    if cx.max() - cx.min() < crop * .18: cx[:] = np.median(cx)        # gần đứng yên → khoá máy
    return "track", np.clip(cx, crop / 2, W - crop / 2), crop


def render(src, out, ss, to, mode="auto", cls=0, y=None, focus=None):
    W, H, fps, _ = probe(src)
    if W / H <= OW / OH + .01:   # nguồn đã dọc → phủ khung
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(ss), "-to", str(to), "-i", src, "-vf",
                        f"scale={OW}:{OH}:force_original_aspect_ratio=increase:flags=lanczos,crop={OW}:{OH},fps=30",
                        "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", out], check=True)
        return []
    cw = H * OW / OH
    W, H, cuts, dets = analyse(src, ss, to, cls)
    shots = []; bounds = cuts + [len(dets)]
    for a, b in zip(bounds, bounds[1:]):
        if focus:   # chỉnh tay: vùng [x1, x2] theo tỉ lệ bề ngang nguồn
            crop = max(cw, (focus[1] - focus[0]) * W)
            shots.append((a, b, "track", np.full(b - a, np.clip((focus[0] + focus[1]) / 2 * W, crop / 2, W - crop / 2)), crop))
        else:
            shots.append((a, b, *plan_shot(dets[a:b], W, H, cw, mode)))
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
                            "-r", str(fps), "-i", "-", "-ss", str(ss), "-to", str(to), "-i", src, "-map", "0:v", "-map", "1:a?",
                            "-vf", "unsharp=5:5:0.45:5:5:0,fps=30", "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", out], stdin=subprocess.PIPE)
    for k, f in enumerate(frames(src, ss, to, W, H)):
        ai = min(int(k / fps * AFPS), len(dets) - 1) if dets else 0
        a, b, m, cx, crop = next((s for s in shots if s[0] <= ai < s[1]), shots[-1])
        img = Image.fromarray(f)
        if m == "track":
            c = float(cx[min(ai - a, len(cx) - 1)]); x = int(round(c - crop / 2))
            img = img.crop((x, 0, x + int(round(crop)), H))
        if img.width <= cw + 1:
            fr = img.resize((OW, OH), Image.LANCZOS)
        else:   # rộng hơn 9:16 → khung chính giữa trên nền mờ của chính nó
            iw, ih = img.size; ph = round(OW * ih / iw)
            bg = img.resize((round(OH * iw / ih), OH), Image.BILINEAR); bx = (bg.width - OW) // 2
            fr = bg.crop((bx, 0, bx + OW, OH)).resize((OW // 8, OH // 8)).filter(ImageFilter.GaussianBlur(4)).resize((OW, OH))
            fr = Image.eval(fr, lambda v: int(v * .55))
            fr.paste(img.resize((OW, ph), Image.LANCZOS), (0, (OH - ph) // 2 if y is None else int(y - ph / 2)))
        enc.stdin.write(fr.tobytes())
    enc.stdin.close(); enc.wait()
    return [{"start": round(ss + a / AFPS, 2), "end": round(ss + b / AFPS, 2),
             "mode": m if m == "fit" or crop <= cw + 1 else f"track {crop / W:.0%}"} for a, b, m, _, crop in shots]


def snap(t, cuts_t, tol=.6):
    c = min(cuts_t, key=lambda v: abs(v - t), default=t)
    return c if abs(c - t) <= tol else t


def list_shots(src):
    W, H, fps, dur = probe(src); ah = int(AW * H / W) // 2 * 2
    small = [sig(f) for f in frames(src, 0, dur, AW, ah, AFPS)]
    b = shot_bounds(small) + [len(small)]
    return [(round(x / AFPS, 2), round(y / AFPS, 2)) for x, y in zip(b, b[1:])]


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("shots"); s.add_argument("src"); s.add_argument("--sheet")
    s = sp.add_parser("cut"); s.add_argument("src"); s.add_argument("out"); s.add_argument("--ss", type=float, default=0)
    s.add_argument("--to", type=float); s.add_argument("--mode", default="auto", choices=["auto", "track", "fit"])
    s.add_argument("--snap", action="store_true"); s.add_argument("--class", dest="cls", type=int, default=0)
    s.add_argument("--y", type=float, help="fit: tâm khung ngang theo trục dọc (mặc định giữa)")
    s.add_argument("--focus", help="chỉnh tay vùng cần giữ, tỉ lệ bề ngang nguồn, vd 0.35,0.8")
    s = sp.add_parser("batch"); s.add_argument("src"); s.add_argument("spec"); s.add_argument("outdir")
    a = ap.parse_args()
    if a.cmd == "shots":
        sh = list_shots(a.src)
        for i, (x, y) in enumerate(sh): print(f"{i:3} {x:7.2f} – {y:7.2f}  ({y - x:.1f}s)")
        if a.sheet:
            W, H, _, _ = probe(a.src); tiles = []
            for x, y in sh:
                t = min(x + .3, (x + y) / 2)
                f = next(frames(a.src, t, t + .5, 320, int(320 * H / W) // 2 * 2), None)
                if f is not None: tiles.append(Image.fromarray(f))
            cols = 6; th = tiles[0].height; g = Image.new("RGB", (320 * cols, th * ((len(tiles) + cols - 1) // cols)))
            for i, t in enumerate(tiles): g.paste(t, (320 * (i % cols), th * (i // cols)))
            g.save(a.sheet); print("→", a.sheet)
        return
    if a.cmd == "cut":
        to = a.to if a.to is not None else probe(a.src)[3]; ss = a.ss
        if a.snap:
            ct = [x for x, _ in list_shots(a.src)] + [probe(a.src)[3]]; ss, to = snap(ss, ct), snap(to, ct)
        for s in render(a.src, a.out, ss, to, a.mode, a.cls, a.y,
                                                                [float(v) for v in a.focus.split(",")] if a.focus else None): print(f"  {s['start']:6.2f}–{s['end']:6.2f} {s['mode']}")
        print("→", a.out); return
    os.makedirs(a.outdir, exist_ok=True)
    for c in json.load(open(a.spec, encoding="utf-8")):
        out = os.path.join(a.outdir, c["name"] + ".mp4")
        shots = render(a.src, out, c["ss"], c["to"], c.get("mode", "auto"), c.get("class", 0), c.get("y"), c.get("focus"))
        print(c["name"], " ".join(f"{s['start']}-{s['end']}:{s['mode']}" for s in shots))


if __name__ == "__main__":
    main()
