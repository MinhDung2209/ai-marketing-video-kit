"""Radar mạng xã hội cho agent tin tức (skill news-explainer): tìm tin/clip đang lên ở Việt Nam, lưu số đo theo thời gian.

Tầng 1 — không cần đăng nhập:
  python <kit>/tools/social_radar.py trends                 → Google Trends "đang thịnh hành" VN + YouTube thịnh hành VN (mọi mục, tin tức, giải trí, hài)
  python <kit>/tools/social_radar.py youtube "<từ khoá>" [--days 3]   → video mới theo lượt xem (token youtube_upload.py)
Tầng 3 — trình duyệt đã đăng nhập (profile riêng kit/.social-profile, KHÔNG commit; nên dùng tài khoản PHỤ):
  python <kit>/tools/social_radar.py login                  → mở Edge: đăng nhập Facebook, TikTok, X … rồi ĐÓNG cửa sổ
  python <kit>/tools/social_radar.py check                  → báo đã đăng nhập nền tảng nào (đọc cookie, không mở trang)
  python <kit>/tools/social_radar.py tiktok "<từ khoá>"     → video tìm được + lượt xem/thích/chia sẻ/giờ đăng (bắt JSON trang tự tải)
  python <kit>/tools/social_radar.py facebook "<từ khoá>"   → bài đăng tìm được (đọc từ trang, mục Bài viết + Video)
Báo cáo:
  python <kit>/tools/social_radar.py report [--hours 24]    → gộp mọi lần quét: xếp theo tốc độ tăng (cần ≥ 2 lần đo cùng link)

Kết quả: newsroom/signals/<YYYY-MM-DD>/<nguồn>-<HHMMSS>.json  {observed_at, source, query, items:[{platform, url, text, author,
published, metrics:{views, likes, comments, shares}}]}. Không bịa số: ô nào trang không hiện thì để null.
CHỈ ĐỌC (không like/bình luận/đăng); nghỉ ngẫu nhiên giữa thao tác. Tự động hoá đọc Facebook/TikTok trái điều khoản của họ →
tài khoản có thể bị khoá: dùng tài khoản phụ, quét thưa (vài lần/ngày).
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, contextlib, datetime as dt, html, json, os, pathlib, random, re, socket, subprocess, time
import requests

KIT = pathlib.Path(__file__).resolve().parent.parent
PROFILE = KIT / ".social-profile"
OUT = KIT / "newsroom" / "signals"
VN = dt.timezone(dt.timedelta(hours=7))
SITES = {"facebook": "https://www.facebook.com/", "tiktok": "https://www.tiktok.com/login", "x": "https://x.com/login"}
AUTH = {"facebook": ("facebook.com", ("c_user",)), "tiktok": ("tiktok.com", ("sessionid",)), "x": ("x.com", ("auth_token",))}

def now(): return dt.datetime.now(VN)

def save(source, query, items):
    t = now(); d = OUT / t.strftime("%Y-%m-%d"); d.mkdir(parents=True, exist_ok=True)
    f = d / f"{source}-{t.strftime('%H%M%S')}.json"
    json.dump({"observed_at": t.isoformat(timespec="seconds"), "source": source, "query": query, "items": items},
              open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ {f.relative_to(KIT)} ({len(items)} mục)"); return f

def num(s):   # "1,2 Tr" / "12K" / "3.4M" / "1.234" → số; không đọc được → None
    if s is None: return None
    if isinstance(s, (int, float)): return int(s)
    s = s.strip().replace("\u00a0", " ")
    m = re.match(r"([\d.,]+)\s*(K|N|nghìn|M|Tr|triệu|B|Tỷ)?", s, re.I)
    if not m: return None
    v, u = m.group(1), (m.group(2) or "").lower()
    if u: v = float(v.replace(",", "."))
    else: v = float(v.replace(".", "").replace(",", ""))
    return int(v * {"k": 1e3, "n": 1e3, "nghìn": 1e3, "m": 1e6, "tr": 1e6, "triệu": 1e6, "b": 1e9, "tỷ": 1e9}.get(u, 1))

# ------------------------------------------------------------------ tầng 1
def cmd_trends(a):
    r = requests.get("https://trends.google.com/trending/rss", params={"geo": "VN"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status(); items = []
    for it in re.findall(r"<item>(.*?)</item>", r.text, re.S):
        g = lambda tag: html.unescape((re.search(rf"<{tag}>(.*?)</{tag}>", it, re.S) or [None, ""])[1]).strip()
        news = [{"title": html.unescape(t), "url": u} for t, u in re.findall(r"<ht:news_item_title>(.*?)</ht:news_item_title>.*?<ht:news_item_url>(.*?)</ht:news_item_url>", it, re.S)]
        items.append({"platform": "google_trends", "url": "", "text": g("title"), "author": None, "published": g("pubDate"),
                      "metrics": {"searches": g("ht:approx_traffic")}, "news": news})
        print(f"  GG  {g('ht:approx_traffic'):>6}  {g('title')}  · {news[0]['title'][:60] if news else ''}")
    save("google_trends", "VN", items)
    sys_path(); import youtube_upload as yt
    for cat, name in (("", "all"), ("25", "news"), ("24", "entertainment"), ("23", "comedy")):
        p = {"part": "snippet,statistics", "chart": "mostPopular", "regionCode": "VN", "maxResults": 20, **({"videoCategoryId": cat} if cat else {})}
        try: vids = yt.api("GET", "videos", params=p).json().get("items", [])
        except SystemExit as e: print(f"  ⚠ YouTube {name}: {e}"); continue
        save(f"youtube_trending_{name}", "VN", [yt_item(v) for v in vids])
        for v in vids[:5]: print(f"  YT-{name:<13} {int(v['statistics'].get('viewCount', 0)):>10,}  {v['snippet']['title'][:70]}")

def sys_path():
    if str(KIT / "tools") not in sys.path: sys.path.insert(0, str(KIT / "tools"))

def yt_item(v):
    s, st = v["snippet"], v.get("statistics", {})
    return {"platform": "youtube", "url": f"https://youtu.be/{v['id'] if isinstance(v['id'], str) else v['id']['videoId']}", "text": s["title"],
            "author": s["channelTitle"], "published": s["publishedAt"],
            "metrics": {"views": num(st.get("viewCount")), "likes": num(st.get("likeCount")), "comments": num(st.get("commentCount")), "shares": None}}

def cmd_youtube(a):
    sys_path(); import youtube_upload as yt
    after = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=a.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids = [x["id"]["videoId"] for x in yt.api("GET", "search", params={"part": "id", "q": a.query, "type": "video", "order": "viewCount",
           "regionCode": "VN", "relevanceLanguage": "vi", "publishedAfter": after, "maxResults": 25}).json().get("items", [])]
    vids = yt.api("GET", "videos", params={"part": "snippet,statistics", "id": ",".join(ids)}).json().get("items", []) if ids else []
    for v in vids: print(f"  {int(v['statistics'].get('viewCount', 0)):>10,}  {v['snippet']['publishedAt'][:10]}  {v['snippet']['channelTitle'][:20]:<20} {v['snippet']['title'][:60]}")
    save("youtube_search", a.query, [yt_item(v) for v in vids])

# ------------------------------------------------------------------ trình duyệt (giống stock_dl.py: Edge thường + CDP, profile riêng)
def find_browser():
    for c in [os.environ.get("VIDEOKIT_SOCIAL_BROWSER", ""), r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]:
        if c and pathlib.Path(c).exists(): return c
    raise SystemExit("Không thấy Edge — đặt VIDEOKIT_SOCIAL_BROWSER=<đường dẫn trình duyệt>")

def browser_cmd(*extra): return [find_browser(), f"--user-data-dir={PROFILE}", "--no-first-run", "--no-default-browser-check", *extra]

@contextlib.contextmanager
def browser(show=False):
    """Không --headless (TikTok/Facebook chặn) → cửa sổ thật đặt ngoài màn hình; Playwright nối qua cổng debug cục bộ."""
    from playwright.sync_api import sync_playwright
    with socket.socket() as s: s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    hide = [] if show else ["--window-position=-32000,-32000", "--window-size=1366,900"]
    proc = subprocess.Popen(browser_cmd(f"--remote-debugging-port={port}", *hide, "about:blank"))
    try:
        with sync_playwright() as p:
            for _ in range(50):
                try: b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}"); break
                except Exception: time.sleep(0.3)
            else: raise SystemExit("Không nối được trình duyệt (profile đang mở ở cửa sổ khác? đóng nó trước)")
            yield b.contexts[0]
    finally:
        proc.terminate()
        with contextlib.suppress(Exception): proc.wait(10)

def cmd_login(a):
    subprocess.Popen(browser_cmd("--new-window", *SITES.values()))
    print("Đăng nhập Facebook / TikTok / X (tài khoản PHỤ) trong cửa sổ Edge vừa mở, xong thì ĐÓNG cửa sổ.")
    lock = PROFILE / "lockfile"
    for _ in range(60):
        if lock.exists(): break
        time.sleep(0.5)
    while lock.exists():
        try: lock.unlink(); break
        except OSError: time.sleep(2)
    print("Đã lưu đăng nhập trong", PROFILE)

def cmd_check(a):
    with browser() as ctx: cookies = ctx.cookies()
    for site, (dom, keys) in AUTH.items():
        ok = any(c["domain"].lstrip(".").endswith(dom) and c["name"] in keys for c in cookies)
        print(f"{site:<9} {'✅ đã đăng nhập' if ok else '— chưa đăng nhập'}")

def human_scroll(pg, n):
    for _ in range(n):
        pg.mouse.wheel(0, random.randint(900, 1600)); time.sleep(random.uniform(1.5, 3.5))

def cmd_tiktok(a):
    """Trang tìm kiếm tự gọi /api/search/... trả JSON (item_list: desc, createTime, stats, author) → bắt từ lưu lượng mạng."""
    got = {}
    def on_resp(r):
        if not re.search(r"/api/(search/(general|item)/full|recommend/item_list|explore/item_list)", r.url): return
        with contextlib.suppress(Exception):
            j = r.json()
            for x in j.get("item_list") or [d.get("item") for d in j.get("data", []) if d.get("item")]:
                if not x or not x.get("id"): continue
                st, au = x.get("stats") or {}, x.get("author") or {}
                got[x["id"]] = {"platform": "tiktok", "url": f"https://www.tiktok.com/@{au.get('uniqueId', '')}/video/{x['id']}",
                    "text": x.get("desc", ""), "author": au.get("uniqueId"),
                    "published": dt.datetime.fromtimestamp(x["createTime"], VN).isoformat() if x.get("createTime") else None,
                    "metrics": {"views": st.get("playCount"), "likes": st.get("diggCount"), "comments": st.get("commentCount"), "shares": st.get("shareCount")}}
    with browser() as ctx:
        pg = ctx.new_page(); pg.on("response", on_resp)
        url = "https://www.tiktok.com/explore" if a.query == "explore" else f"https://www.tiktok.com/search/video?q={requests.utils.quote(a.query)}"
        pg.goto(url, wait_until="domcontentloaded", timeout=60000); time.sleep(random.uniform(4, 7)); human_scroll(pg, a.scrolls)
        if not got: pg.screenshot(path=str(KIT / "tmp_tiktok_check.png")); print("  ⚠ không bắt được dữ liệu — xem tmp_tiktok_check.png (chưa đăng nhập / captcha?)")
    items = sorted(got.values(), key=lambda x: -(x["metrics"]["views"] or 0))
    for x in items[:15]: print(f"  {x['metrics']['views'] or 0:>11,}  {(x['published'] or '')[:10]}  @{x['author'] or '':<18} {x['text'][:60]}")
    save("tiktok", a.query, items)

FB_JS = r"""() => {
  const out = [];
  for (const art of document.querySelectorAll('[role="article"], div[aria-posinset]')) {
    const links = [...art.querySelectorAll('a[href]')].map(a => a.href.split('?')[0]);
    const url = links.find(h => /\/(posts|videos|reel|watch|permalink|story\.php|share\/[pvr])\b/.test(h)) || '';
    const text = (art.querySelector('[data-ad-preview="message"], [data-ad-comet-preview="message"]') || art).innerText || '';
    const author = (art.querySelector('h2 a, h3 a, strong a, a[role="link"] strong') || {}).innerText || null;
    const aria = [...art.querySelectorAll('[aria-label]')].map(e => e.getAttribute('aria-label')).join(' | ');
    out.push({ url, text: text.slice(0, 1500), author, aria: aria.slice(0, 800) });
  }
  return out;
}"""

def fb_metrics(t):
    """Đếm tương tác hiện trên bài (tiếng Việt/Anh): '1,2K bình luận', '345 lượt chia sẻ', 'Tất cả cảm xúc: 2,3K', '12K lượt xem'."""
    g = lambda pat: num((re.search(pat, t, re.I) or [None, None])[1])
    return {"views": g(r"([\d.,]+\s*(?:K|N|Tr|M)?)\s*(?:lượt xem|views)"), "likes": g(r"(?:Tất cả cảm xúc|All reactions):?\s*([\d.,]+\s*(?:K|N|Tr|M)?)"),
            "comments": g(r"([\d.,]+\s*(?:K|N|Tr|M)?)\s*(?:bình luận|comments?)"), "shares": g(r"([\d.,]+\s*(?:K|N|Tr|M)?)\s*(?:lượt chia sẻ|shares?)")}

def cmd_facebook(a):
    seen, items = set(), []
    with browser() as ctx:
        pg = ctx.new_page()
        for tab in ("posts", "videos"):
            pg.goto(f"https://www.facebook.com/search/{tab}?q={requests.utils.quote(a.query)}", wait_until="domcontentloaded", timeout=60000)
            time.sleep(random.uniform(4, 7))
            if "login" in pg.url: raise SystemExit("Facebook: chưa đăng nhập — chạy social_radar.py login")
            human_scroll(pg, a.scrolls)
            for x in pg.evaluate(FB_JS):
                key = x["url"] or x["text"][:80]
                if not x["text"].strip() or key in seen: continue
                seen.add(key)
                items.append({"platform": "facebook", "url": x["url"], "text": x["text"].strip(), "author": x["author"], "published": None,
                              "metrics": fb_metrics(x["text"] + " " + x["aria"]), "tab": tab})
            time.sleep(random.uniform(3, 6))
        if not items: pg.screenshot(path=str(KIT / "tmp_facebook_check.png")); print("  ⚠ không đọc được bài — xem tmp_facebook_check.png")
    for x in items[:15]: print(f"  {x['tab']:<6} 💬{x['metrics']['comments'] or '-':>6} ↗{x['metrics']['shares'] or '-':>6}  {x['author'] or '':<22} {x['text'][:60]!r}")
    save("facebook", a.query, items)

# ------------------------------------------------------------------ báo cáo
def cmd_report(a):
    since = now() - dt.timedelta(hours=a.hours); obs = {}
    for f in sorted(OUT.rglob("*.json")):
        d = json.load(open(f, encoding="utf-8")); t = dt.datetime.fromisoformat(d["observed_at"])
        if t < since: continue
        for x in d["items"]:
            k = x.get("url") or x.get("text")
            if k: obs.setdefault(k, []).append((t, x))
    rows = []
    for k, seq in obs.items():
        seq.sort(key=lambda e: e[0]); (t0, x0), (t1, x1) = seq[0], seq[-1]
        m = lambda x: (x.get("metrics") or {}).get("views") or (x.get("metrics") or {}).get("likes")
        rate = (m(x1) - m(x0)) / max((t1 - t0).total_seconds() / 3600, 1e-6) if len(seq) >= 2 and m(x0) is not None and m(x1) is not None and t1 > t0 else None
        rows.append((rate, m(x1), x1, len(seq)))
    rows.sort(key=lambda r: (r[0] is None, -(r[0] or 0), -(r[1] or 0)))
    print(f"{len(rows)} mục trong {a.hours} giờ · tốc độ chỉ tính khi có ≥ 2 lần đo")
    for rate, val, x, n in rows[:a.top]:
        sp = f"+{rate:,.0f}/giờ" if rate is not None else "1 lần đo"
        print(f"  {x['platform']:<14} {sp:>14}  {val or 0:>11,}  {x['text'][:70]!r}\n  {'':>14} {x.get('url', '')}")

if __name__ == "__main__":
    import sys
    ap = argparse.ArgumentParser(description="Radar mạng xã hội (chỉ đọc)"); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("trends").set_defaults(fn=cmd_trends)
    s = sp.add_parser("youtube"); s.add_argument("query"); s.add_argument("--days", type=float, default=3); s.set_defaults(fn=cmd_youtube)
    sp.add_parser("login").set_defaults(fn=cmd_login); sp.add_parser("check").set_defaults(fn=cmd_check)
    for name, fn in (("tiktok", cmd_tiktok), ("facebook", cmd_facebook)):
        s = sp.add_parser(name); s.add_argument("query", help="từ khoá ('explore' = trang khám phá TikTok)")
        s.add_argument("--scrolls", type=int, default=6); s.set_defaults(fn=fn)
    s = sp.add_parser("report"); s.add_argument("--hours", type=float, default=24); s.add_argument("--top", type=int, default=30); s.set_defaults(fn=cmd_report)
    a = ap.parse_args(); a.fn(a)
