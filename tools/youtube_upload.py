"""Đăng video lên YouTube ở chế độ RIÊNG TƯ (xem thử trước khi công khai) + mô tả có chương + thumbnail — YouTube Data API v3.

API KHÔNG tạo được "bản nháp" như YouTube Studio → "private" là gần nhất (chỉ chủ kênh xem). Project Google chưa được
duyệt (OAuth app ở chế độ Testing) thì video tải qua API bị khoá ở private, và token đăng nhập hết hạn sau 7 ngày.

Cài đặt 1 lần (Google Cloud Console của bạn):
  APIs & Services → bật "YouTube Data API v3" → Credentials → OAuth client ID loại "Desktop app"
  → OAuth consent screen: thêm Gmail của kênh vào "Test users".
  kit/.env:  YT_CLIENT_ID=…apps.googleusercontent.com   YT_CLIENT_SECRET=GOCSPX-…   (không commit)
  Client loại "Web application" thay vì Desktop: thêm http://127.0.0.1:8976 vào Authorized redirect URIs
  và YT_REDIRECT_PORT=8976 vào kit/.env (không thì Google báo 400 redirect_uri_mismatch).
Dùng:
  python <kit>/tools/youtube_upload.py login                 → mở trình duyệt chọn kênh, lưu token vào kit/.youtube_token.json
  python <kit>/tools/youtube_upload.py thumb <video> <ra.jpg> --t 3 --text "LIVING IN CALIFORNIA"
  python <kit>/tools/youtube_upload.py upload <video> --title "…" [--desc mo_ta.txt] [--chapters youtube_chapters.txt]
                                           [--credits audio_credits.json] [--thumb anh.jpg] [--tags a,b] [--privacy private]
Chương: YouTube tự tạo từ mốc trong mô tả — mốc đầu "00:00", ≥ 3 mốc, mỗi chương ≥ 10 giây.
Thumbnail: kênh phải xác minh số điện thoại; JPG ≤ 2 MB, 1280×720.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, http.server, json, os, pathlib, secrets, subprocess, threading, time, urllib.parse, webbrowser
import requests

KIT = pathlib.Path(__file__).resolve().parent.parent
TOKEN = KIT / ".youtube_token.json"   # không commit (.gitignore)
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube"

def env(name, default=None):
    if os.environ.get(name): return os.environ[name]
    for f in (pathlib.Path(".env"), KIT / ".env"):
        if f.exists():
            for ln in f.read_text(encoding="utf-8").splitlines():
                k, _, v = ln.partition("=")
                if k.strip() == name and v.strip(): return v.strip()
    if default is not None: return default
    raise SystemExit(f"Thiếu {name} trong kit/.env (xem hướng dẫn đầu file)")

def login(_=None):
    """OAuth cho ứng dụng desktop: mở trình duyệt → Google chuyển về http://127.0.0.1:<cổng> kèm mã → đổi lấy token."""
    cid, sec = env("YT_CLIENT_ID"), env("YT_CLIENT_SECRET"); state = secrets.token_urlsafe(16); got = {}
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state: got.update({k: v[0] for k, v in q.items()})
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write("Xong — quay lại cửa sổ lệnh.".encode() if "code" in got else "Lỗi đăng nhập.".encode())
        def log_message(self, *x): pass
    # client "Desktop app": cổng nào cũng được. Client "Web application": Google chỉ nhận đúng URI đã khai báo
    # (lỗi 400 redirect_uri_mismatch) → thêm http://127.0.0.1:8976 vào Authorized redirect URIs + YT_REDIRECT_PORT=8976
    srv = http.server.HTTPServer(("127.0.0.1", int(env("YT_REDIRECT_PORT", "0"))), H); redirect = f"http://127.0.0.1:{srv.server_port}"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "access_type": "offline", "prompt": "consent", "state": state})
    print("Mở trình duyệt để chọn tài khoản/kênh YouTube…\nNếu không tự mở, dán link này:\n" + url, flush=True)
    webbrowser.open(url)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    for _ in range(600):
        if got: break
        time.sleep(0.5)
    srv.shutdown()
    if "code" not in got: raise SystemExit(f"Không nhận được mã đăng nhập: {got.get('error', 'hết giờ')}")
    r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "code": got["code"], "client_id": cid, "client_secret": sec, "redirect_uri": redirect, "grant_type": "authorization_code"})
    if not r.ok:   # 401 invalid_client = client secret không khớp Client ID (secret của client khác / đã bị đổi)
        raise SystemExit(f"Đổi mã lấy token lỗi {r.status_code}: {r.text[:300]} — invalid_client: lấy lại secret ĐÚNG của client "
                         f"{cid[:20]}… (Credentials → mở client → Client secrets)")
    tok = r.json(); tok["expires_at"] = time.time() + tok["expires_in"] - 60
    TOKEN.write_text(json.dumps(tok), encoding="utf-8")
    ch = api("GET", "channels", params={"part": "snippet", "mine": "true"}).json().get("items", [])
    print("Đã đăng nhập kênh:", ", ".join(c["snippet"]["title"] for c in ch) or "(không thấy kênh)")

