/* Motion HTML cho video tin tức 1920×1080 — chạy với tools/render.py (GSAP timeline "main", seek từng khung).
   Cần nạp trước: gsap.min.js, opentype.min.js, fonts/<Font>.js (chữ viết tay, base64 — file:// không fetch được .ttf).
   Mọi hàm nhận (t, d, …): t = giây bắt đầu, d = thời lượng. Mỗi cảnh/lớp là 1 div có data-start/data-duration
   → render.py tự ẩn/hiện; <video> trong cảnh được render.py tua đúng khung. Xem README.md. */
(function () {
  const SVGNS = 'http://www.w3.org/2000/svg';
  const W = 1920, H = 1080;

  function el(tag, cls, parent, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    if (parent) parent.appendChild(e);
    return e;
  }
  function svg(tag, attrs, parent) {
    const e = document.createElementNS(SVGNS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
  // *chữ vàng*  ~chữ đỏ~  → [{w, cls}] theo từ
  function words(text) {
    const out = []; let mode = '';
    for (const tok of String(text).split(/(\*|~|\s+)/)) {
      if (tok === '*') { mode = mode === 'hot' ? '' : 'hot'; continue; }
      if (tok === '~') { mode = mode === 'red' ? '' : 'red'; continue; }
      if (!tok || /^\s+$/.test(tok)) { if (tok && tok.includes('\n')) out.push({ br: true }); continue; }
      out.push({ w: tok, cls: mode });
    }
    return out;
  }
  function fmt(v, decimals, sep) {   // 6.5 → "6,5" (kiểu Việt), 100000 → "100.000"
    const s = Math.abs(v).toFixed(decimals);
    let [i, f] = s.split('.');
    if (sep !== false) i = i.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return (v < 0 ? '−' : '') + i + (f ? ',' + f : '');
  }
  function rand(seed) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
  // co cỡ chữ tới khi khối không cao quá maxH (sau khi font đã nạp)
  function fit(e, maxH, minPx) {
    let px = parseFloat(getComputedStyle(e).fontSize);
    while (e.scrollHeight > maxH && px > (minPx || 24)) { px -= 2; e.style.fontSize = px + 'px'; }
  }

  const fonts = {};
  function handFont(name) {
    if (!fonts[name]) {
      const b64 = (window.HAND_FONTS || {})[name];
      if (!b64) throw new Error('Thiếu fonts/' + name + '.js');
      const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      fonts[name] = opentype.parse(bin.buffer);
    }
    return fonts[name];
  }

  const PEN = '<svg viewBox="0 0 58 58" width="58" height="58"><g transform="rotate(0)">' +
    '<path d="M6 52 L12 40 L44 8 Q50 3 55 8 Q59 13 54 18 L22 50 Z" fill="#1d1f23" stroke="#fff" stroke-width="2.5" stroke-linejoin="round"/>' +
    '<path d="M6 52 L12 40 L22 50 Z" fill="#ffc531"/><path d="M38 14 L48 24" stroke="#ffc531" stroke-width="4"/></g></svg>';
  const PEN_TIP = [6, 52];

  class Motion {
    constructor(opts = {}) {
      this.root = typeof opts.root === 'string' ? document.querySelector(opts.root) : (opts.root || document.getElementById('root'));
      this.tl = gsap.timeline({ paused: true });
      this.end = 0;
      window.__timelines = window.__timelines || {};
      window.__timelines.main = this.tl;
    }
    _layer(t, d, cls, parent) {
      const e = el('div', 'm-scene' + (cls ? ' ' + cls : ''), parent || this.root);
      if (!parent) { e.dataset.start = t; e.dataset.duration = d; }
      this.end = Math.max(this.end, t + d);
      return e;
    }
    /** cảnh trống có nền tối + vân giấy */
    scene(t, d, { bg = true } = {}) {
      const s = this._layer(t, d);
      if (bg) { el('div', 'm-bg', s); el('div', 'm-grain', s); el('div', 'm-vignette', s); }
      return s;
    }
    _grain(s) { el('div', 'm-grain', s); el('div', 'm-vignette', s); }
    _credit(s, t, credit) {
      if (!credit) return;
      const c = el('div', 'm-credit', s, esc(credit));
      this.tl.fromTo(c, { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: .45, ease: 'power3.out' }, t + .35);
    }
    _kenburns(node, t, d, dir) {
      const m = { in: [1.02, 1.16, 0, 0, 0, 0], out: [1.16, 1.02, 0, 0, 0, 0], left: [1.14, 1.14, 3, -3, 0, 0],
        right: [1.14, 1.14, -3, 3, 0, 0], up: [1.14, 1.14, 0, 0, 3, -3], down: [1.14, 1.14, 0, 0, -3, 3] }[dir] || [1.02, 1.16, 0, 0, 0, 0];
      this.tl.fromTo(node, { scale: m[0], xPercent: m[2], yPercent: m[4] },
        { scale: m[1], xPercent: m[3], yPercent: m[5], duration: d, ease: 'none' }, t);
    }

    /** ảnh tràn khung + Ken Burns. dir: in|out|left|right|up|down. pos: object-position (vd '50% 30%') */
    photo(t, d, src, { dir = 'in', credit, pos, shade = true, fade = .3 } = {}) {
      const s = this._layer(t, d);
      const img = el('img', 'm-media', s); img.src = src; if (pos) img.style.objectPosition = pos;
      this._kenburns(img, t, d, dir);
      if (shade) el('div', 'm-shade', s);
      this._grain(s); this._credit(s, t, credit);
      if (fade) this.tl.fromTo(s, { opacity: 0 }, { opacity: 1, duration: fade, ease: 'none' }, t);
      return s;
    }

    /** video tràn khung (render.py tua khung). offset/end: đoạn dùng (giây trong clip), rate: tốc độ */
    video(t, d, src, { offset = 0, end, rate = 1, credit, push = true, shade = true, fade = .25, dim = 0 } = {}) {
      const s = this._layer(t, d);
      const v = el('video', 'm-media', s); v.muted = true; v.preload = 'auto'; v.setAttribute('playsinline', ''); v.src = src;
      v.dataset.offset = offset; v.dataset.rate = rate; if (end != null) v.dataset.end = end;
      if (push) this.tl.fromTo(v, { scale: 1 }, { scale: 1.06, duration: d, ease: 'none' }, t);
      if (dim) el('div', 'm-scene', s).style.background = `rgba(0,0,0,${dim})`;
      if (shade) el('div', 'm-shade', s);
      this._grain(s); this._credit(s, t, credit);
      if (fade) this.tl.fromTo(s, { opacity: 0 }, { opacity: 1, duration: fade, ease: 'none' }, t);
      return s;
    }

    /** ảnh chụp đầu bài báo: trượt vào, nghiêng, bút dạ quang quét các ô box [x,y,w,h] (tỉ lệ 0–1 của ảnh) */
    headline(t, d, src, { box, boxes, tag, width = 1500, tilt = -2, zoom = 1.1, crop = [0, 0], credit } = {}) {
      const s = this.scene(t, d);
      const paper = el('div', 'm-paper', s); paper.style.width = width + 'px'; paper.style.overflow = 'hidden';
      const inner = el('div', '', paper); inner.style.position = 'relative';
      const img = el('img', '', inner); img.src = src;
      // crop [trên, dưới] = phần cắt bỏ (tỉ lệ chiều cao ảnh) — ảnh chụp bài báo hay có dải trắng/quảng cáo phía trên
      const doCrop = () => { const k = width * img.naturalHeight / img.naturalWidth;
        inner.style.marginTop = -crop[0] * k + 'px'; inner.style.marginBottom = -crop[1] * k + 'px'; };
      if (crop[0] || crop[1]) { if (img.complete && img.naturalWidth) doCrop(); else img.addEventListener('load', doCrop); }
      const list = boxes || (box ? [box] : []);
      const tl = this.tl;
      tl.fromTo(paper, { xPercent: -50, yPercent: -50, y: 900, rotation: tilt - 6, scale: .92 },
        { y: 0, rotation: tilt, scale: 1, duration: .85, ease: 'power3.out' }, t);
      tl.fromTo(paper, { scale: 1 }, { scale: zoom, duration: Math.max(.1, d - .85), ease: 'none', immediateRender: false }, t + .85);
      list.forEach((b, i) => {
        const hl = el('div', 'm-hl', inner);
        Object.assign(hl.style, { left: b[0] * 100 + '%', top: b[1] * 100 + '%', width: b[2] * 100 + '%', height: b[3] * 100 + '%' });
        tl.fromTo(hl, { scaleX: 0 }, { scaleX: 1, duration: .55, ease: 'power2.inOut' }, t + 1.0 + i * .6);
      });
      if (tag) {
        const g = el('div', 'm-tag', s, esc(tag));
        tl.fromTo(g, { xPercent: -110, opacity: 0 }, { xPercent: 0, opacity: 1, duration: .5, ease: 'power3.out' }, t + .3);
      }
      this._credit(s, t, credit);
      return s;
    }

    /** chữ viết tay hiện theo nét + đầu bút chạy theo. Đè lên cảnh khác: đặt t trong cửa sổ cảnh đó (lớp riêng) hoặc parent.
        x,y: điểm neo (align left|center|right), y là đường chân chữ dòng đầu. '\n' xuống dòng. */
    handwrite(t, d, text, { x = W / 2, y = H / 2, size = 110, color = '#ffc531', font = 'Pangolin', align = 'center',
      write, stroke, pen = true, parent, lineHeight = 1.25, shadow = true, backing = 'rgba(0,0,0,.55)' } = {}) {
      const s = this._layer(t, d, '', parent);
      const f = handFont(font);
      const sv = svg('svg', { class: 'm-draw', viewBox: `0 0 ${W} ${H}`, width: W, height: H }, s);
      if (shadow) sv.style.filter = 'drop-shadow(0 6px 10px rgba(0,0,0,.55))';
      const sw = stroke || Math.max(1.5, size / 40);
      const glyphs = [];
      String(text).split('\n').forEach((line, li) => {
        const wpx = f.getAdvanceWidth(line, size);
        const x0 = align === 'center' ? x - wpx / 2 : align === 'right' ? x - wpx : x;
        f.getPaths(line, x0, y + li * size * lineHeight, size).forEach(p => {
          const dd = p.toPathData(2); if (!dd || dd.length < 4) return;
          // nền tối dày phía sau từng nét → đọc được khi viết đè lên ảnh/video rối mắt
          const back = backing ? svg('path', { d: dd, fill: backing, 'fill-opacity': 0, stroke: backing, 'stroke-width': sw + size / 9,
            'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, sv) : null;
          const path = svg('path', { d: dd, fill: color, 'fill-opacity': 0, stroke: color, 'stroke-width': sw,
            'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, sv);
          const len = path.getTotalLength();
          for (const q of [back, path]) if (q) { q.style.strokeDasharray = len; q.style.strokeDashoffset = len; }
          glyphs.push({ path, back, len });
        });
      });
      const total = glyphs.reduce((a, g) => a + g.len, 0) || 1;
      const T = write || Math.min(d * .75, .55 + glyphs.length * .085);
      let cur = t;
      const penEl = pen ? el('div', 'm-pen', s, PEN) : null; let penPos = null;
      if (penEl) this.tl.fromTo(penEl, { opacity: 0 }, { opacity: 1, duration: .12 }, t);
      glyphs.forEach(g => {
        const gd = T * g.len / total;
        const both = g.back ? [g.back, g.path] : [g.path];
        this.tl.fromTo(both, { strokeDashoffset: g.len }, { strokeDashoffset: 0, duration: gd, ease: 'none' }, cur);
        this.tl.fromTo(both, { attr: { 'fill-opacity': 0 } }, { attr: { 'fill-opacity': 1 }, duration: Math.max(.12, gd * .8), ease: 'none' }, cur + gd * .5);
        if (penEl) {
          const k = Math.max(3, Math.min(10, Math.round(g.len / 60)));
          for (let i = 0; i <= k; i++) {
            const pt = g.path.getPointAtLength(g.len * i / k), nx = pt.x - PEN_TIP[0], ny = pt.y - PEN_TIP[1];
            const from = penPos || { x: nx, y: ny };
            this.tl.fromTo(penEl, { x: from.x, y: from.y }, { x: nx, y: ny, duration: i ? gd / k : .04, ease: 'none', immediateRender: !penPos },
              cur + (i ? gd * (i - 1) / k : 0));
            penPos = { x: nx, y: ny };
          }
        }
        cur += gd;
      });
      if (penEl && penPos) this.tl.fromTo(penEl, { opacity: 1, x: penPos.x, y: penPos.y }, { opacity: 0, x: penPos.x + 60, y: penPos.y - 40, duration: .3, immediateRender: false }, cur + .05);
      return s;
    }

    /** nét vẽ tay: circle (khoanh), underline (gạch chân), arrow (mũi tên x,y → x+w,y+h), cross (gạch chéo) */
    scribble(t, d, { type = 'circle', x, y, w, h, color = '#e63b2e', width = 9, draw = .6, seed = 7, parent } = {}) {
      const s = this._layer(t, d, '', parent);
      const sv = svg('svg', { class: 'm-draw', viewBox: `0 0 ${W} ${H}`, width: W, height: H }, s);
      sv.style.filter = 'drop-shadow(0 4px 6px rgba(0,0,0,.4))';
      const r = rand(seed); const ds = [];
      if (type === 'circle') {
        const cx = x + w / 2, cy = y + h / 2; let p = '';
        for (let i = 0; i <= 64; i++) {
          const a = -2.2 + i / 64 * Math.PI * 2 * 1.12, j = 1 + (r() - .5) * .06 + i / 64 * .05;
          p += (i ? 'L' : 'M') + (cx + Math.cos(a) * w / 2 * 1.08 * j).toFixed(1) + ' ' + (cy + Math.sin(a) * h / 2 * 1.15 * j).toFixed(1);
        }
        ds.push(p);
      } else if (type === 'underline') {
        ds.push(`M${x} ${y + 4} Q${x + w * .3} ${y - 6} ${x + w * .55} ${y + 2} T${x + w} ${y - 4}`);
        ds.push(`M${x + w * .08} ${y + 18} Q${x + w * .5} ${y + 8} ${x + w * .9} ${y + 16}`);
      } else if (type === 'arrow') {
        const x2 = x + w, y2 = y + h, mx = (x + x2) / 2 - h * .25, my = (y + y2) / 2 + w * .12;
        ds.push(`M${x} ${y} Q${mx} ${my} ${x2} ${y2}`);
        const ang = Math.atan2(y2 - my, x2 - mx), L = 46;
        ds.push(`M${x2 - L * Math.cos(ang - .5)} ${y2 - L * Math.sin(ang - .5)} L${x2} ${y2} L${x2 - L * Math.cos(ang + .5)} ${y2 - L * Math.sin(ang + .5)}`);
      } else if (type === 'cross') {
        ds.push(`M${x} ${y} L${x + w} ${y + h}`); ds.push(`M${x + w} ${y} L${x} ${y + h}`);
      }
      let cur = t;
      ds.forEach((p, i) => {
        const path = svg('path', { d: p, fill: 'none', stroke: color, 'stroke-width': width, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, sv);
        const len = path.getTotalLength(); path.style.strokeDasharray = len;
        const dur = draw * (i ? .45 : 1);
        this.tl.fromTo(path, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: dur, ease: 'power1.inOut' }, cur);
        cur += dur;
      });
      return s;
    }

    /** số lớn chạy from → to. suffix nhỏ màu vàng; decimals; label dưới; kicker trên; photo: ảnh nền mờ */
    counter(t, d, from, to, { suffix = '', prefix = '', decimals = 0, label = '', kicker = '', sub = '', count = 1.6, photo, color } = {}) {
      const s = this.scene(t, d);
      if (photo) {
        const img = el('img', 'm-media', s); img.src = photo; img.style.opacity = .28; img.style.filter = 'grayscale(.4) blur(2px)';
        this._kenburns(img, t, d, 'in'); this._grain(s);
      }
      const c = el('div', 'm-center', s);
      const k = kicker ? el('div', 'm-kicker', c, esc(kicker)) : null;
      const n = el('div', 'm-num', c);
      const span = el('span', '', n, prefix + fmt(from, decimals)); if (color) span.style.color = color;
      if (suffix) el('small', '', n, esc(suffix));
      const lab = label ? el('div', 'm-label', c, esc(label)) : null;
      const sb = sub ? el('div', 'm-sub', c, esc(sub)) : null;
      const tl = this.tl;
      if (k) tl.fromTo(k, { opacity: 0, y: -20, letterSpacing: '18px' }, { opacity: 1, y: 0, letterSpacing: '6px', duration: .6, ease: 'power3.out' }, t + .05);
      tl.fromTo(n, { opacity: 0, scale: .7, filter: 'blur(14px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)', duration: .5, ease: 'power3.out' }, t + .15);
      const o = { v: from };
      tl.fromTo(o, { v: from }, { v: to, duration: Math.min(count, d * .6), ease: 'power2.out',
        onUpdate: () => { span.textContent = prefix + fmt(o.v, decimals); } }, t + .25);
      if (lab) tl.fromTo(lab, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: .5, ease: 'power3.out' }, t + .6);
      if (sb) tl.fromTo(sb, { opacity: 0 }, { opacity: 1, duration: .5 }, t + 1.1);
      tl.fromTo(c, { scale: 1 }, { scale: 1.05, duration: d, ease: 'none' }, t);
      return s;
    }

    /** 2 cột: before mọc lên, after mọc tới mức before rồi tụt xuống (thể hiện giảm). delta: chữ ghi mức thay đổi */
    compare(t, d, { title = '', before, after, unit = '%', decimals = 1, delta = '', max } = {}) {
      const s = this.scene(t, d);
      const tl = this.tl;
      if (title) { const ti = el('div', 'm-title', s, esc(title)); fit(ti, 200); tl.fromTo(ti, { opacity: 0, y: -30 }, { opacity: 1, y: 0, duration: .5, ease: 'power3.out' }, t); }
      const M = max || Math.max(before.value, after.value) * 1.08;
      const wrap = el('div', 'm-bars', s);
      const floor = el('div', 'm-floor', s);
      tl.fromTo(floor, { scaleX: 0 }, { scaleX: 1, duration: .5, ease: 'power2.out' }, t + .1);
      const mk = (o, col) => {
        const b = el('div', 'm-bar', wrap);
        const val = el('div', 'val', b); val.style.color = col;
        const vs = el('span', '', val, fmt(0, decimals)); el('span', '', val, unit).style.fontSize = '.55em';
        const fill = el('div', 'fill', b); fill.style.background = col; fill.style.height = (o.value / M * 450) + 'px';
        el('div', 'lab', b, esc(o.label || ''));
        return { b, vs, fill };
      };
      const A = mk(before, before.color || '#e63b2e'), B = mk(after, after.color || '#ffc531');
      const hA = before.value / M * 450, hB = after.value / M * 450;
      const oa = { v: 0 }, ob = { v: 0 };
      tl.fromTo(A.fill, { height: 0 }, { height: hA, duration: .9, ease: 'power3.out' }, t + .4);
      tl.fromTo(oa, { v: 0 }, { v: before.value, duration: .9, ease: 'power3.out', onUpdate: () => A.vs.textContent = fmt(oa.v, decimals) }, t + .4);
      // after: mọc lên ngang before rồi tụt
      tl.fromTo(B.fill, { height: 0 }, { height: hA, duration: .8, ease: 'power3.out' }, t + 1.0);
      tl.fromTo(ob, { v: 0 }, { v: before.value, duration: .8, ease: 'power3.out', onUpdate: () => B.vs.textContent = fmt(ob.v, decimals) }, t + 1.0);
      const drop = t + 2.0;
      tl.fromTo(B.fill, { height: hA }, { height: hB, duration: .9, ease: 'power2.inOut', immediateRender: false }, drop);
      tl.fromTo(ob, { v: before.value }, { v: after.value, duration: .9, ease: 'power2.inOut', immediateRender: false, onUpdate: () => B.vs.textContent = fmt(ob.v, decimals) }, drop);
      if (delta) {
        const dl = el('div', 'm-delta', s, '▼ ' + esc(delta));
        tl.fromTo(dl, { opacity: 0, y: -30, scale: .8 }, { opacity: 1, y: 0, scale: 1, duration: .45, ease: 'back.out(2)' }, drop + .6);
      }
      return s;
    }

    /** mốc thời gian: [{date, text, img?}] — đường được vẽ dần, mỗi mốc bật ra lần lượt */
    timeline(t, d, items, { title = '', lineY } = {}) {
      const s = this.scene(t, d);
      const tl = this.tl;
      const hasImg = items.some(i => i.img);
      const Y = lineY || (hasImg ? 640 : 560);
      if (title) { const ti = el('div', 'm-title', s, esc(title)); tl.fromTo(ti, { opacity: 0, y: -30 }, { opacity: 1, y: 0, duration: .5 }, t); }
      const line = el('div', 'm-tl-line', s), prog = el('div', 'm-tl-prog', s);
      line.style.top = prog.style.top = Y + 'px';
      tl.fromTo(line, { scaleX: 0, transformOrigin: '0 50%' }, { scaleX: 1, duration: .6, ease: 'power2.out' }, t + .15);
      const L = 150, R = W - 150, n = items.length;
      const step = Math.max(.5, (d - 1.2) / n);
      tl.set(prog, { scaleX: 0, transformOrigin: '0 50%' }, t); let px = 0;
      items.forEach((it, i) => {
        const x = n === 1 ? W / 2 : L + 180 + (R - L - 360) * i / (n - 1);
        const at = t + .6 + i * step;
        const box = el('div', 'm-tl-item', s); box.style.left = x + 'px'; box.style.top = (Y - 53) + 'px';
        const dot = el('div', 'm-tl-dot', box);
        const date = el('div', 'm-tl-date', box, esc(it.date)); date.style.top = '-96px'; date.style.bottom = 'auto';
        const tx = el('div', 'm-tl-text', box, esc(it.text));
        tl.fromTo(prog, { scaleX: px }, { scaleX: (x - L) / (R - L), duration: .45, ease: 'power2.inOut', immediateRender: false }, at - .35); px = (x - L) / (R - L);
        tl.fromTo(dot, { scale: 0 }, { scale: 1, duration: .4, ease: 'back.out(3)' }, at);
        tl.fromTo(date, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: .4, ease: 'power3.out' }, at + .05);
        tl.fromTo(tx, { opacity: 0, y: -16 }, { opacity: 1, y: 0, duration: .4, ease: 'power3.out' }, at + .15);
        if (it.img) {
          const im = el('img', 'm-tl-img', box); im.src = it.img; im.style.top = '-330px'; im.style.bottom = 'auto'; im.style.height = '210px';
          tl.fromTo(im, { opacity: 0, y: 40, rotation: i % 2 ? 3 : -3 }, { opacity: 1, y: 0, rotation: i % 2 ? 1.5 : -1.5, duration: .5, ease: 'power3.out' }, at + .1);
        }
      });
      tl.fromTo(prog, { scaleX: px }, { scaleX: 1, duration: .5, ease: 'power2.inOut', immediateRender: false }, t + .6 + (n - 1) * step + .5);
      return s;
    }

    /** trích dẫn: chữ hiện theo từ; *từ vàng*; photo: ảnh người nói bên trái */
    quote(t, d, text, who, { photo, credit, size } = {}) {
      const s = this.scene(t, d);
      const tl = this.tl;
      if (photo) {
        const ph = el('div', 'm-qphoto', s); const img = el('img', '', ph); img.src = photo;
        this._kenburns(img, t, d, 'in');
        tl.fromTo(ph, { clipPath: 'inset(0 100% 0 0)' }, { clipPath: 'inset(0 0% 0 0)', duration: .7, ease: 'power3.inOut' }, t);
      }
      const q = el('div', 'm-quote' + (photo ? ' with-photo' : ''), s);
      const mk = el('div', 'm-qmark', q, '“');
      const tx = el('div', 'm-qtext', q); if (size) tx.style.fontSize = size + 'px';
      const spans = words(text).filter(x => !x.br).map(x => el('span', x.cls, tx, esc(x.w)));
      const wh = who ? el('div', 'm-who', q, esc(who)) : null;
      fit(tx, photo ? 640 : 600, 36);
      tl.fromTo(mk, { opacity: 0, scale: .4, rotation: -20 }, { opacity: 1, scale: 1, rotation: 0, duration: .5, ease: 'back.out(2)' }, t + .1);
      const T = Math.min(d * .55, spans.length * .11);
      spans.forEach((sp, i) => tl.fromTo(sp, { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: .3, ease: 'power2.out' }, t + .35 + T * i / spans.length));
      if (wh) tl.fromTo(wh, { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: .45, ease: 'power3.out' }, t + .45 + T);
      this._credit(s, t, credit);
      return s;
    }

    /** chữ lớn đập vào theo từ (kinetic). *vàng* ~đỏ~. kicker: nhãn vàng phía trên */
    bigtitle(t, d, text, { kicker, size, photo, credit } = {}) {
      const s = this.scene(t, d);
      const tl = this.tl;
      if (photo) {
        const img = el('img', 'm-media', s); img.src = photo; img.style.opacity = .35; img.style.filter = 'grayscale(.5)';
        this._kenburns(img, t, d, 'in'); this._grain(s);
      }
      const b = el('div', 'm-big', s); if (size) b.style.fontSize = size + 'px';
      words(text).forEach(x => x.br ? el('br', '', b) : el('span', 'w ' + x.cls, b, esc(x.w)));
      fit(b, 700, 60);
      const ws = [...b.querySelectorAll('.w')];
      ws.forEach((w, i) => tl.fromTo(w, { opacity: 0, scale: 1.9, filter: 'blur(14px)' },
        { opacity: 1, scale: 1, filter: 'blur(0px)', duration: .42, ease: 'power4.out' }, t + .1 + i * .11));
      tl.fromTo(b, { scale: 1 }, { scale: 1.05, duration: d, ease: 'none' }, t);
      if (kicker) {
        const k = el('div', 'm-big-kicker', s, esc(kicker));
        const top = b.offsetTop - b.offsetHeight / 2 - 90;   // ngay trên khối chữ
        k.style.top = Math.max(60, top) + 'px';
        tl.fromTo(k, { clipPath: 'inset(0 100% 0 0)' }, { clipPath: 'inset(0 0% 0 0)', duration: .45, ease: 'power3.out' }, t);
      }
      this._credit(s, t, credit);
      return s;
    }
    chapter(t, d, label, text, opts = {}) { return this.bigtitle(t, d, text, { kicker: label, ...opts }); }

    /** tên + chức danh (đè lên cảnh đang chạy) */
    lowerThird(t, d, name, role, { parent } = {}) {
      const s = this._layer(t, d, '', parent);
      const box = el('div', 'm-l3', s);
      const bar = el('div', 'bar', box), n = el('div', 'name', box, esc(name)), r = role ? el('div', 'role', box, esc(role)) : null;
      const tl = this.tl;
      tl.fromTo(bar, { scaleY: 0 }, { scaleY: 1, duration: .3, ease: 'power3.out' }, t);
      tl.fromTo(n, { clipPath: 'inset(0 100% 0 0)' }, { clipPath: 'inset(0 0% 0 0)', duration: .5, ease: 'power3.out' }, t + .15);
      if (r) tl.fromTo(r, { clipPath: 'inset(0 100% 0 0)' }, { clipPath: 'inset(0 0% 0 0)', duration: .5, ease: 'power3.out' }, t + .3);
      tl.fromTo(box, { opacity: 1, x: 0 }, { opacity: 0, x: -40, duration: .3, immediateRender: false }, t + d - .35);
      return s;
    }

    /** nhãn góc phải trên suốt đoạn t..t+d */
    bug(t, d, text) {
      const s = this._layer(t, d); s.style.zIndex = 50; s.style.pointerEvents = 'none';
      el('div', 'm-bug', s, '<i></i>' + esc(text));
      return s;
    }

    /** chuyển cảnh quanh mốc t: wipe (2 tấm vàng/đỏ quét), flash (chớp trắng), whip (nhoè + vệt quét) */
    transition(t, type = 'wipe', { colors = ['#ffc531', '#e63b2e'] } = {}) {
      const D = type === 'flash' ? .5 : .7, t0 = t - D / 2;
      const s = this._layer(t0, D, 'm-tr'); s.style.zIndex = 100;
      const tl = this.tl;
      if (type === 'wipe') {
        colors.forEach((c, i) => {
          const p = el('div', 'panel', s); p.style.background = c;
          tl.fromTo(p, { x: 0 }, { x: W * 2.6, duration: D * .85, ease: 'power2.inOut' }, t0 + i * D * .1);
        });
      } else if (type === 'flash') {
        const f = el('div', 'flash', s);
        tl.fromTo(f, { opacity: 0 }, { opacity: .95, duration: D * .3, ease: 'power2.in' }, t0);
        tl.fromTo(f, { opacity: .95 }, { opacity: 0, duration: D * .7, ease: 'power2.out', immediateRender: false }, t0 + D * .3);
      } else if (type === 'whip') {
        const st = el('div', 'streak', s);
        tl.fromTo(st, { xPercent: -100, opacity: 0 }, { xPercent: 100, opacity: 1, duration: D, ease: 'power3.inOut' }, t0);
        tl.fromTo(this.root, { filter: 'blur(0px)' }, { filter: 'blur(18px)', duration: D / 2, ease: 'power2.in', immediateRender: false }, t0);
        tl.fromTo(this.root, { filter: 'blur(18px)' }, { filter: 'blur(0px)', duration: D / 2, ease: 'power2.out', immediateRender: false }, t0 + D / 2);
      }
      return s;
    }

    /** gọi cuối cùng: ghi tổng thời lượng vào khung gốc (render.py đọc data-duration) */
    finish(total) {
      const T = total || this.end;
      this.root.dataset.duration = T.toFixed(3);
      this.tl.set({}, {}, T);
      return T;
    }
  }

  /** chờ font Be Vietnam Pro nạp xong rồi dựng (để đo/co chữ chính xác) */
  Motion.ready = function (fn) {
    const loads = ['700 40px "Be Vietnam Pro"', '800 40px "Be Vietnam Pro"'].map(f => document.fonts.load(f, 'Ấắễ'));
    return Promise.all(loads).then(() => fn());
  };
  Motion.fmt = fmt;
  window.Motion = Motion;
})();
