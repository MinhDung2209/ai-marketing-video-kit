"""Bộ quay màn hình cho video demo sản phẩm (screendemo).

Điều khiển cửa sổ "Chrome quay video" (profile riêng + cổng debug, xem KIT/docs/12) — Chrome thật, NGƯỜI DÙNG tự đăng nhập
sẵn, nên ít bị bot detector. Thao tác như người: con trỏ đi đường cong, gõ từng phím có nhịp, dừng đọc trước khi bấm.
Ghi hình bằng CDP screencast (khung hình thật của trang) → MP4 30 fps + file mốc thời gian từng bước (marks.json).

Thường không gọi trực tiếp: viết kịch bản thao tác dạng dữ liệu (shots.json) rồi chạy shoot.py. Gọi tay:
    from rec import Session
    with Session("D:/.../assets/screen/h2", width=720, height=1080) as s:
        s.goto("https://www.google.com.vn")
        s.click("textarea[name=q]"); s.type("xuất khẩu sầu riêng 2026"); s.press("Enter")
        s.mark("ket-qua")            # ghi mốc để dựng/khớp giọng
"""
import base64, json, math, os, random, subprocess, sys, time, pathlib
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from config import cfg as _cfg
CDP =os.environ.get("REC_CDP") or _cfg().get("cdp", "http://127.0.0.1:9333")
FFMPEG = os.environ.get("FFMPEG") or _cfg().get("ffmpeg") or "ffmpeg"

# Con trỏ giả vẽ trong trang: screencast không chụp con trỏ thật của hệ điều hành.
CURSOR_JS = r"""
(() => {
  if (window.__recCursor) return;
  const mk = () => {
    if (!document.body || document.getElementById('__rec_cursor')) return;
    const c = document.createElement('div'); c.id = '__rec_cursor';
    c.innerHTML = '<svg width="34" height="40" viewBox="0 0 17 20"><path d="M1 1 L1 16 L5 12.5 L8 19 L10.6 17.8 L7.7 11.5 L13 11.5 Z" fill="#111" stroke="#fff" stroke-width="1.3" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, {position:'fixed', left:'0', top:'0', zIndex:2147483647, pointerEvents:'none',
      transform:'translate(var(--x,-100px),var(--y,-100px))', filter:'drop-shadow(0 2px 3px rgba(0,0,0,.35))'});
    const r = document.createElement('div'); r.id = '__rec_ripple';
    Object.assign(r.style, {position:'fixed', width:'44px', height:'44px', marginLeft:'-22px', marginTop:'-22px', borderRadius:'50%',
      border:'3px solid rgba(79,70,229,.9)', background:'rgba(79,70,229,.18)', zIndex:2147483646, pointerEvents:'none', opacity:'0'});
    document.body.append(r, c);
    const p = window.__recPos; if (p) { c.style.setProperty('--x', p[0]+'px'); c.style.setProperty('--y', p[1]+'px'); }
  };
  window.__recCursor = true;
  window.__recMove = (x, y) => { window.__recPos = [x, y]; mk(); const c = document.getElementById('__rec_cursor');
    if (c) { c.style.setProperty('--x', x+'px'); c.style.setProperty('--y', y+'px'); } };
  window.__recClick = (x, y) => { mk(); const r = document.getElementById('__rec_ripple'); if (!r) return;
    r.style.left = x+'px'; r.style.top = y+'px';
    r.animate([{opacity:1, transform:'scale(.4)'}, {opacity:0, transform:'scale(1.6)'}], {duration:520, easing:'ease-out'}); };
  document.addEventListener('DOMContentLoaded', mk); mk();
})();
"""