def access_token():
    if not TOKEN.exists(): raise SystemExit("Chưa đăng nhập: python youtube_upload.py login")
    tok = json.loads(TOKEN.read_text(encoding="utf-8"))
    if time.time() > tok.get("expires_at", 0):
        r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
            "client_id": env("YT_CLIENT_ID"), "client_secret": env("YT_CLIENT_SECRET"),
            "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"})
        if not r.ok: raise SystemExit(f"Token hết hạn (app Testing: 7 ngày) — chạy lại login. {r.text[:200]}")
        tok.update(r.json()); tok["expires_at"] = time.time() + tok["expires_in"] - 60
        TOKEN.write_text(json.dumps(tok), encoding="utf-8")
    return tok["access_token"]

def api(method, path, upload=False, **kw):
    base = "https://www.googleapis.com/upload/youtube/v3/" if upload else "https://www.googleapis.com/youtube/v3/"
    hdr = {"Authorization": f"Bearer {access_token()}", **kw.pop("headers", {})}
    r = requests.request(method, base + path, headers=hdr, timeout=kw.pop("timeout", 60), **kw)
    if r.status_code >= 400 and r.status_code != 308: raise SystemExit(f"YouTube {r.status_code}: {r.text[:500]}")
    return r

def description(a):
    parts = [pathlib.Path(a.desc).read_text(encoding="utf-8").strip()] if a.desc else []
    if a.chapters:
        ch = pathlib.Path(a.chapters).read_text(encoding="utf-8").strip().splitlines()
        if len(ch) >= 3 and ch[0].startswith("00:00"): parts.append("Chapters:\n" + "\n".join(ch))
        else: print(f"  (chương không hiện: cần ≥ 3 mốc, mốc đầu 00:00 — đang có {len(ch)})")
    if a.credits:   # nhạc/SFX CC BY bắt buộc ghi công; CC0 ghi cũng không sao
        cr = json.load(open(a.credits, encoding="utf-8"))
        lines = [f"♪ \"{c['title']}\" — {c['creator']} ({'CC0' if c['license'] == 'cc0' else 'CC ' + c['license'].upper() + ' ' + c.get('license_version', '')}) {c['page']}"
                 for c in cr if c["license"] != "cc0"]
        if lines: parts.append("Music:\n" + "\n".join(lines))
    return "\n\n".join(parts)[:5000]

