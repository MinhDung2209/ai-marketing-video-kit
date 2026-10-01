# 07 · Dựng cảnh & render

## 1. Hai cách dựng
| | Khung mẫu (`templates/video-project`) | Tuỳ biến (như `examples/stradevn-ad-v2`) |
| --- | --- | --- |
| Viết gì | `scenes.json` | `index.src.html` (HTML + GSAP) + `build.py` |
| Cảnh | 4 kiểu có sẵn: media · screenshot · logo · cta | Tự do: xé giấy, gõ từng ký tự, lia bảng, đếm số, bảng liên hệ… |
| Hợp với | Video nhanh, người mới | Video "xịn", người biết chút HTML/JS (hoặc để Claude Code làm) |

## 2. Định dạng trang dựng (theo HyperFrames)
- Khung gốc: `<div id="root" data-composition-id="main" data-width="1080" data-height="1920" data-duration="54">`.
- Mỗi cảnh / phụ đề / đoạn clip: phần tử có `data-start` + `data-duration` (giây, **tính từ đầu video**) → chỉ hiện
  trong khoảng đó.
- MỘT timeline GSAP dừng sẵn: `const tl = gsap.timeline({paused:true}); … window.__timelines["main"] = tl;`
- Chuyển động bằng `tl.fromTo(el, {từ}, {tới, duration, ease}, <giây>)`.
- Clip: `<video src="assets/clips/x.mp4" muted playsinline preload="auto" data-rate="0.75" data-offset="3.9" data-end="6">`
  - `data-rate`: tốc độ (0.75 = chậm) · `data-offset`: bắt đầu từ giây này của clip · `data-end`: dừng ở giây này
    (bỏ đoạn lỗi); hết đoạn thì giữ khung cuối.
  - Nối 2 đoạn clip trong 1 cảnh: 2 `<div data-start data-duration>` con, mỗi cái 1 `<video>` (ví dụ cảnh C9 của v2).

## 3. build.py — mọi mốc suy ra từ giọng đọc
- Đọc `audio/timing.json` → mốc cắt cảnh = giữa 2 câu liên tiếp.
- Mốc hoạt ảnh bám lời: dùng **`speech_segments.py`** (đo khoảng lặng → các cụm nói thật). Bài học v2: ước lượng theo số
  ký tự lệch ~1,2s → người duyệt thấy "thẻ không khớp lời"; đo khoảng lặng thì khớp:
  ```python
  from speech_segments import segments
  s2 = segments("audio/V2.mp3")      # [(0.28,1.38), (1.68,3.17), (3.85,6.0), (6.21,6.8) "lật tờ khai", (7.15,8.33) "copy…", …]
  ```
  In ra để đối chiếu: `python <kit>/tools/speech_segments.py audio/V2.mp3`.
- Sinh phụ đề (`captions.py`, theo cụm, ~46 ký tự/cụm, cắt ở `[short pause]`/dấu phẩy) và `cues.json` (hiệu ứng theo mốc).
- Luật hay vấp (đã gặp):
  - `fromTo` của tween bắt đầu muộn áp giá trị "from" ngay từ đầu → dùng `immediateRender:false` (lỗi chớp trắng).
  - Phần tử vừa là `.clip` (`inset:0`) vừa định vị riêng → bị kéo giãn → đặt `inset:auto`.
  - Video trong khung bo góc + transform không bị cắt góc → thêm `clip-path: inset(0 round …)`.
  - Chữ đè ảnh → chia cột rõ ràng; nút bị phụ đề che → phụ đề ở y 1480–1720, đặt nút cao hơn.
  - Font: nhúng `@font-face` (file woff2 đi kèm) để tiếng Việt đủ dấu trên mọi máy.

## 4. Render — `render.py`
```bash
python <kit>/tools/render.py . --snap 0.5,5,12,30          # PNG từng mốc → MỞ XEM (bắt buộc trước khi render đủ)
python <kit>/tools/render.py . --fps 30 --audio assets/final_audio.mp3 --out video.mp4
```
Cách chạy: Chrome headless (Playwright) mở `index.html` → mỗi khung: `tl.seek(t)`, bật/tắt phần tử theo data-start/duration,
tua `<video>` tới đúng khung (chờ `seeked`) → chụp JPEG → đẩy thẳng vào FFmpeg (H.264 CRF 18, yuv420p, AAC 192k,
faststart). ~5 phút cho 54s ở 30 fps. GSAP nạp từ CDN (cần mạng).

HyperFrames CLI (`npx hyperframes check` / `render`) cũng chạy được trên cùng định dạng nếu được cấp quyền; `check` hữu ích để
bắt lỗi bố cục/độ tương phản. `render.py` là cách tự chủ, không phụ thuộc gói npm.

## 5. Xuất nhiều tỉ lệ
Đổi `width/height` (1080×1080, 1920×1080) → chỉnh vị trí chữ trong template → build → render. (Chưa làm tự động.)
