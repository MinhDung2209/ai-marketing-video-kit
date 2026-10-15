"""Video DÀI (10–60 phút, 16:9, kiểu phim tài liệu du lịch): giọng đọc + footage stock Pexels cắt ~3s/cảnh + FFmpeg.

Khác render.py (Chrome chụp từng khung — hợp video ngắn có hoạt ảnh): ở đây mọi thứ ghép bằng FFmpeg nên
video 15 phút / 300 cảnh render trong vài phút.

Dự án = 1 thư mục có script.json + .env (PEXELS_API_KEY; PIXABAY_API_KEY tuỳ chọn). Wikimedia Commons không cần key.
  python <kit>/tools/longform.py tts <dự án>        # đọc từng câu (song song) → audio/*.wav, timing.json, narration.mp3
  python <kit>/tools/longform.py footage <dự án>    # chọn + tải + cắt footage cho từng cảnh → footage/plan.json, ảnh ghép
  python <kit>/tools/longform.py render <dự án>     # ghép chương (chuyển mờ), tiêu đề chương, trộn nhạc → video.mp4 + .srt
Chọn lại footage: ghi id clip sai vào footage/blacklist.txt (mỗi dòng 1 id) rồi chạy lại footage (chỉ tải phần thiếu).

Footage TẢI TAY (Envato Elements, Storyblocks — không có API tải cho gói cá nhân; bot tải hàng loạt vi phạm điều khoản):
  python <kit>/tools/longform.py collect <dự án>    # mở trang: mỗi chương 1 thẻ (lời đọc, số clip cần, link tìm Envato/Storyblocks)
  → bấm link, bấm Download như bình thường; tool canh thư mục Downloads, file tải xong tự chuyển vào footage/local/<chương>/
  footage tự dùng footage/local/<chương>/ nếu có (không gọi API), mỗi clip cắt tối đa 4 cảnh ở các đoạn khác nhau.
4K: "res": "4k" trong script.json (footage + render cùng đọc) · --nvenc: mã hoá bằng card NVIDIA (nhanh hơn nhiều ở 4K).

Lọc đúng địa danh: Pexels không trả mô tả/tag, chỉ có đường dẫn dạng /video/<mô-tả-tự-sinh>-<id>/ → clip chỉ được
nhận khi đường dẫn chứa 1 từ trong "must" của chương (vd "ha-long"); thiếu thì mới lấy "fallback" (vd "vietnam").
Pixabay: tag do người đăng tự gõ, hay gắn rác (1 clip thác nước gắn cả hanoi, saigon, sapa) → clip gắn ≥3 địa danh bị loại.
Wikimedia: tên/mô tả/danh mục có dấu → bỏ dấu rồi so ("Hội An" → hoi-an); chỉ nhận CC0 / CC BY / CC BY-SA / public domain.
Đo 15/10/2026: tìm "hue vietnam" 160 clip chỉ 1 clip ghi "hue"; "ha long bay" 80/160 → viết chương theo footage có thật.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, base64, hashlib, json, os, pathlib, random, re, subprocess, sys, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
import requests

TOOLS = pathlib.Path(__file__).resolve().parent
W, H, FPS = 1920, 1080, 30
XF = 0.5            # giây chuyển mờ giữa 2 cảnh
SHOT = 3.2          # độ dài cảnh mong muốn (khách yêu cầu ~3s/footage)
GAP, LEAD, TITLE_LEAD, TAIL = 0.45, 0.8, 3.0, 1.0   # lặng giữa câu · trước câu đầu chương · khi có tiêu đề · cuối chương

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mxf", ".webm", ".mkv"}
PER_CLIP = 4        # clip tải tay (Envato dài 10–30s) → tối đa 4 cảnh lấy ở 4 đoạn khác nhau
SEARCH = {"Envato": "https://elements.envato.com/stock-video/{slug}", "Storyblocks": "https://www.storyblocks.com/video/search/{slug}"}

def sh(cmd, **kw): return subprocess.run(cmd, check=True, **kw)
def dur(f): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]).decode())
def load(p): return json.load(open(p, encoding="utf-8"))
def save(o, p): json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def set_res(sc):    # "res": "4k" trong script.json → mọi bước (cắt cảnh, ghép, xuất) làm ở 3840×2160
    global W, H
    W, H = (3840, 2160) if str(sc.get("res", "")).lower() in ("4k", "2160", "2160p") else (1920, 1080)
def seg_dir(proj): return proj / "footage" / ("seg" if H == 1080 else f"seg_{H}p")   # đổi độ phân giải không dùng nhầm cảnh cũ
_NV = {}
def nvenc_ok():   # thử mã hoá 1 khung — đo 15/10/2026: driver 591.86 + FFmpeg mới báo "Required: 13.1 Found: 13.0" → cần driver ≥ 610
    if "ok" not in _NV:
        r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:s=1280x720:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"], capture_output=True, text=True)
        _NV["ok"] = r.returncode == 0
        if not _NV["ok"]: print("  ⚠ NVENC không chạy (" + (r.stderr.strip().splitlines() or ["?"])[0][:120] + ") → mã hoá bằng CPU. Cập nhật driver NVIDIA rồi thử lại", flush=True)
    return _NV["ok"]
def venc(a, crf, preset="veryfast", final=False):
    if getattr(a, "nvenc", False) and nvenc_ok():   # GTX 1650: h264_nvenc cho file trung gian, hevc_nvenc cho file xuất (YouTube nhận HEVC)
        return ["-c:v", "hevc_nvenc" if final else "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", str(crf), "-b:v", "0"] + (["-tag:v", "hvc1"] if final else [])
    return ["-c:v", "libx264", "-preset", preset, "-crf", str(crf)]
def probe(f):       # → (giây, rộng, cao) hoặc None nếu không đọc được
    try:
        o = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "json", str(f)], stderr=subprocess.DEVNULL))
        return float(o["format"]["duration"]), o["streams"][0]["width"], o["streams"][0]["height"]
    except Exception: return None
def fold(t):   # "Hội An" → "-hoi-an-" để so với must / kw
    t = unicodedata.normalize("NFKD", t.replace("Đ", "D").replace("đ", "d"))
    return "-" + re.sub(r"[^a-z0-9]+", "-", "".join(ch for ch in t if not unicodedata.combining(ch)).lower()) + "-"

def env_key(proj, name):
    if os.environ.get(name): return os.environ[name]
    for f in (proj / ".env", pathlib.Path(".env")):
        if f.exists():
            for ln in f.read_text(encoding="utf-8").splitlines():
                k, _, v = ln.partition("=")
                if k.strip() == name: return v.strip()
    raise SystemExit(f"Thiếu {name} (biến môi trường hoặc .env của dự án)")

# ------------------------------------------------------------------ 1. giọng đọc
def tts(proj, a):
    sys.path.insert(0, str(TOOLS)); from gcp import token_and_project
    sc = load(proj / "script.json"); v = sc["voice"]; out = proj / "audio"; out.mkdir(exist_ok=True)
    tok, gp = token_and_project(); hdr = {"Authorization": f"Bearer {tok}", "x-goog-user-project": gp}
    lines = [(f"{ci:02d}-{li:02d}", ln) for ci, c in enumerate(sc["chapters"]) for li, ln in enumerate(c["lines"])]
    only = set(a.only.split(",")) if a.only else None

    def one(item):
        lid, ln = item; f = out / f"{lid}.wav"   # WAV: nối concat khớp từng mẫu (mp3 lệch ~26ms/file)
        if f.exists() and (only is None or lid not in only) and not a.force: return lid, "giữ"
        for attempt in range(5):   # bộ lọc an toàn đôi khi chặn nhầm → thử lại, cuối cùng bỏ lời đạo diễn
            prof = v["profile"] if attempt < 2 else v.get("profile_fallback", v["profile"])
            inp = {"text": ln["text"]} if attempt == 4 else {"prompt": prof + " " + ln.get("direction", ""), "text": ln["text"]}
            r = requests.post("https://texttospeech.googleapis.com/v1/text:synthesize", headers=hdr, timeout=120, json={
                "input": inp, "voice": {"languageCode": v.get("language", "vi-VN"), "name": v.get("voice", "Kore"), "modelName": v["model"]},
                "audioConfig": {"audioEncoding": "MP3", "sampleRateHertz": 44100}})
            if r.ok: break
            if r.status_code in (429, 500, 503): time.sleep(5 * (attempt + 1)); continue
            if "usage guidelines" not in r.text: raise SystemExit(f"{lid}: {r.status_code} {r.text[:300]}")
        if not r.ok: raise SystemExit(f"{lid}: {r.status_code} {r.text[:300]}")
        raw = out / f"{lid}.raw.mp3"; raw.write_bytes(base64.b64decode(r.json()["audioContent"]))
        trim = "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse"
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af", f"{trim},atempo={a.tempo},loudnorm=I=-18:TP=-2:LRA=7,apad=pad_dur=0.1", "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(f)])
        raw.unlink(); return lid, "đọc" + (" (không kèm đạo diễn)" if attempt == 4 else "")

    with ThreadPoolExecutor(a.jobs) as ex:
        for lid, st in ex.map(one, lines): print(lid, st, flush=True)
    # dựng dòng thời gian: chương có tiêu đề thì để nhạc + chữ chạy TITLE_LEAD giây trước khi đọc
    t, tl, chaps = 0.0, [], []
    for ci, c in enumerate(sc["chapters"]):
        cs = round(t, 2); t += TITLE_LEAD if c.get("title") else LEAD
        for li, ln in enumerate(c["lines"]):
            lid = f"{ci:02d}-{li:02d}"; d = round(dur(out / f"{lid}.wav"), 2)
            tl.append({"id": lid, "file": f"{lid}.wav", "chapter": ci, "start": round(t, 2), "dur": d, "text": ln["text"]}); t += d + GAP
        t += TAIL - GAP; chaps.append({"id": c["id"], "title": c.get("title", ""), "subtitle": c.get("subtitle", ""), "start": cs})
    total = round(t + 2.0, 2)
    for i, c in enumerate(chaps): c["end"] = chaps[i + 1]["start"] if i + 1 < len(chaps) else total
    save({"total": total, "chapters": chaps, "lines": tl}, out / "timing.json")
    # ghép narration bằng concat (nhiều đầu vào adelay/amix với 100+ câu rất chậm)
    parts, cur = [], 0.0
    lst = out / "_concat.txt"
    with open(lst, "w", encoding="utf-8") as fh:
        for m in tl:
            gap = round(m["start"] - cur, 3)
            if gap > 0:
                sil = out / f"_sil_{int(gap * 1000)}.wav"
                if not sil.exists(): sh(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(gap), "-c:a", "pcm_s16le", str(sil)])
                fh.write(f"file '{sil.name}'\n")
            fh.write(f"file '{m['file']}'\n"); cur = m["start"] + dur(out / m["file"])
    sh(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-af", f"aresample=44100,apad=whole_dur={total}",
        "-ac", "2", "-t", str(total), "-b:a", "192k", str(out / "narration.mp3")])
    for f in out.glob("_sil_*.wav"): f.unlink()
    lst.unlink()
    print(f"xong: {len(tl)} câu · {len(chaps)} chương · {total / 60:.1f} phút → audio/narration.mp3")

# ------------------------------------------------------------------ 2. footage
def footage(proj, a):
    sc = load(proj / "script.json"); tm = load(proj / "audio/timing.json"); set_res(sc)
    fd = proj / "footage"; (fd / "search").mkdir(parents=True, exist_ok=True); (fd / "src").mkdir(exist_ok=True); seg_dir(proj).mkdir(exist_ok=True)
    black = set((fd / "blacklist.txt").read_text(encoding="utf-8").split()) if (fd / "blacklist.txt").exists() else set()

    def local(c):   # footage tải tay ở footage/local/<chương>/ — người đã chọn đúng cảnh → không lọc địa danh
        d = fd / "local" / c["id"]; out = []   # footage/local/<chương>/<số câu>/ = clip riêng của câu đó (vd 03 = câu thứ 4)
        files = sorted(f for f in d.rglob("*") if f.suffix.lower() in VIDEO_EXT) if d.exists() else []
        for n, f in enumerate(files):
            line = int(f.parent.name) if f.parent != d and f.parent.name.isdigit() else None
            info = probe(f)
            if not info or info[0] < 2: print(f"  ⚠ bỏ {f.name}: không đọc được / quá ngắn"); continue
            cid = "lc" + hashlib.md5(f.name.encode()).hexdigest()[:8]
            if cid in black: continue
            slots = max(1, min(PER_CLIP, int(info[0] // (SHOT + 1.5))))
            for k in range(slots):   # rank theo đợt: dùng hết đoạn 1 của mọi clip rồi mới tới đoạn 2 → 2 cảnh liền nhau ít khi cùng clip
                if f"{cid}-{k}" in black: continue
                out.append({"id": f"{cid}-{k}", "text": fold(f.stem), "dur": info[0], "width": info[1], "tier": 2, "rank": k * 4000 + n,
                            "file": f.relative_to(proj).as_posix(), "url": f.name, "author": "tải tay", "local": [k, slots], "line": line})
        return out

    source = getattr(a, "source", "auto")
    use_local = {c["id"]: source != "stock" and bool(local(c)) for c in sc["chapters"]}
    if source == "local" and not all(use_local.values()):
        raise SystemExit("Chưa có footage tải tay cho: " + ", ".join(k for k, v in use_local.items() if not v) + " — chạy collect trước")
    key = env_key(proj, "PEXELS_API_KEY") if not all(use_local.values()) else None

    pb_key = None
    if key:
        try: pb_key = env_key(proj, "PIXABAY_API_KEY")
        except SystemExit: print("  (không có PIXABAY_API_KEY → chỉ dùng Pexels)")

    def cached(name, fetch):   # lỗi (None) thì không lưu → lần sau gọi lại
        cf = fd / "search" / (hashlib.md5(name.encode()).hexdigest()[:12] + ".json")
        if cf.exists(): return load(cf)
        out = fetch()
        if out is not None: save(out, cf)
        return out

    def pexels(q):   # → danh sách chung {id, text, dur, file, width, url, author}
        def fetch():
            vids = []
            for page in (1, 2):
                r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key}, timeout=30,
                                 params={"query": q, "orientation": "landscape", "per_page": 80, "page": page})
                r.raise_for_status(); vids += r.json().get("videos", [])
            return vids
        out = []
        for v in cached(q, fetch):
            fs = [f for f in v["video_files"] if f.get("width") and f.get("height") and f["file_type"] == "video/mp4" and f["width"] > f["height"]]
            ok = [f for f in fs if f["width"] >= W]
            f = min(ok, key=lambda f: f["width"]) if ok else (max(fs, key=lambda f: f["width"]) if fs else None)
            if f: out.append({"id": str(v["id"]), "text": "-" + v["url"].rstrip("/").split("/")[-1] + "-", "dur": v["duration"],
                              "file": f["link"], "width": f["width"], "url": v["url"], "author": v["user"]["name"]})
        return out

    pb_state = {"last": 0.0, "off": False}
    def pixabay(q):  # tag do người đăng tự gõ → dùng làm "text" để lọc địa danh
        if not pb_key: return []
        def fetch():
            if pb_state["off"]: return None
            time.sleep(max(0, pb_state["last"] + 1.2 - time.time())); pb_state["last"] = time.time()   # ≤ 50 lượt/phút
            r = requests.get("https://pixabay.com/api/videos/", timeout=30, params={"key": pb_key, "q": q[:100], "per_page": 100, "safesearch": "true", "video_type": "film", "min_width": 1280})
            if r.ok and "json" in r.headers.get("content-type", ""): return r.json().get("hits", [])
            # 429 = Cloudflare chặn TẠM theo IP công khai (cả n8n/Docker cùng IP cũng dính) → bỏ Pixabay ở lượt này, chạy lại sau
            pb_state["off"] = True; print(f"  ⚠ Pixabay HTTP {r.status_code} — tạm bỏ Pixabay ở lượt này (chạy lại footage sau sẽ lấy bù)"); return None
        hits = cached("pixabay:" + q, fetch) or []
        out = []
        for h in hits:
            vs = [x for x in h["videos"].values() if x.get("url") and x["width"] > x["height"]]
            ok = [x for x in vs if x["width"] >= W]
            f = min(ok, key=lambda x: x["width"]) if ok else (max(vs, key=lambda x: x["width"]) if vs else None)
            if f: out.append({"id": f"pb{h['id']}", "text": "-" + re.sub(r"[^a-z0-9]+", "-", h["tags"].lower()) + "-", "dur": h["duration"],
                              "file": f["url"], "width": f["width"], "url": h["pageURL"], "author": h["user"]})
        return out

    WM_UA = {"User-Agent": "ai-marketing-video-kit/1.0 (https://github.com/MinhDung2209/ai-marketing-video-kit)"}
    def wikimedia(q):   # Commons: không cần key; tên file/mô tả/danh mục ghi đúng địa danh. Giấy phép CC → PHẢI ghi tác giả
        wq = q
        def fetch():
            r = requests.get("https://commons.wikimedia.org/w/api.php", headers=WM_UA, timeout=60, params={
                "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{wq} filetype:video", "gsrnamespace": 6,
                "gsrlimit": 50, "prop": "imageinfo|categories", "cllimit": "max", "iiprop": "url|size|mime|extmetadata"})
            if not r.ok: return None
            return list(r.json().get("query", {}).get("pages", {}).values())
        out = []
        for pg in cached("wikimedia:" + wq, fetch) or []:
            ii = (pg.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata", {})
            w, h, d = ii.get("width", 0), ii.get("height", 0), float(ii.get("duration") or 0)
            if not ii.get("url") or w < 1.6 * h or d < 4: continue   # chỉ video ngang ~16:9 (bỏ clip dọc bị viền đen)
            lic = md.get("LicenseShortName", {}).get("value", "")
            if not re.search(r"CC0|CC BY|Public domain", lic, re.I): continue
            text = fold(pg["title"] + " " + re.sub("<[^>]+>", " ", md.get("ImageDescription", {}).get("value", "")) + " " + " ".join(x["title"] for x in pg.get("categories", [])))
            author = re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip() or "Wikimedia Commons"
            out.append({"id": f"wm{pg['pageid']}", "text": text, "dur": d, "file": ii["url"], "width": w,
                        "url": ii.get("descriptionurl", ""), "author": f"{author} ({lic})"})
        return out

    # mọi địa danh trong kịch bản: clip Pixabay gắn ≥3 địa danh khác nhau = tag rác (vd 1 thác nước gắn cả hanoi, saigon, sapa) → loại
    # địa danh → chương; clip ghi địa danh của ≥2 chương khác nhau = tag rác (Pixabay: 1 clip núi đá Ninh Bình gắn cả "hanoi")
    # chương tổng hợp (mở đầu/kết: must có "vietnam") không tính
    place_ch = {}
    for k, c in enumerate(sc["chapters"]):
        if "vietnam" in c.get("must", []): continue
        for m in c.get("must", []): place_ch.setdefault(m, set()).add(k)
    def spam(text): return len({k for m, ks in place_ch.items() if f"-{m}-" in text for k in ks}) >= 2

    plan, used = [], {}
    lines_by_ch = {}
    for m in tm["lines"]: lines_by_ch.setdefault(m["chapter"], []).append(m)
    for ci, (c, ch) in enumerate(zip(sc["chapters"], tm["chapters"])):
        must, fb = c.get("must", []), c.get("fallback", [])
        pool = {v["id"]: v for v in local(c)} if use_local[c["id"]] else {}
        if pool: print(f"  {c['id']}: {len({v['file'] for v in pool.values()})} clip tải tay → {len(pool)} đoạn")
        jobs = [] if pool else [(q, lambda q: pexels(q) + pixabay(q)) for q in c["queries"]]
        # Wikimedia: CHỈ khi chương có "wm_queries" — đo 15/10/2026 kết quả tự động lẫn nhiều rác (màn chữ "Present",
        # logo kênh khác, tin bão lũ có chữ, dashcam, quảng cáo) → nên duyệt tay rồi ghi id tốt vào plan / blacklist phần còn lại
        jobs += [(q, wikimedia) for q in c.get("wm_queries", [])]
        for rank, (q, fn) in enumerate(jobs):
            for i, v in enumerate(fn(q)):
                t = v["text"]
                tier = 2 if any(f"-{m}-" in t for m in must) else (1 if any(f"-{m}-" in t for m in fb) else 0)
                if not tier or spam(t) or v["dur"] < 3 or v["id"] in black or v["width"] < 1280: continue
                if v["id"] not in pool: pool[v["id"]] = {**v, "tier": tier, "rank": rank * 200 + i}
        ls = lines_by_ch[ci]
        for li, m in enumerate(ls):
            s0 = ch["start"] if li == 0 else m["start"]
            s1 = ls[li + 1]["start"] if li + 1 < len(ls) else ch["end"]
            n = max(1, round((s1 - s0) / SHOT)); kw = sc["chapters"][ci]["lines"][li].get("kw", [])
            # clip gán riêng cho câu này (tải tay vào footage/local/<chương>/<số câu>/) → dùng trước; clip của câu KHÁC
            # không bao giờ lấy (vd câu "Cầu Rồng phun lửa" không nhận clip Hội An), clip chung của chương lấp phần còn lại
            own = [p for p in pool.values() if p.get("line") == li]; gen = [p for p in pool.values() if p.get("line") is None]
            for k in range(n):
                fresh = lambda g: [p for p in g if p["id"] not in used]
                cand = fresh(own) or fresh(gen)
                if not cand and pool:   # hết clip mới → dùng lại clip ít dùng nhất (đoạn cắt khác) và báo
                    grp = own or gen or list(pool.values())
                    least = min(used.get(p["id"], 0) for p in grp); cand = [p for p in grp if used.get(p["id"], 0) == least]
                    print(f"  ⚠ {c['id']} câu {li}: hết clip mới, dùng lại clip — tải thêm / thêm queries")
                if not cand: raise SystemExit(f"Chương {c['id']}: không còn footage — thêm queries hoặc nới must/fallback")
                score = lambda p: p["tier"] * 10 + 3 * sum(f"-{w}" in p["text"] for w in kw) - p["rank"] / 400
                p = max(cand, key=score); used[p["id"]] = used.get(p["id"], 0) + 1
                a0 = s0 + (s1 - s0) * k / n; a1 = s0 + (s1 - s0) * (k + 1) / n
                plan.append({"chapter": ci, "line": m["id"], "start": round(a0, 3), "dur": round(a1 - a0, 3), "id": p["id"],
                             "tier": p["tier"], "url": p["url"], "author": p["author"], "file": p["file"], **({"local": p["local"]} if "local" in p else {})})
    for i, s in enumerate(plan):
        last = i + 1 == len(plan) or plan[i + 1]["chapter"] != s["chapter"]
        # tên file có id clip → đổi clip là cắt lại
        s["seg"] = f"{i:04d}_{s['id']}.mp4"; s["need"] = round(s["dur"] + (0 if last else XF), 3)
    weak = sum(1 for s in plan if s["tier"] < 2)
    print(f"{len(plan)} cảnh · {len(used)} clip khác nhau · {weak} cảnh chỉ khớp 'fallback' (không ghi đúng địa danh)")

    import threading
    locks = {s["id"]: threading.Lock() for s in plan}   # 1 clip dùng cho 2 cảnh → 2 luồng không tải trùng file
    def get(s):
        src = proj / s["file"] if "local" in s else fd / "src" / f"{s['id']}.mp4"
        with locks[s["id"]]:
            if not src.exists():
                tmp = src.with_suffix(".part")
                with requests.get(s["file"], stream=True, timeout=180, headers=WM_UA) as r:   # upload.wikimedia.org trả 403 nếu thiếu User-Agent
                    r.raise_for_status()
                    with open(tmp, "wb") as fh:
                        for chunk in r.iter_content(1 << 20): fh.write(chunk)
                tmp.replace(src)
        seg = seg_dir(proj) / s["seg"]
        if seg.exists() and (ok := probe(seg)) and abs(ok[0] - s["need"]) < 0.1: return   # file hỏng (lần trước lỗi giữa chừng) → cắt lại
        sd = dur(src); rnd = random.Random(f"{s['id']}-{s['seg']}")
        if "local" in s:   # đoạn thứ k trong k/slots phần của clip → các cảnh cùng clip không trùng hình
            k, n = s["local"]; w = sd / n
            off = k * w + max(0, (w - s["need"]) / 2) if w > s["need"] else max(0, min(k * w, sd - s["need"] - 0.1))
        else: off = rnd.uniform(0.3, sd - s["need"] - 0.3) if sd > s["need"] + 0.6 else 0
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1,"
              f"eq=saturation=1.08:contrast=1.03,tpad=stop_mode=clone:stop_duration={s['need']},format=yuv420p")
        sh(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{off:.2f}", "-i", str(src), "-t", str(s["need"]), "-an", "-vf", vf,
            *venc(a, 17), "-r", str(FPS), str(seg)])
    done = 0
    with ThreadPoolExecutor(a.jobs) as ex:
        for _ in ex.map(get, plan):
            done += 1
            if done % 20 == 0 or done == len(plan): print(f"  footage {done}/{len(plan)}", flush=True)
    save(plan, fd / "plan.json")
    credits = sorted({(s["author"], s["url"]) for s in plan})
    head = "Footage: Pexels (https://www.pexels.com/license/) · Pixabay (https://pixabay.com/service/license-summary/) · Wikimedia Commons (giấy phép ghi từng dòng)"
    if any("local" in s for s in plan): head += "\nFootage tải tay (Envato Elements / Storyblocks): giấy phép theo tài khoản đã tải — giữ danh sách file dưới đây làm bằng chứng"
    (proj / "footage_credits.txt").write_text(head + "\n" + "\n".join(f"{a} — {u}" for a, u in credits), encoding="utf-8")
    sheets(proj, plan)

def sheets(proj, plan):
    from PIL import Image, ImageDraw
    fd = proj / "footage"; (fd / "thumb").mkdir(exist_ok=True)
    def thumb(s):
        t = fd / "thumb" / s["seg"].replace(".mp4", ".jpg")
        sh(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(s["dur"] / 2), "-i", str(seg_dir(proj) / s["seg"]), "-frames:v", "1", "-vf", "scale=320:-2", str(t)])
        return t
    with ThreadPoolExecutor(8) as ex: thumbs = list(ex.map(thumb, plan))
    for ci in sorted({s["chapter"] for s in plan}):
        idx = [i for i, s in enumerate(plan) if s["chapter"] == ci]; cols = 8
        im = Image.new("RGB", (cols * 320, -(-len(idx) // cols) * 180), "black"); dr = ImageDraw.Draw(im)
        for j, i in enumerate(idx):
            x, y = (j % cols) * 320, (j // cols) * 180; im.paste(Image.open(thumbs[i]), (x, y))
            col = "yellow" if plan[i]["tier"] == 2 else "orange"
            dr.rectangle((x, y, x + 150, y + 26), fill="black"); dr.text((x + 5, y + 4), f"{i} · {plan[i]['id']}", fill=col, font_size=16)
        im.save(fd / f"_sheet_{ci:02d}.jpg", quality=80)
    print("ảnh ghép từng chương: footage/_sheet_*.jpg (số vàng = đúng địa danh, cam = chỉ 'vietnam')")

# ------------------------------------------------------------------ 2b. footage tải tay (Envato Elements / Storyblocks)
COLLECT_CSS = """body{font:15px/1.5 system-ui,sans-serif;margin:0;padding:16px;background:#f4f4f2;color:#1d1d1b}
.top{position:sticky;top:0;background:#1d1d1b;color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:14px;z-index:2}
.card{background:#fff;border:3px solid transparent;border-radius:10px;padding:12px 14px;margin-bottom:12px;cursor:pointer}
.card.on{border-color:#1a7f37}.full>h2>.cnt,li.full>.cnt{background:#1a7f37;color:#fff}
li.ln{border:2px solid transparent;border-radius:6px;padding:4px 6px;margin:2px 0}li.ln.on{border-color:#1a7f37;background:#1a7f3712}
h2{font-size:17px;margin:0 0 6px;display:flex;gap:10px;align-items:center}.cnt{font-size:13px;padding:2px 8px;border-radius:12px;background:#eee}
ol{margin:6px 0;padding-left:22px;color:#444;font-size:14px}.kw{color:#8a5a00;font-size:12px}
a.q{display:inline-block;margin:3px 4px 0 0;padding:4px 10px;border-radius:6px;text-decoration:none;font-size:13px;color:#fff}
a.Envato{background:#82b541}a.Storyblocks{background:#0b5cad}#log{font-size:12px;opacity:.85;margin-top:4px}
@media (prefers-color-scheme:dark){body{background:#111;color:#eee}.card{background:#1e1e1e}ol{color:#bbb}.cnt{background:#333}}"""

def collect(proj, a):
    import html as hm, http.server, math, shutil, threading, webbrowser, zipfile
    from urllib.parse import urlparse, parse_qs
    sc = load(proj / "script.json"); root = proj / "footage" / "local"; root.mkdir(parents=True, exist_ok=True)
    dl = pathlib.Path(a.downloads)
    if not dl.is_dir(): raise SystemExit(f"Không thấy thư mục tải về: {dl} — dùng --downloads <thư mục>")
    tm = load(proj / "audio/timing.json") if (proj / "audio/timing.json").exists() else None
    # đích nhận file: "<chương>" (clip chung) hoặc "<chương>/<số câu>" (clip riêng cho đúng câu đó)
    need = {}   # số cảnh ~SHOT giây → số clip cần tải (mỗi clip ~3 cảnh)
    for ci, c in enumerate(sc["chapters"]):
        for li, ln in enumerate(c["lines"]):
            if tm:
                ls = [m for m in tm["lines"] if m["chapter"] == ci]
                s1 = ls[li + 1]["start"] if li + 1 < len(ls) else tm["chapters"][ci]["end"]
                secs = s1 - (tm["chapters"][ci]["start"] if li == 0 else ls[li]["start"])
            else: secs = len(ln["text"].split()) / 2.6 + GAP + ((TITLE_LEAD if c.get("title") else LEAD) if li == 0 else 0)
            need[f"{c['id']}/{li:02d}"] = max(1, round(secs / SHOT))   # tạm giữ số cảnh, đổi ra số clip bên dưới
        need[c["id"]] = math.ceil(sum(v for k, v in need.items() if k.startswith(c["id"] + "/")) / 3)
    for k in [k for k in need if "/" in k]: need[k] = math.ceil(need[k] / 3)
    def count(t):
        d = root / t
        return sum(1 for f in d.rglob("*") if f.suffix.lower() in VIDEO_EXT) if d.exists() else 0
    st = {"active": sc["chapters"][0]["id"], "log": []}

    def uniq(p):
        i = 2
        while p.exists(): p = p.with_name(f"{p.stem}_{i}{p.suffix}"); i += 1
        return p
    def place(f):   # file tải xong → footage/local/<chương đang chọn>/ (zip thì giải nén lấy video)
        dest = root / st["active"]; dest.mkdir(parents=True, exist_ok=True)
        if f.suffix.lower() == ".zip":
            with zipfile.ZipFile(f) as z:
                vids = [n for n in z.namelist() if pathlib.Path(n).suffix.lower() in VIDEO_EXT and not n.startswith("__MACOSX")]
                for n in vids:
                    with z.open(n) as src, open(uniq(dest / pathlib.Path(n).name), "wb") as out: shutil.copyfileobj(src, out)
            if not vids: return False   # zip không chứa video (tài liệu khác) → để yên
            f.unlink(); names = [pathlib.Path(n).name for n in vids]
        else: shutil.move(str(f), str(uniq(dest / f.name))); names = [f.name]
        for n in names: st["log"].insert(0, f"{st['active']} ← {n}"); print(f"  {st['active']} ← {n}", flush=True)
        del st["log"][8:]; return True

    seen, sizes = {f.name for f in dl.iterdir()}, {}   # file có sẵn trong Downloads trước khi chạy: không đụng tới
    def watch():
        while True:
            for f in list(dl.iterdir()):
                if f.name in seen or not f.is_file() or f.suffix.lower() not in VIDEO_EXT | {".zip"}: continue   # .crdownload/.part: đang tải
                if (dl / (f.name + ".part")).exists(): continue   # Firefox tạo sẵn file rỗng + .part
                sz = f.stat().st_size
                if not sz or sizes.get(f.name) != sz: sizes[f.name] = sz; continue   # chờ kích thước đứng yên 1 nhịp
                try: place(f); seen.add(f.name)
                except PermissionError: pass   # trình duyệt còn giữ file → nhịp sau
                except Exception as e: seen.add(f.name); print(f"  ⚠ {f.name}: {e}", flush=True)
            time.sleep(1.5)

    cards = []
    for ci, c in enumerate(sc["chapters"]):
        name = c.get("title") or c.get("chapter_name") or c["id"]
        spot = c.get("place") or (c.get("must") or [""])[0].replace("-", " ")
        def link(q, short=False):
            slug = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")
            return "".join(f"<a class='q {s}' target=_blank href='{hm.escape(u.format(slug=slug))}'>{s if short else s + ': ' + hm.escape(q)}</a>" for s, u in SEARCH.items())
        def line_q(ln):   # "q" do người/AI viết cho đúng cảnh của câu; thiếu thì ghép địa danh + 2 kw đầu
            return ln.get("q") or " ".join([spot] + ln.get("kw", [])[:2]).strip()
        lines = "".join(f"<li class=ln data-t='{c['id']}/{li:02d}'>{hm.escape(ln['text'])} <span class=cnt></span><br>"
                        f"<span class=kw>{hm.escape(line_q(ln))}</span> {link(line_q(ln), True)}</li>" for li, ln in enumerate(c["lines"]))
        links = "".join(link(q) for q in c.get("stock_queries") or c["queries"])
        cards.append(f"<div class=card data-t='{c['id']}'><h2>{ci:02d} · {hm.escape(name)} <span class=cnt></span></h2><ol>{lines}</ol>{links}</div>")
    page = f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Tải footage</title><style>{COLLECT_CSS}</style>
<div class=top><b>{hm.escape(sc.get('title', proj.name))}</b> — bấm vào <b>câu</b> cần cảnh riêng (vd "Cầu Rồng phun lửa") hoặc tiêu đề chương (clip chung) — viền xanh = file tải về sẽ vào đó → bấm link tìm → chọn clip → Download.
Envato: đăng ký license theo tên kênh của khách. Cài trình duyệt lưu thẳng vào <code>{hm.escape(str(dl))}</code>, không hỏi chỗ lưu.<div id=log></div></div>
{''.join(cards)}
<script>
const pick=t=>fetch('/active?ch='+encodeURIComponent(t)).then(tick);
document.querySelectorAll('[data-t]').forEach(c=>c.addEventListener('click',e=>{{e.stopPropagation();pick(c.dataset.t);}}));
async function tick(){{const s=await (await fetch('/status')).json();
 document.querySelectorAll('[data-t]').forEach(c=>{{const t=c.dataset.t,n=s.counts[t],m=s.need[t];
  c.classList.toggle('on',t===s.active);c.classList.toggle('full',n>=m);c.querySelector('.cnt').textContent=n+'/'+m+' clip';}});
 document.getElementById('log').textContent=s.log.join(' · ');}}
tick();setInterval(tick,2000);
</script>"""

    class Hd(http.server.BaseHTTPRequestHandler):
        def log_message(self, *x): pass
        def send(self, body, ctype):
            b = body.encode(); self.send_response(200); self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/active":
                ch = parse_qs(u.query).get("ch", [""])[0]
                if ch in need: st["active"] = ch
                return self.send("{}", "application/json")
            if u.path == "/status":
                return self.send(json.dumps({"active": st["active"], "log": st["log"], "need": need,
                                             "counts": {t: count(t) for t in need}}, ensure_ascii=False), "application/json")
            self.send(page, "text/html")

    threading.Thread(target=watch, daemon=True).start()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), Hd); url = f"http://127.0.0.1:{a.port}/"
    print(f"Trang tải footage: {url}\nĐang canh {dl} → {root} · Ctrl+C để dừng, xong thì chạy: longform.py footage {proj}", flush=True)
    if not a.no_open: webbrowser.open(url)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    print("Đã có: " + ", ".join(f"{c['id']} {count(c['id'])}/{need[c['id']]}" for c in sc["chapters"]))

# ------------------------------------------------------------------ 3. render
def ass_time(t): return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
def srt_time(t): return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(t * 1000 % 1000):03d}"

def render(proj, a):
    sys.path.insert(0, str(TOOLS)); from captions import build as build_caps
    tm = load(proj / "audio/timing.json"); plan = load(proj / "footage/plan.json"); sc = load(proj / "script.json"); set_res(sc)
    rd = proj / "render" / ("" if H == 1080 else f"{H}p"); rd.mkdir(parents=True, exist_ok=True); D = tm["total"]
    # 3a. mỗi chương = chuỗi xfade, mờ từ/đến đen ở đầu/cuối chương
    parts = []
    for ci, ch in enumerate(tm["chapters"]):
        segs = [s for s in plan if s["chapter"] == ci]; out = rd / f"ch{ci:02d}.mp4"; parts.append(out)
        cd = round(sum(s["dur"] for s in segs), 3)
        if out.exists() and not a.force and abs(dur(out) - cd) < 0.1: continue
        inp, flt, last, off = [], [], "[0:v]", 0.0
        for j, s in enumerate(segs): inp += ["-i", str(seg_dir(proj) / s["seg"])]
        for j in range(1, len(segs)):
            off += segs[j - 1]["dur"]
            # cảnh j-1 dài dur+XF → mờ sang cảnh j bắt đầu đúng ở mốc cộng dồn dur
            # (đo 15/10/2026: lấy off - XF làm mỗi chương hụt 0,5s → 11 chương lệch tiếng ~5s)
            flt.append(f"{last}[{j}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{j}]"); last = f"[x{j}]"
        fo = max(0, cd - 0.8)
        flt.append(f"{last}fade=t=in:st=0:d=0.8,fade=t=out:st={fo:.3f}:d=0.8,trim=duration={cd},setpts=PTS-STARTPTS[v]")
        sh(["ffmpeg", "-y", "-loglevel", "error", *inp, "-filter_complex", ";".join(flt), "-map", "[v]", *venc(a, 16),
            "-r", str(FPS), "-pix_fmt", "yuv420p", str(out)])
        print(f"  chương {ci} ({ch['id']}): {len(segs)} cảnh, {cd:.1f}s", flush=True)
    with open(rd / "list.txt", "w", encoding="utf-8") as fh: fh.writelines(f"file '{p.name}'\n" for p in parts)
    sh(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(rd / "list.txt"), "-c", "copy", str(rd / "video.mp4")])
    # 3b. tiêu đề chương (ASS)
    font = a.font   # toạ độ chữ luôn theo khung 1920×1080 — libass tự phóng lên 4K
    ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "", "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: T,{font},112,&H00FFFFFF,&H00FFFFFF,&H90000000,&H64000000,1,0,0,0,100,100,10,0,1,5,2,5,80,80,0,1",   # viền tối mờ (+\blur) → đọc được cả trên nền sáng
           f"Style: S,{font},48,&H00FFFFFF,&H00FFFFFF,&H90000000,&H64000000,1,0,0,0,100,100,4,0,1,4,1,5,80,80,0,1",
           "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for ch in tm["chapters"]:
        if not ch["title"]: continue
        t0, t1 = ch["start"] + 0.6, ch["start"] + TITLE_LEAD + 2.2
        ass.append(f"Dialogue: 0,{ass_time(t0)},{ass_time(t1)},T,,0,0,0,,{{\\pos(960,510)\\fad(700,700)\\blur4}}{ch['title']}")
        if ch["subtitle"]:
            ass.append(f"Dialogue: 0,{ass_time(t0 + 0.4)},{ass_time(t1)},S,,0,0,0,,{{\\pos(960,610)\\fad(700,700)\\blur3}}{ch['subtitle']}")
    (rd / "titles.ass").write_text("\n".join(ass) + "\n", encoding="utf-8")
    rel = rd.relative_to(proj).as_posix()
    # 3c. âm thanh: giọng + nhạc (tự lặp, tự hạ khi có giọng) — dùng lại mix_audio.py
    bgm = sc.get("bgm", {})
    cues = {"duration": D, "voice": {"file": "audio/narration.mp3", "volume": 1.0}, "sfx": []}
    if bgm.get("file"): cues["bgm"] = {"volume": 0.22, "fade_in": 1.5, "fade_out": 4, "duck": True, "start": 0, **bgm}
    save(cues, rd / "cues.json")
    sh([sys.executable, str(TOOLS / "mix_audio.py"), str(rd / "cues.json"), str(rd / "final_audio.mp3")], cwd=proj)
    # 3d. xuất cuối
    out = proj / a.out
    sh(["ffmpeg", "-y", "-loglevel", "error", "-stats", "-i", str(rd / "video.mp4"), "-i", str(rd / "final_audio.mp3"),
        "-vf", f"ass={rel}/titles.ass", "-map", "0:v", "-map", "1:a", *venc(a, a.crf, a.preset, final=True),
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)], cwd=proj)
    caps = build_caps(proj / "audio/timing.json", 84)
    (proj / pathlib.Path(a.out).with_suffix(".srt").name).write_text(
        "\n".join(f"{i + 1}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n" for i, c in enumerate(caps)), encoding="utf-8")
    names = {c["id"]: c.get("chapter_name") or c.get("title") or c["id"] for c in sc["chapters"]}   # chương không tiêu đề: "chapter_name"
    chap_txt = "\n".join(f"{int(c['start'] // 60):02d}:{int(c['start'] % 60):02d} {names[c['id']]}" for c in tm["chapters"])
    (proj / "youtube_chapters.txt").write_text(chap_txt + "\n", encoding="utf-8")
    print(f"xong: {out} · phụ đề .srt · mốc chương youtube_chapters.txt")

ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
for name in ("tts", "footage", "render", "collect"):
    p = sub.add_parser(name); p.add_argument("project"); p.add_argument("--jobs", type=int, default=4); p.add_argument("--force", action="store_true")
    if name == "tts": p.add_argument("--only", help="đọc lại các câu này, vd 03-02,05-01"); p.add_argument("--tempo", type=float, default=1.0)
    if name in ("footage", "render"): p.add_argument("--nvenc", action="store_true", help="mã hoá bằng card NVIDIA (nên bật khi 4K)")
    if name == "footage": p.add_argument("--source", choices=("auto", "local", "stock"), default="auto",
                                         help="auto: chương có footage/local/<chương>/ thì dùng tải tay, không thì Pexels/Pixabay")
    if name == "render":
        p.add_argument("--out", default="video.mp4"); p.add_argument("--crf", type=int, default=19)
        p.add_argument("--preset", default="medium"); p.add_argument("--font", default="Segoe UI Semibold")
    if name == "collect":
        p.add_argument("--downloads", default=str(pathlib.Path.home() / "Downloads"), help="thư mục trình duyệt lưu file tải về")
        p.add_argument("--port", type=int, default=8765); p.add_argument("--no-open", action="store_true")
a = ap.parse_args()
{"tts": tts, "footage": footage, "render": render, "collect": collect}[a.cmd](pathlib.Path(a.project).resolve(), a)
