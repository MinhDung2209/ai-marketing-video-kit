# Motion HTML — cảnh động cho video tin tức 1920×1080

Render bằng `tools/render.py` (GSAP timeline `main`, tua từng khung; phần tử `data-start/data-duration` tự ẩn/hiện; `<video>` được tua đúng khung).
Không dùng mạng: `gsap.min.js` 3.14.2, `opentype.min.js` 1.3.4, font trong `fonts/` (Be Vietnam Pro 700/800; viết tay Pangolin / Patrick Hand / Itim, đủ dấu tiếng Việt, OFL).

## Khung trang

```html
<link rel="stylesheet" href="motion/motion.css">
<script src="motion/gsap.min.js"></script><script src="motion/opentype.min.js"></script>
<script src="motion/fonts/Pangolin.js"></script>   <!-- font viết tay dạng base64: file:// không fetch được .ttf -->
<script src="motion/motion.js"></script>
<!-- render.py đọc data-duration TRỰC TIẾP từ chữ trong file → ghi số giây cố định, không gán bằng JS -->
<div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="180"></div>
<script>
Motion.ready(() => {                 // chờ font nạp xong (để co chữ đúng) rồi dựng
  const m = new Motion({ root: '#root' });
  m.photo(0, 5, 'media/x/img-01.jpg', { credit: 'Ảnh: SBV · Dân trí' });
  ...
  m.finish(180);
});
</script>
```

Mọi hàm: `(t, d, …)` — `t` giây bắt đầu, `d` thời lượng. Cảnh tạo sau nằm trên. Lớp đè (handwrite, scribble, lowerThird) là lớp trong suốt riêng: đặt `t` nằm trong cửa sổ của cảnh nền.
Chữ đánh dấu: `*vàng*`, `~đỏ~` (bigtitle, quote). Số kiểu Việt: `9,8` / `100.000` (`Motion.fmt`).

## API

| Hàm | Mô tả | Tuỳ chọn |
|---|---|---|
| `photo(t,d,src,o)` | Ảnh tràn khung, Ken Burns, viền tối, vân hạt, nhãn nguồn | `dir` in/out/left/right/up/down · `pos` object-position · `credit` · `shade` · `fade` |
| `video(t,d,src,o)` | Video tràn khung (muted), đẩy chậm 1→1.06 | `offset` `end` (giây trong clip) · `rate` · `credit` · `dim` 0–1 (tối nền để viết chữ lên) · `pos` '30% 50%' (khung dọc: giữ phần nào của clip ngang) · `card` true = khung dọc đặt clip ngang thành thẻ nét giữa trên nền chính clip đó nhoè (không mất chữ/đồ họa), `y` tâm thẻ (mặc định 0,4·H) |
| `headline(t,d,src,o)` | Ảnh chụp bài báo trượt vào nghiêng, zoom chậm, bút dạ quang quét | `boxes` [[x,y,w,h],…] tỉ lệ 0–1 của ảnh GỐC · `crop` [trên,dưới] tỉ lệ cao (cắt dải trắng) · `tag` 'VnExpress · 20/10' · `width` 1500 · `tilt` · `zoom` |
| `handwrite(t,d,text,o)` | Chữ viết tay hiện theo nét, đầu bút chạy theo, nền tối sau nét | `x,y` (y = chân chữ dòng 1) · `align` · `size` · `color` · `font` Pangolin/PatrickHand/Itim · `write` (giây viết) · `backing` (null = tắt) · `\n` xuống dòng |
| `scribble(t,d,o)` | Nét vẽ tay | `type` circle/underline/arrow/cross · `x,y,w,h` · `color` · `width` · `draw` (giây vẽ) · `seed` |
| `counter(t,d,from,to,o)` | Số lớn chạy | `suffix` `prefix` `decimals` `kicker` `label` `sub` `photo` (nền mờ) `color` `count` |
| `compare(t,d,o)` | 2 cột; cột sau mọc ngang cột trước rồi TỤT xuống + nhãn giảm | `title` · `before/after {value,label,color}` · `unit` · `decimals` · `delta` · `max` |
| `timeline(t,d,items,o)` | Mốc ngày: đường vàng chạy dần, chấm bật, ảnh nhỏ | `items` [{date,text,img?}] (≤4–5) · `title` · `lineY` |
| `quote(t,d,text,who,o)` | Trích dẫn, chữ hiện theo từ | `photo` (ảnh trái, mở bằng clip) · `credit` · `size` |
| `bigtitle(t,d,text,o)` / `chapter(t,d,label,text)` | Chữ lớn đập vào theo từ (kinetic) | `kicker` · `photo` (nền mờ) · `size` · `credit` |
| `lowerThird(t,d,name,role)` | Tên + chức danh | — |
| `bug(t,d,text)` | Nhãn góc phải trên | — |
| `transition(t,type)` | Chuyển cảnh quanh mốc `t` (đặt đúng chỗ nối 2 cảnh) | `wipe` (2 tấm vàng/đỏ) · `flash` · `whip` (nhoè + vệt) · `colors` |
| `scene(t,d)` | Cảnh trống nền tối + hạt, tự thêm phần tử | — |
| `finish(total)` | Chốt timeline | — |

## Ví dụ

```js
m.photo(4.2, 5.3, MD + 'dantri-…/img-01.jpg', { credit: 'Ảnh: SBV · Dân trí' });
m.handwrite(5.0, 4.5, 'Họp “nóng” 19/10', { x: 1380, y: 300, size: 120 });
m.scribble(6.4, 3.1, { type: 'underline', x: 1080, y: 345, w: 600 });
m.lowerThird(5.4, 3.9, 'Thống đốc Phạm Đức Ấn', 'Chủ trì cuộc họp với các ngân hàng');
m.transition(9.5, 'flash');
m.headline(9.5, 5, MD + 'vnexpress-5134403/shot.png', { boxes: [[.072,.52,.66,.15]], crop: [.27,.02], tag: 'VnExpress · 20/10' });
m.compare(19, 5, { title: '…', before: { value: 7.3, label: 'Trước 19/10' }, after: { value: 6.8, label: 'Sau 19/10' }, delta: 'giảm 0,5 điểm %' });
```

Demo đầy đủ: `demo/index.html` (40 s, mọi hàm). Kiểm tra:
`python tools/render.py <dự án>/motion/demo --snap 5.6,11.4,22.8` · bản 10 s đã render: `demo10/demo10.mp4` (~2,8 s render / 1 s video).

## Lưu ý
- Ảnh chụp đầu bài của `news_media.py --shot` có dải trắng ~25% phía trên → `crop: [.27, .02]`; toạ độ `boxes` vẫn tính trên ảnh gốc.
- Viết tay ~0,085 s/ký tự (tối đa 75% thời lượng cảnh); câu dài nên tách dòng `\n`, `size` 100–130.
- Viết chữ lên video/ảnh rối: dùng `dim: .4` cho video hoặc đặt chữ vào vùng trời/tường trống.
