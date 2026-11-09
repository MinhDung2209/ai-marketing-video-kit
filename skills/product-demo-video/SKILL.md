---
name: product-demo-video
description: Làm video demo sản phẩm / phần mềm bằng QUAY MÀN HÌNH THAO TÁC THẬT (TikTok/Reels 9:16) — kể chuyện "một ngày làm việc", con trỏ + gõ phím như người, camera phóng đúng con số lời đọc nhắc, giọng Gemini, phụ đề, sticker, nhạc; nhiều bản (đầy đủ / demo cho khách). Dùng khi người dùng nói "làm video demo tính năng", "video quay màn hình sản phẩm", "clip mã HS tiếp theo", "video StradeVn cho mặt hàng …", "làm video như clip sầu riêng cho doanh nghiệp X".
---

# Video demo sản phẩm (screendemo)

KIT = <ĐƯỜNG DẪN TỚI THƯ MỤC kit>   ← cài bằng `python tools/install_skill.py`.
Python: `KIT/.venv/Scripts/python.exe -X utf8`. Cấu hình máy (Chrome, ffmpeg, cổng quay): `KIT/config.json → screendemo`.

## Luật bắt buộc
1. **Không lộ agent / Claude Code** trong video. Không bịa số: mọi số trên hình là số thật trên trang lúc quay.
2. **Người dùng tự đăng nhập** Chrome quay video. Agent không tạo token, mật khẩu, không đọc cookie.
3. **Việc thật = phải hỏi trước**: tạo dữ liệu, chạy tác vụ tốn lượt, gửi thư, thanh toán, xoá. `shoot.py` chặn theo
   `profiles/<dn>/profile.json → safety` — không bao giờ sửa danh sách cấm để "chạy cho qua".
4. Đọc và theo `profile.json → safety.rules` + `story_rules` của doanh nghiệp (vd StradeVn: không gửi email thật, luồng
   email dừng ở "Xem trước"; **không nhắc nguồn dữ liệu bên thứ ba**; đọc tên "Strade vi-en").
5. Khoanh mực (`ink`) ~1 lần / 10–15 s, chỉ con số lời đọc nhấn; còn lại `focus`. Sticker ≤ 1 / 10–15 s, không ở cảnh 1.
   Bài báo làm bằng chứng phải cùng chiều thông điệp.
6. Kiểm bằng mắt trước khi báo xong: `sheet.jpg` sau mỗi lần quay, `produce.py --snap` rồi Read ảnh, sau render cắt khung MP4.
7. Render tốn RAM: chạy **một bản một lần** (`--only`), không tự chạy lại nếu hệ thống đã dừng nó — báo người dùng.

## Quy trình (chi tiết: KIT/docs/12 mục 2)
1. `python KIT/screendemo/new_clip.py --list` → có hồ sơ doanh nghiệp + thể loại phù hợp chưa?
   - Có → `new_clip.py <clip> --profile <dn> --genre <tl> --slug <NN-ten>`.
   - Doanh nghiệp mới → KIT/docs/12 mục 4 (chép `profiles/_mau`, khảo sát web bằng `probe.py` — chỉ đọc).
2. Nghiên cứu + điền `clip.json → vars` (chữ NGUYÊN VĂN trên trang) và `story`. → ✋ người dùng chốt chủ đề/bài báo.
3. Lời `voice.json` (giữ số dấu câu như mẫu) → ✋ duyệt lời → `python KIT/tools/tts_script.py voice.json audio` → ✋ nghe.
4. `shoot.py <clip> --list` (kiểm biến thiếu) → người dùng mở Chrome quay video + đăng nhập → `shoot.py <clip> <cảnh…>`.
   Việc thật: hỏi rồi mới `--set CREATE=1`. Read `assets/screen/<cảnh>/sheet.jpg` sau mỗi cảnh.
5. Kết quả cần chờ (vd truy xuất): `status.py <url>` đọc số thật → điền `R_*` → quay cảnh kết quả.
6. `produce.py <clip> --build` (xem độ dài cảnh, lỗi cụm) → `--snap …` (Read ảnh, sửa) → `produce.py <clip> --only full` → `--only demo`.
7. Kiểm MP4 (độ dài, LUFS ~-14, cắt vài khung) → báo đường dẫn + dòng ghi nguồn sticker
   *"Animated emoji: Google Noto Emoji (CC BY 4.0)"* cho mô tả bài đăng.

## Khi người dùng góp ý
Sửa đúng tầng: lời → `voice.json` + đọc lại `--only Vn`; chỗ khoanh/phóng → `shots.json` + quay lại cảnh đó; nhịp/cắt →
`story.py` (hint, mốc, VARIANT); chữ trên thẻ → `clip.json → story`. Góp ý mang tính luật chung → ghi vào
`profiles/<dn>/profile.json` (`story_rules`/`safety`) hoặc KIT/docs/12 để mọi clip sau đều theo.