class Session:
    def __init__(self, out_dir, width=720, height=1080, scale=1.5, url=None):
        self.out = pathlib.Path(out_dir).resolve(); self.out.mkdir(parents=True, exist_ok=True)
        self.w, self.h, self.scale = width, height, scale
        self.frames, self.marks, self.pos = [], [], (width * 0.6, height * 0.3)
        self.events = []   # thao tác thật (click/gõ/cuộn) → engine tự đặt SFX khớp hình
        self.t0 = None

    # ---------- mở / đóng ----------
    def __enter__(self):
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.connect_over_cdp(CDP)
        self.ctx = self.browser.contexts[0]
        self.page = self.ctx.new_page()                  # tab riêng để quay, không đụng tab người dùng
        self.page.add_init_script(CURSOR_JS)
        # chặn quảng cáo NGAY khi trang bắt đầu dựng (hide_ads sau khi tải thì bản quay đã kịp dính quảng cáo)
        self.page.add_init_script("(() => { const css = %s; const add = () => { if (document.getElementById('__rec_noads')) return;"
            " const st = document.createElement('style'); st.id = '__rec_noads'; st.textContent = css; (document.head || document.documentElement).append(st); };"
            " add(); document.addEventListener('DOMContentLoaded', add); })();" % json.dumps(self.AD_CSS))
        self.cdp = self.ctx.new_cdp_session(self.page)
        self.cdp.send("Emulation.setDeviceMetricsOverride",
                      {"width": self.w, "height": self.h, "deviceScaleFactor": self.scale, "mobile": False})
        self.cdp.on("Page.screencastFrame", self._on_frame)
        return self

    def __exit__(self, *exc):
        try: self.stop()
        finally:
            try: self.page.close()
            except Exception: pass
            self.pw.stop()

    # ---------- ghi hình ----------
    def _on_frame(self, ev):
        self.frames.append((ev["metadata"]["timestamp"], ev["data"]))
        try: self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
        except Exception: pass

    def start(self):
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92,
                      "maxWidth": int(self.w * self.scale), "maxHeight": int(self.h * self.scale), "everyNthFrame": 1})
        self.t0 = time.time(); self.mark("start")

    def stop(self):
        if self.t0 is None: return
        self.mark("end")
        try: self.cdp.send("Page.stopScreencast")
        except Exception: pass
        self.t0 = None
        self._encode()

    def mark(self, name, **info):
        """Ghi mốc (giây tính từ đầu bản quay) — build.py dùng để khớp cảnh với câu đọc."""
        t = round(time.time() - (self.t0 or time.time()), 3)
        entry = {"name": name, "t": t, **info}
        if "element_text" not in entry:
            elem_text = ""
            if hasattr(self, "page") and self.page:
                try:
                    elem_text = self.page.evaluate("""() => {
                        const el = window.__recSpan;
                        if (!el || !el.isConnected) return "";
                        return (el.innerText || el.textContent || "").trim();
                    }""") or ""
                except Exception:
                    elem_text = ""
            if elem_text:
                entry["element_text"] = elem_text
        if "page_text_path" not in entry:
            page_path = ""
            if hasattr(self, "page") and self.page and hasattr(self, "out") and self.out:
                try:
                    dom_text = self.page.evaluate("() => document.body ? (document.body.innerText || '') : ''") or ""
                    dom_dir = pathlib.Path(self.out) / "_dom"
                    dom_dir.mkdir(parents=True, exist_ok=True)
                    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name))
                    idx = len(self.marks)
                    dom_file = dom_dir / f"{idx:03d}_{safe_name}.txt"
                    dom_file.write_text(dom_text, encoding="utf-8")
                    page_path = str(dom_file.relative_to(self.out).as_posix())
                except Exception:
                    page_path = ""
            if page_path:
                entry["page_text_path"] = page_path
        self.marks.append(entry)
        print(f"  [{t:6.2f}s] {name}", flush=True)

    def _ev(self, kind, **info):
        """Ghi 1 thao tác (cùng đồng hồ với mark) — engine dùng để đặt tiếng click/gõ phím/cuộn đúng khung hình."""
        if self.t0 is None: return
        self.events.append({"k": kind, "t": round(time.time() - self.t0, 3), **info})

    def snap(self, name):
        """Ảnh tĩnh để duyệt bằng mắt."""
        self.page.screenshot(path=str(self.out / f"{name}.png"))

    def _encode(self):
        if not self.frames: print("không có khung hình"); return
        fdir = self.out / "_frames"; fdir.mkdir(exist_ok=True)
        lines, frames = ["ffconcat version 1.0"], sorted(self.frames, key=lambda f: f[0])
        base = frames[0][0]
        for i, (ts, data) in enumerate(frames):
            f = fdir / f"{i:05d}.jpg"; f.write_bytes(base64.b64decode(data))
            nxt = frames[i + 1][0] if i + 1 < len(frames) else ts + 0.5
            lines += [f"file '{f.as_posix()}'", f"duration {max(nxt - ts, 0.001):.4f}"]
        lines.append(f"file '{(fdir / f'{len(frames)-1:05d}.jpg').as_posix()}'")
        lst = self.out / "_frames.ffconcat"; lst.write_text("\n".join(lines), encoding="utf-8")
        # mốc theo đồng hồ khung hình đầu tiên
        shift = base - (self.frames_wall0 if hasattr(self, "frames_wall0") else base)
        mp4 = self.out / "screen.mp4"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-vf", "fps=30,scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "16",
                        "-pix_fmt", "yuv420p", str(mp4)], check=True)
        (self.out / "marks.json").write_text(json.dumps({"first_frame_wall": base, "marks": self.marks, "events": self.events},
                                             ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✅ {mp4} · {len(frames)} khung · {frames[-1][0]-base:.1f}s")

    # ---------- thao tác như người ----------
    def sleep(self, sec):
        """Chờ NHƯNG vẫn bơm sự kiện Playwright → screencast tiếp tục nhận khung (time.sleep làm đứng hình)."""
        if sec > 0: self.page.wait_for_timeout(sec * 1000)

    def wait(self, a=0.6, b=None):
        self.sleep(a if b is None else random.uniform(a, b))

    def goto(self, url, wait="domcontentloaded"):
        self.page.goto(url, wait_until=wait); self._sync_cursor(); self.wait(0.8)

    def _sync_cursor(self):
        try: self.page.evaluate("([x,y]) => window.__recMove && window.__recMove(x,y)", list(self.pos))
        except Exception: pass

    def move_to(self, x, y, dur=None):
        x0, y0 = self.pos; d = math.hypot(x - x0, y - y0)
        dur = dur or min(1.1, 0.35 + d / 1400)
        steps = max(12, int(dur * 60))
        # đường cong Bezier lệch nhẹ như tay người
        cx = (x0 + x) / 2 + random.uniform(-0.18, 0.18) * d; cy = (y0 + y) / 2 + random.uniform(-0.18, 0.18) * d
        for i in range(1, steps + 1):
            t = i / steps; e = t * t * (3 - 2 * t)          # ease in-out
            px = (1 - e) ** 2 * x0 + 2 * (1 - e) * e * cx + e * e * x
            py = (1 - e) ** 2 * y0 + 2 * (1 - e) * e * cy + e * e * y
            self.page.mouse.move(px, py)
            self.page.evaluate("([x,y]) => window.__recMove && window.__recMove(x,y)", [px, py])
            self.sleep(dur / steps)
        self.pos = (x, y)

    def box(self, selector, nth=0):
        loc = self.loc(selector, nth); loc.wait_for(state="visible")
        return loc.bounding_box()

    def hover(self, selector, nth=0):
        b = self.box(selector, nth)
        self.move_to(b["x"] + b["width"] * random.uniform(0.35, 0.6), b["y"] + b["height"] * random.uniform(0.4, 0.6))
        return b

    def click(self, selector, nth=0, think=(0.25, 0.5)):
        self.hover(selector, nth); self.wait(*think)
        x, y = self.pos
        self.page.evaluate("([x,y]) => window.__recClick && window.__recClick(x,y)", [x, y])
        self._ev("click"); self.page.mouse.click(x, y); self._sync_cursor(); self.wait(0.3)

    def type(self, text, cps=(9, 15)):
        self._ev("type_start", n=len(text))
        for ch in text:
            self.page.keyboard.type(ch)
            self.sleep(1 / random.uniform(*cps) + (0.18 if ch == " " and random.random() < 0.25 else 0))
        self._ev("type_end")

    def press(self, key):
        self._ev("key", key=key); self.page.keyboard.press(key); self.wait(0.4)

    def scroll(self, dy, dur=1.0):
        steps = max(10, int(dur * 40)); self._ev("scroll", dur=dur, dy=dy)
        # lăn chuột khi ô <input type=number> đang được chọn sẽ ĐỔI SỐ trong ô (clip 02: gõ 20 → bị lăn còn 1) → bỏ chọn trước
        self.page.evaluate("() => { const a = document.activeElement; if (a && a.type === 'number') a.blur(); }")
        for i in range(steps):
            self.page.mouse.wheel(0, dy / steps); self.sleep(dur / steps)
        self.wait(0.3)

    def loc(self, target, nth=0):
        """target: CSS selector (str) hoặc Locator của Playwright."""
        return (self.page.locator(target) if isinstance(target, str) else target).nth(nth)

    def scroll_to(self, target, nth=0, frac=0.35, dur=1.2):
        """Cuộn mượt cho phần tử nằm ở ~35% chiều cao màn hình (như người lăn chuột)."""
        b = self.loc(target, nth).bounding_box()
        if b: self.scroll(b["y"] - self.h * frac, dur)

    def mark_text(self, text, scope="body", name=None, scroll=True, color="#FDE047", ring="#EF4444", hold=1.8, ink=True):
        """Tô bút dạ quang + khoanh vòng đỏ ĐÚNG cụm chữ `text` (lần xuất hiện đầu tiên còn nhìn thấy).
        Trả về khung (x, y, w, h — toạ độ màn hình quay) và ghi vào marks.json để lúc dựng phóng sát vào đó.
        ink=False: KHÔNG vẽ gì, chỉ cuộn tới + ghi khung để camera phóng vào (dùng `focus`).
        Luật (người duyệt 04/11/2026: "mark hơi spam"): mỗi cảnh chỉ 1–2 lần khoanh có mực, đúng con số lời đọc nhấn;
        còn lại dùng focus()."""
        for attempt in range(4):                      # trang báo hay tự tải lại (quảng cáo/redirect) → thử lại
            try:
                return self._mark_text(text, scope, name, scroll, color, ring, hold, ink)
            except Exception as e:
                if "context was destroyed" not in str(e) and "navigation" not in str(e) or attempt == 3: raise
                self.settle()

    AD_CSS = """iframe:not([src*="youtube"]), ins.adsbygoogle, [id^="google_ads"], [id*="-ads"], [id*="_ads"], [class*="ads-"],
      [class*="-ads"], [class*="banner"], [class*="qc-"], [class*="advert"], [id*="banner"], [class*="sticky-ad"],
      .zone-ads, .box-ads, .ads, .ad, [id^="adnzone"], [id^="ssppagebid"],
      [id*="popup"][style*="fixed"], [class*="topbanner"], img[src*="admicro"], a[href*="admicro"] { display:none !important; }"""

    def hide_ads(self):
        """Ẩn quảng cáo trên trang báo để khung hình sạch (chỉ trong tab quay)."""
        try: self.page.add_style_tag(content=self.AD_CSS)
        except Exception: pass

    def settle(self, timeout=12):
        """Chờ trang ổn định: load xong + không đổi URL trong 1,5s."""
        try: self.page.wait_for_load_state("load", timeout=timeout * 1000)
        except Exception: pass
        url = None
        for _ in range(int(timeout / 0.5)):
            if url == self.page.url: break
            url = self.page.url; self.sleep(1.5)
        self._sync_cursor()

    def _mark_text(self, text, scope, name, scroll, color, ring, hold, ink=True):
        # B1: tìm ĐÚNG nút chữ (bỏ phần ẩn), bọc <span>, cuộn chính nó vào giữa màn hình
        found = self.page.evaluate("""([text, scope]) => {
          const root = document.querySelector(scope) || document.body;
          const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {acceptNode: n => {
            const el = n.parentElement; if (!el || el.closest('script,style,noscript,head')) return NodeFilter.FILTER_REJECT;
            const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden' || !el.getClientRects().length) return NodeFilter.FILTER_REJECT;
            return n.data.includes(text) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP; }});
          const n = w.nextNode(); let span;
          if (n) {
            const i = n.data.indexOf(text), range = document.createRange(); range.setStart(n, i); range.setEnd(n, i + text.length);
            // thẻ riêng (không phải <span>): CSS của trang kiểu ".mm-stat span{font-size:12px}" sẽ không áp vào → số giữ nguyên cỡ/màu (clip 07: "15" bị teo)
            span = document.createElement('rec-hl'); range.surroundContents(span);
          } else {   // cụm chữ bị tách qua nhiều thẻ (vd số in đậm) → lấy phần tử NHỎ NHẤT chứa trọn cụm
            const norm = x => x.replace(/\\s+/g, ' ');
            const all = [...root.querySelectorAll('*')].filter(e => e.getClientRects().length && !e.closest('script,style') && norm(e.innerText || '').includes(text));
            if (!all.length) return false;
            span = all.reduce((a, b) => (b.innerText.length < a.innerText.length ? b : a));
            // phần tử khối (ô bảng/div) → bọc NỘI DUNG vào <rec-hl> để mực/vòng ôm sát chữ, không kéo ngang cả hàng (clip 08: "120 KG")
            if (getComputedStyle(span).display !== 'inline') { const w2 = document.createElement('rec-hl'); while (span.firstChild) w2.appendChild(span.firstChild); span.appendChild(w2); span = w2; }
          }
          window.__recSpan = span;
          // bảng rộng: cuộn NGANG khung chứa cho ô nằm giữa (dọc để Python tự cuộn mượt)
          let p = span.parentElement; while (p && p !== document.body) { if (p.scrollWidth > p.clientWidth + 4 && getComputedStyle(p).overflowX !== 'visible') { const r = span.getBoundingClientRect(), pr = p.getBoundingClientRect(); p.scrollBy({left: (r.left + r.width / 2) - (pr.left + pr.width / 2), behavior: 'smooth'}); break; } p = p.parentElement; }
          return true; }""", [text, scope])
        if not found: raise RuntimeError(f"không thấy chữ trên trang: {text!r}")
        self.wait(0.6)                                   # chờ cuộn ngang (nếu có)
        if scroll:
            b = self.page.evaluate("() => { const r = window.__recSpan.getBoundingClientRect(); return {y: r.top}; }")
            if b["y"] < self.h * 0.15 or b["y"] > self.h * 0.7: self.scroll(b["y"] - self.h * 0.4, 1.1)
            self.wait(0.5)
        # B2: tô dạ quang + vẽ vòng đỏ theo vị trí HIỆN TẠI (gắn vào trang, cuộn theo nội dung)
        if not ink:
            box = self.page.evaluate("""() => { const s = window.__recSpan, r = s.getClientRects(); const b = r.length > 1 ? r[r.length-1] : s.getBoundingClientRect();
              return {x: b.left, y: b.top, w: b.width, h: b.height}; }""")
            self.mark(name or f"focus:{text}", box=box, vw=self.w, vh=self.h, ink=False); self.wait(hold); return box
        box = self.page.evaluate("""([color, ring, hold]) => {
          const span = window.__recSpan;
          // += giữ style inline sẵn có của phần tử (cỡ chữ/màu số to); = sẽ xoá → số bị teo nhỏ (clip 07: "15")
          span.style.cssText += `;background:linear-gradient(transparent 12%, ${color} 12%, ${color} 92%, transparent 92%);background-size:0% 100%;background-repeat:no-repeat;transition:background-size .5s ease-out;border-radius:4px;padding:0 2px`;
          requestAnimationFrame(() => span.style.backgroundSize = '100% 100%');
          const rects = span.getClientRects(); const b = rects.length > 1 ? rects[rects.length - 1] : span.getBoundingClientRect();
          const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
          const W = b.width + 36, H = b.height + 26;
          svg.setAttribute('width', W); svg.setAttribute('height', H);
          // vòng tròn BÁM THEO chữ từng khung hình (trang tự xê dịch / cuộn khung con vẫn khoanh đúng chỗ)
          Object.assign(svg.style, {position:'fixed', left:(b.left-18)+'px', top:(b.top-13)+'px', zIndex:2147483645, pointerEvents:'none', overflow:'visible'});
          const follow = () => { if (!svg.isConnected) return; const rs = span.getClientRects(); const r = rs.length > 1 ? rs[rs.length - 1] : span.getBoundingClientRect();
            svg.style.left = (r.left - 18) + 'px'; svg.style.top = (r.top - 13) + 'px'; requestAnimationFrame(follow); };
          requestAnimationFrame(follow);
          const e = document.createElementNS('http://www.w3.org/2000/svg', 'ellipse');
          e.setAttribute('cx', W/2); e.setAttribute('cy', H/2); e.setAttribute('rx', W/2-3); e.setAttribute('ry', H/2-3);
          e.setAttribute('fill', 'none'); e.setAttribute('stroke', ring); e.setAttribute('stroke-width', '4'); e.setAttribute('stroke-linecap', 'round');
          e.setAttribute('transform', `rotate(-2 ${W/2} ${H/2})`);
          const L = Math.PI * (W + H) / 2 * 1.05; e.style.strokeDasharray = L; e.style.strokeDashoffset = L;
          e.style.transition = 'stroke-dashoffset .6s ease-in-out .35s';
          svg.append(e); document.body.append(svg);
          requestAnimationFrame(() => requestAnimationFrame(() => e.style.strokeDashoffset = 0));
          setTimeout(() => svg.remove(), hold * 1000 + 2500);
          return {x: b.left, y: b.top, w: b.width, h: b.height}; }""", [color, ring, hold])
        self.mark(name or f"mark:{text}", box=box, vw=self.w, vh=self.h)
        self.wait(hold)
        return box

    def focus(self, text, scope="body", name=None, scroll=True, hold=1.0):
        """Chỉ cuộn tới cụm chữ + ghi khung cho camera phóng vào — không tô, không khoanh."""
        return self.mark_text(text, scope, name, scroll, hold=hold, ink=False)

    def highlight(self, target, nth=0, color="#F59E0B", hold=1.2):
        """Khoanh vùng (giống video guide) — vẽ khung sáng quanh phần tử."""
        self.loc(target, nth).evaluate(f"""el => {{
          const b = el.getBoundingClientRect(); const d = document.createElement('div');
          Object.assign(d.style, {{position:'fixed', left:(b.left-8)+'px', top:(b.top-6)+'px', width:(b.width+16)+'px',
            height:(b.height+12)+'px', border:'4px solid {color}', borderRadius:'12px', zIndex:2147483645,
            pointerEvents:'none', boxShadow:'0 0 0 6px rgba(245,158,11,.25)'}});
          d.animate([{{opacity:0, transform:'scale(1.08)'}}, {{opacity:1, transform:'scale(1)'}}], {{duration:300, easing:'ease-out'}});
          document.body.append(d); setTimeout(() => d.remove(), {int(hold*1000)});
        }}""")
        self.wait(hold)


if __name__ == "__main__":
    # Thử nhanh: mở Google, chụp 1 ảnh — kiểm tra kết nối tới Chrome quay video.
    out = sys.argv[1] if len(sys.argv) > 1 else "_probe"
    with Session(out) as s:
        s.goto("https://www.google.com.vn/?hl=vi"); s.snap("probe")
    print("ok", out)

