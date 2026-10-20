"""Ảnh/video thật từ báo điện tử Việt Nam cho video tin tức (skill news-explainer).

  python <kit>/tools/news_media.py search "<từ khoá>" [--days 3] [--sites vnexpress,tuoitre,...] [-o bai.json]
      → bài mới nhất từng báo: ngày đăng, tiêu đề, link, số ảnh/video
  python <kit>/tools/news_media.py grab <link bài> <thư mục> [--video] [--shot]
      → <thư mục>/<báo>-<mã bài>/: ảnh bản lớn nhất, video (--video, mở trang bằng Playwright để bắt luồng m3u8/mp4),
        ảnh chụp đầu bài (--shot), media.json: báo, link, tiêu đề, giờ đăng, chú thích + tác giả ảnh ("Ảnh: ...") từng file
  python <kit>/tools/news_media.py sheet <thư mục> → contact.jpg để duyệt: ảnh nào khớp câu thoại nào

Ảnh báo có bản quyền của tòa soạn/tác giả (không phải CC). Người dùng chọn dùng (20/10/2026) và tự chịu rủi ro khiếu nại →
luôn giữ media.json để ghi nguồn trên hình + mô tả video. Không xoá logo/watermark của báo.
Đo 20/10/2026: VnExpress, Tuổi Trẻ, Dân trí, Thanh Niên, Báo Chính phủ trả HTML thường (không cần trình duyệt);
ảnh nằm trong <figure>, chú thích có "Ảnh: <tác giả>"; giờ đăng ở meta article:published_time / datePublished.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import argparse, datetime as dt, html, io, json, math, pathlib, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor
import requests
from PIL import Image, ImageDraw, ImageFont

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
      "Accept-Language": "vi-VN,vi;q=0.9"}
# trang tìm kiếm → link bài (bài có mã số dài ở cuối)
SITES = {
    "vnexpress":  ("https://timkiem.vnexpress.net/", "q", "https://vnexpress.net"),
    "tuoitre":    ("https://tuoitre.vn/tim-kiem.htm", "keywords", "https://tuoitre.vn"),
    "dantri":     ("https://dantri.com.vn/tim-kiem/{q}.htm", None, "https://dantri.com.vn"),
    "thanhnien":  ("https://thanhnien.vn/tim-kiem.htm", "keywords", "https://thanhnien.vn"),
    "baochinhphu": ("https://baochinhphu.vn/tim-kiem.htm", "keywords", "https://baochinhphu.vn"),
}
NAMES = {"vnexpress": "VnExpress", "tuoitre": "Tuổi Trẻ", "dantri": "Dân trí", "thanhnien": "Thanh Niên",
         "baochinhphu": "Báo Điện tử Chính phủ", "vietnamnet": "VietNamNet", "vtv": "VTV", "laodong": "Lao Động",
         "nld": "Người Lao Động", "zingnews": "Znews", "znews": "Znews", "vov": "VOV", "vietnamplus": "VietnamPlus"}

def outlet(url):
    host = re.sub(r"^www\.", "", requests.utils.urlparse(url).netloc)
    key = host.split(".")[0] if not host.startswith("timkiem") else "vnexpress"
    return key, NAMES.get(key, host)

def get(url, headers=None, **kw):
    r = requests.get(url, headers={**UA, **(headers or {})}, timeout=30, **kw); r.raise_for_status(); return r

def clean(s): return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()

def meta(t, *names):
    for n in names:
        m = re.search(rf'<meta[^>]+(?:property|name|itemprop)="{n}"[^>]+content="([^"]+)"', t) \
            or re.search(rf'<meta[^>]+content="([^"]+)"[^>]+(?:property|name|itemprop)="{n}"', t)
        if m: return html.unescape(m.group(1))
    return ""

def published(t):
    v = meta(t, "article:published_time", "pubdate", "datePublished") or \
        next(iter(re.findall(r'"datePublished"\s*:\s*"([^"]+)"', t)), "")
    return html.unescape(v)

def parse_time(s):   # "2026-10-19T20:18:19+07:00" (không múi giờ → coi là giờ VN)
    try: t = dt.datetime.fromisoformat(s.strip().replace(" ", "T")[:25])
    except ValueError: return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone(dt.timedelta(hours=7)))

def credit(caption):   # "... Ảnh: VĂN TRUNG" / "(Ảnh: SBV)." / "- Ảnh: Cổng TTĐT Quốc hội"
    m = re.search(r"(?:Ảnh|Video|Clip|Nguồn)\s*:\s*([^().]+?)\s*\)?\.?\s*$", caption, re.I) \
        or re.search(r"Ảnh\s+(\S+\.vn/[^()]+?)\s*\)?\.?\s*$", caption)   # Báo CP: "- Ảnh chinhphu.vn/Đức Tuân" (không có dấu hai chấm)
    return m.group(1).strip(" -–") if m else ""

def hires(src):
    """Bản lớn hơn của ảnh CDN báo (thử lần lượt, không được thì giữ bản gốc trong bài)."""
    c = []
    if re.search(r"/thumb_w/\d+/", src): c.append(re.sub(r"/thumb_w/\d+/", "/", src))          # Tuổi Trẻ, Thanh Niên, Báo CP
    if re.search(r"/zoom/\d+_\d+/", src): c.append(re.sub(r"/zoom/\d+_\d+/", "/", src))
    if "vnecdn.net" in src and "w=" in src: c.append(src.split("?")[0])                          # VnExpress: bỏ tham số co ảnh
    m = re.match(r"https://cdnphoto\.dantri\.com\.vn/[^/]+=/(.+)", src)
    if m: c.append("https://icdn.dantri.com.vn/" + m.group(1))
    return c + [src]

def figures(t, base):
    """[(link ảnh, chú thích)] theo thứ tự trong bài; bỏ ảnh quảng cáo/logo nhỏ."""
    out = []
    for m in re.finditer(r"<figure[^>]*>.*?</figure>", t, re.S):
        s = m.group(0)
        srcs = re.findall(r'(?:data-src|data-original|data-srcset|src)="([^"\s]+\.(?:jpe?g|png|webp)[^"\s]*)', s, re.I)
        if not srcs: continue
        src = html.unescape(srcs[0]); src = src if src.startswith("http") else requests.compat.urljoin(base, src)
        c = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", s, re.S) or re.search(r'class="[^"]*(?:caption|desc)[^"]*"[^>]*>(.*?)</', s, re.S)
        cap = clean(c.group(1)) if c else ""
        if src not in (x for x, _ in out): out.append((src, cap))
    return out

ADS = re.compile(r"/adt/|admicro|googlesyndication|doubleclick|/banners?/|[/.]ads?[/.]|preroll|postroll", re.I)

def html_videos(t):
    """Video nhúng sẵn link trong HTML thân bài (VTV 20/10: <div data-vid="https://cdn-videos.vtv.vn/.../h264/mp4/...mp4">)."""
    i = max(t.find("detail-content"), t.find("article-content"), t.find("fck_detail"), 0)
    urls = re.findall(r'data-(?:vid|src|file|video-src|url)="((?:https?:)?//[^"\s]+?\.(?:mp4|m3u8)[^"\s]*)"', t[i:])
    return [u if u.startswith("http") else "https:" + u for u in dict.fromkeys(urls) if not ADS.search(u) and "/thumb/" not in u]

def article(url):
    t = get(url).text; key, name = outlet(url)
    return {"outlet": name, "site": key, "url": url, "title": meta(t, "og:title") or clean((re.search(r"<title>(.*?)</title>", t, re.S) or [""," "])[1]),
            "published": published(t), "description": meta(t, "og:description", "description"),
            "og_image": meta(t, "og:image"), "figures": figures(t, url), "videos": html_videos(t)}

# ------------------------------------------------------------------ search
def search_site(site, q):
    page, param, base = SITES[site]
    r = get(page.format(q=requests.utils.quote(q.lower().replace(" ", "-"))) if param is None else page, params={param: q} if param else None)
    links = re.findall(r'href="((?:https?://[^"]+|/[^"]+?)-\d{7,}\.html?)"', r.text)
    full = [l if l.startswith("http") else base + l for l in links]
    host = requests.utils.urlparse(base).netloc
    return [l for l in dict.fromkeys(full) if host in l and "/video-" not in l.split(host)[-1][:7]]

def u_host(u): return requests.utils.urlparse(u).netloc

def cmd_search(a):
    sites = a.sites.split(",") if a.sites else list(SITES)
    def links(s):
        try: return search_site(s, a.query)[:a.per_site]
        except Exception as e: print(f"  ⚠ {s}: {str(e)[:100]}"); return []
    with ThreadPoolExecutor(5) as ex: found = [u for ls in ex.map(links, sites) for u in ls]
    since = dt.datetime.now().astimezone() - dt.timedelta(days=a.days)
    rows = []
    def info(u):
        try: return article(u)
        except Exception as e: return {"url": u, "error": str(e)[:120]}
    with ThreadPoolExecutor(8) as ex:
        for r in ex.map(info, found):
            if "error" in r: print("  ⚠", r["url"], r["error"]); continue
            when = parse_time(r["published"])
            if when and when < since: continue
            r["n_images"] = len(r.pop("figures")); r["has_video"] = bool(r["videos"]) or "video." in u_host(r["url"]); rows.append(r)
    rows.sort(key=lambda r: r["published"], reverse=True)
    for r in rows:
        print(f"{r['published'][:16]:16} {r['outlet']:12} {r['n_images']} ảnh{' +video' if r['has_video'] else ''} · {r['title'][:80]}\n   {r['url']}")
    if a.out: json.dump(rows, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(rows)} bài trong {a.days} ngày")

# ------------------------------------------------------------------ grab
def save_image(src, out):
    for u in hires(src):
        try:
            r = get(u, headers={"Referer":"https://" + requests.utils.urlparse(src).netloc + "/"})
            im = Image.open(io.BytesIO(r.content)); im.load()
        except Exception: continue
        im = im.convert("RGB"); im.save(out, quality=95)
        return u, im.size
    return None, None

def browse(url, folder, video, shot, known=(), prefix=""):
    """Mở bài bằng Chromium của Playwright: chụp đầu bài; phát video, bắt link m3u8/mp4 trong lưu lượng mạng, tải bằng ffmpeg.
    known = link video đọc thẳng từ HTML → không cần bắt mạng."""
    from playwright.sync_api import sync_playwright
    net, streams, files = [], [], []
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 900}, user_agent=UA["User-Agent"],
                                                 locale="vi-VN", device_scale_factor=2)
        pg.on("request", lambda r: net.append(r.url) if re.search(r"\.(m3u8|mp4)(\?|$)", r.url) and not ADS.search(r.url) else None)
        if shot or (video and not known): pg.goto(url, wait_until="domcontentloaded", timeout=60000); time.sleep(3)
        if shot:   # vùng logo báo + tiêu đề (không chụp cả trang: dính quảng cáo, banner cookie)
            h1 = pg.locator("h1").first; box = h1.bounding_box() if h1.count() else None
            clip = {"x": max(0, box["x"] - 60), "y": max(0, box["y"] - 160), "width": min(1280, box["width"] + 120),
                    "height": box["height"] + 260} if box else None
            pg.screenshot(path=str(folder / f"{prefix}shot.png"), clip=clip)
            files.append({"file": f"{prefix}shot.png", "kind": "screenshot"})
        # chỉ video trong thân bài; khung phát nổi / tin liên quan (Dân trí 20/10: clip "đề xuất" tự phát) không tính
        body = "article, [class*=detail], [class*=content], [class*=singular], [class*=body]"
        skip = "[class*=float], [class*=sticky], [class*=relate], [class*=suggest], [class*=recommend], aside"
        for v in pg.locator("video").all()[:6] if video and not known else []:
            if not v.evaluate("(v, [b, s]) => !!v.closest(b) && !v.closest(s)", [body, skip]): continue
            seen = len(net)
            try: v.scroll_into_view_if_needed(timeout=3000); v.evaluate("v => { v.muted = true; v.play() }"); time.sleep(5)
            except Exception: pass
            src = v.evaluate("v => v.currentSrc || v.src || ''")
            if src.startswith("blob:"):   # m3u8 phát qua MSE → lấy luồng phát sinh khi bấm phát, hoặc luồng tải sẵn lúc mở trang (VnExpress)
                streams += net[seen:] or [u for u in net if ".m3u8" in u]
            elif re.search(r"\.(mp4|m3u8)(\?|$)", src): streams.append(src)   # bỏ ảnh xem trước .gif trong thẻ <video>
        b.close()
    # cùng 1 video có master m3u8 + m3u8 từng độ phân giải (VnExpress 20/10: master ",480p,," + 480p/index) → có master thì chỉ lấy
    # master (ffmpeg tự chọn luồng nét nhất); bỏ đoạn .ts lẻ
    streams = [s for s in dict.fromkeys([*known, *streams]) if not re.search(r"\.ts(\?|$)", s) and not ADS.search(s)] if video else []
    picks = [s for s in streams if re.search(r"master|playlist", s)] or streams
    for i, first in enumerate(picks[:4]):
        out = folder / f"{prefix}video-{i + 1}.mp4"
        # VTV 20/10: link .mp4 trong data-vid trả 400, trình phát dùng "<link .mp4>/master.m3u8"
        for s in [first] + ([first.split("?")[0] + "/master.m3u8"] if re.search(r"\.mp4(\?|$)", first) else []):
            r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-headers", f"Referer: {url}\r\nUser-Agent: {UA['User-Agent']}\r\n",
                                "-i", s, "-c", "copy", "-bsf:a", "aac_adtstoasc", str(out)], capture_output=True, text=True)
            if not r.returncode and out.exists() and out.stat().st_size >= 50_000: break
            out.unlink(missing_ok=True)
        else:
            print("  ⚠ video", first[:100], (r.stderr or "")[-160:].strip()); continue
        files.append({"file": out.name, "kind": "video", "stream": s}); print("  video", out.name, f"{out.stat().st_size / 1e6:.1f} MB")
    return files

def cmd_grab(a):
    art = article(a.url)
    aid = re.search(r"(\d{7,})\.html?$", a.url); folder = pathlib.Path(a.dir) / f"{art['site']}-{aid.group(1) if aid else 'bai'}"
    folder.mkdir(parents=True, exist_ok=True)
    figs = art.pop("figures") or ([(art["og_image"], "")] if art["og_image"] else [])
    items = []
    for i, (src, cap) in enumerate(figs, 1):
        out = folder / f"img-{i:02d}.jpg"
        used, size = save_image(src, out)
        if not used: print("  ⚠ ảnh", src[:100]); continue
        items.append({"file": out.name, "kind": "image", "size": list(size), "caption": cap, "credit": credit(cap), "src": used})
        print(f"  {out.name} {size[0]}×{size[1]} · {cap[:90]}")
    if a.video or a.shot: items += browse(a.url, folder, a.video, a.shot, art["videos"])
    art.update({"grabbed": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "items": items,
                "rights": "Bản quyền thuộc tòa soạn/tác giả ảnh — ghi nguồn khi dùng, không xoá logo/watermark"})
    json.dump(art, open(folder / "media.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{art['outlet']} · {art['published'][:16]} · {art['title'][:70]}\n→ {folder} ({len(items)} file)")

# ------------------------------------------------------------------ sheet
def cmd_sheet(a):
    root = pathlib.Path(a.dir); rows = []
    for mj in sorted(root.rglob("media.json")):
        m = json.load(open(mj, encoding="utf-8"))
        for it in m["items"]:
            f = mj.parent / it["file"]
            if it["kind"] == "video":
                thumb = f.with_suffix(".jpg")
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "2", "-i", str(f), "-frames:v", "1", str(thumb)])
                f = thumb
            if f.exists(): rows.append((f, f"{mj.parent.name}/{it['file']} · {m['outlet']} {m['published'][:10]}", it.get("caption", "")))
    if not rows: raise SystemExit("chưa có media.json nào trong " + str(root))
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15); W, H = 420, 300
    sheet = Image.new("RGB", (W * 3, math.ceil(len(rows) / 3) * H), "#111827"); d = ImageDraw.Draw(sheet)
    for i, (f, label, cap) in enumerate(rows):
        im = Image.open(f).convert("RGB"); im.thumbnail((W - 10, H - 60)); x, y = (i % 3) * W, (i // 3) * H
        sheet.paste(im, (x + 5, y + 5)); d.text((x + 5, y + H - 52), label[:58], font=font, fill="#facc15")
        d.text((x + 5, y + H - 32), cap[:58], font=font, fill="white")
    out = root / "contact.jpg"; sheet.save(out, quality=88); print(out, f"({len(rows)} hình)")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Ảnh/video thật từ báo điện tử VN")
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("search"); s.add_argument("query"); s.add_argument("--days", type=float, default=3)
    s.add_argument("--sites", help="mặc định: " + ",".join(SITES)); s.add_argument("--per-site", type=int, default=6)
    s.add_argument("-o", "--out"); s.set_defaults(fn=cmd_search)
    s = sp.add_parser("grab"); s.add_argument("url"); s.add_argument("dir")
    s.add_argument("--video", action="store_true", help="mở trang, bắt và tải video trong bài")
    s.add_argument("--shot", action="store_true", help="chụp màn hình đầu bài"); s.set_defaults(fn=cmd_grab)
    s = sp.add_parser("sheet"); s.add_argument("dir"); s.set_defaults(fn=cmd_sheet)
    a = p.parse_args(); a.fn(a)