def upload(a):
    f = pathlib.Path(a.video); size = f.stat().st_size
    lang = getattr(a, "lang", None) or "vi"   # ngôn ngữ tiêu đề/mô tả + ngôn ngữ âm thanh → YouTube xếp đúng người xem, phụ đề tự động đúng tiếng
    meta = {"snippet": {"title": a.title[:100], "description": description(a), "categoryId": a.category,
                        "defaultLanguage": lang, "defaultAudioLanguage": lang,
                        "tags": [t.strip() for t in a.tags.split(",") if t.strip()] if a.tags else []},
            "status": {"privacyStatus": a.privacy, "selfDeclaredMadeForKids": False}}
    r = api("POST", "videos", upload=True, params={"uploadType": "resumable", "part": "snippet,status"}, json=meta,
            headers={"X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})
    loc, pos, CH = r.headers["Location"], 0, 64 << 20
    with open(f, "rb") as fh:
        while pos < size:   # tải từng khúc 64 MB; rớt mạng → hỏi server đã nhận tới đâu rồi tải tiếp
            fh.seek(pos); data = fh.read(CH); end = pos + len(data) - 1
            try:
                r = requests.put(loc, data=data, timeout=600, headers={"Authorization": f"Bearer {access_token()}",
                                                                       "Content-Range": f"bytes {pos}-{end}/{size}"})
            except requests.exceptions.RequestException as e:
                print(f"  rớt mạng ({str(e)[:80]}) — tải tiếp", flush=True); time.sleep(5)
                r = requests.put(loc, timeout=60, headers={"Authorization": f"Bearer {access_token()}", "Content-Range": f"bytes */{size}"})
            if r.status_code == 308:
                rng = r.headers.get("Range"); pos = int(rng.split("-")[1]) + 1 if rng else 0
            elif r.ok: pos = size
            else: raise SystemExit(f"Tải lên lỗi {r.status_code}: {r.text[:300]}")
            print(f"  {pos / size * 100:5.1f}%  ({pos / 1e6:.0f}/{size / 1e6:.0f} MB)", flush=True)
    vid = r.json()["id"]
    print(f"Đã tải lên ({a.privacy}): https://youtu.be/{vid}  ·  Studio: https://studio.youtube.com/video/{vid}/edit")
    if a.thumb:
        t = api("POST", "thumbnails/set", upload=True, params={"videoId": vid}, data=open(a.thumb, "rb").read(),
                headers={"Content-Type": "image/jpeg"}, timeout=120)
        print("  thumbnail: đã đặt" if t.ok else f"  thumbnail lỗi: {t.text[:200]}")
    return vid

def update(a):
    """Sửa video đã đăng (title/mô tả/tag/chế độ/thumbnail). File video thì YouTube không cho thay — phải đăng mới."""
    v = api("GET", "videos", params={"id": a.id, "part": "snippet,status"}).json()["items"]
    if not v: raise SystemExit(f"không thấy video {a.id}")
    sn, st = v[0]["snippet"], v[0]["status"]
    if a.title: sn["title"] = a.title[:100]
    if a.desc or a.chapters or a.credits: sn["description"] = description(a)
    if a.tags is not None: sn["tags"] = [t.strip() for t in a.tags.split(",") if t.strip()]
    if a.privacy: st["privacyStatus"] = a.privacy
    body = {"id": a.id, "snippet": {k: sn[k] for k in ("title", "description", "categoryId", "tags", "defaultLanguage", "defaultAudioLanguage") if k in sn},
            "status": {k: st[k] for k in ("privacyStatus", "selfDeclaredMadeForKids", "embeddable", "license", "publicStatsViewable") if k in st}}
    api("PUT", "videos", params={"part": "snippet,status"}, json=body)
    print(f"đã sửa ({st['privacyStatus']}): https://youtu.be/{a.id} · {sn['title']}")
    if a.thumb:
        t = api("POST", "thumbnails/set", upload=True, params={"videoId": a.id}, data=open(a.thumb, "rb").read(),
                headers={"Content-Type": "image/jpeg"}, timeout=120)
        print("  thumbnail: đã đặt" if t.ok else f"  thumbnail lỗi: {t.text[:200]}")

def thumb(a):
    """Khung hình ở giây --t, thu về 1280×720, chữ to viền đậm (đọc được trên điện thoại) → JPG ≤ 2 MB."""
    from PIL import Image, ImageDraw, ImageFont
    tmp = pathlib.Path(a.out).with_suffix(".frame.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(a.t), "-i", a.video, "-frames:v", "1",
                    "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720", str(tmp)], check=True)
    im = Image.open(tmp).convert("RGB"); d = ImageDraw.Draw(im); tmp.unlink()
    if a.text:
        font = None
        for name in ("arialbd.ttf", "seguisb.ttf", "DejaVuSans-Bold.ttf"):
            try: font = ImageFont.truetype(name, 96); break
            except OSError: pass
        lines = a.text.split("|"); y = 720 - 70 - 110 * len(lines)
        for ln in lines:
            w = d.textlength(ln, font=font); d.text(((1280 - w) / 2, y), ln, font=font, fill="white", stroke_width=8, stroke_fill="black"); y += 110
    q = 92
    while True:
        im.save(a.out, "JPEG", quality=q)
        if os.path.getsize(a.out) <= 2 << 20 or q < 50: break
        q -= 8
    print("đã tạo", a.out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("login").set_defaults(fn=login)
    u = sp.add_parser("upload"); u.add_argument("video"); u.add_argument("--title", required=True); u.add_argument("--desc")
    u.add_argument("--chapters"); u.add_argument("--credits"); u.add_argument("--thumb"); u.add_argument("--tags")
    u.add_argument("--privacy", default="private", choices=("private", "unlisted", "public")); u.add_argument("--category", default="19")   # 19 = Travel & Events
    u.add_argument("--lang", default="vi", help="ngôn ngữ video (defaultLanguage + defaultAudioLanguage)")
    u.set_defaults(fn=upload)
    e = sp.add_parser("update"); e.add_argument("id"); e.add_argument("--title"); e.add_argument("--desc")
    e.add_argument("--chapters"); e.add_argument("--credits"); e.add_argument("--thumb"); e.add_argument("--tags")
    e.add_argument("--privacy", choices=("private", "unlisted", "public")); e.set_defaults(fn=update)
    t = sp.add_parser("thumb"); t.add_argument("video"); t.add_argument("out"); t.add_argument("--t", type=float, default=3)
    t.add_argument("--text", help="chữ trên ảnh; '|' để xuống dòng"); t.set_defaults(fn=thumb)
    a = ap.parse_args(); a.fn(a)
