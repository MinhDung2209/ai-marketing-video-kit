# 08 · Kiểm tra trước khi đăng

## 1. Kiểm bằng máy (bắt buộc — đừng tin "chắc là ổn")
```bash
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height -of compact video.mp4   # 1080x1920, h264 + aac
ffmpeg -hide_banner -i video.mp4 -af volumedetect -vn -f null - 2>&1 | grep -E "mean_volume|max_volume"   # đỉnh ≤ -1 dB, TB ~ -16..-20 dB
for t in 1 10 20 30 45; do ffmpeg -v error -y -ss $t -i video.mp4 -frames:v 1 -vf scale=270:480 f_$t.png; done   # xem từng khung
```
Cắt khung **từ chính file MP4** (không phải từ bản xem thử) — bắt được lỗi chỉ xuất hiện khi render đủ.

## 2. Checklist nội dung
- [ ] Nghe hết: không đọc sai, không lẫn lời đạo diễn; tên thương hiệu rõ; câu nào đọc "không kèm đạo diễn" (⚠) đã nghe lại
- [ ] Hoạt ảnh khớp lời (thẻ/chữ bật lên đúng lúc nói)
- [ ] Mặt KOL đồng bộ mọi cảnh; tay chân / đồ vật trong clip không "dịch chuyển"; chữ trong ảnh AI đúng chính tả
- [ ] Logo là file thật; số liệu khớp nguồn + nhãn "ví dụ thật"; không lộ email/SĐT/dữ liệu cá nhân
- [ ] Không SFX chói tai (người duyệt đã nghe); giọng rõ, nhạc không lấn; không đứng hình "sượng" ở cuối
- [ ] Phụ đề đúng chính tả, không tách đôi cụm từ, không che nút/chữ chính
- [ ] Xem trên **điện thoại thật**: chừa vùng an toàn TikTok/Reels (trên ~200px, dưới ~300px, phải ~140px)

## 3. Xuất bản
- Tên file: `<thuong-hieu>-<so>-<ti-le>.mp4` (vd `stradevn-ad-v2-9x16.mp4`).
- Lưu kèm BRIEF.md + voice.json + credits.md để làm bản A/B / bản sau.
- Chạy quảng cáo A/B hook: giữ thân, thay 3–5 giây đầu (docs/03).
- Dọn plenxai: xoá ảnh/clip thử & bản trùng; **giữ ảnh gốc nhân vật** (mỏ neo tham chiếu).

## Hai bản cho Facebook Reels và TikTok (thêm 05/10/2026)
- **Vùng an toàn** (khung 1080×1920): TikTok che trên ~240px, dưới ~660px, cột nút phải ~180px từ y 840; Reels che trên
  ~210px, dưới ~670px. Khung mẫu có khoá `safe` trong `scenes.json` + 2 bộ sẵn `_safe_presets.reels / .tiktok`
  (tiêu đề từ y 270, phụ đề y 1150 tối đa ~30 ký tự/dòng, nút kêu gọi dời lên 290px).
- **Làm 2 bản rẻ:** chép thư mục dự án, chỉ đổi hook (V1, có thể V2) + `safe`, rồi
  `tts_script.py voice.json audio --only V1,V2` (câu khác giữ nguyên) → `make_video.py <dự án> --from build --out <tên>.mp4`.
- **Hook theo nền tảng:** Reels (người xem lớn tuổi hơn, chủ DN) → câu hỏi kết quả + sản phẩm thật ngay giây 0;
  TikTok → nỗi đau đời thường, kiểu "native", nói như bạn bè. Không mở bằng logo; 21–40s.
- Ví dụ thật: StradeVn v3 (`projects/stradevn/ad-v3-reels`, `ad-v3-tiktok` — ngoài kit).
