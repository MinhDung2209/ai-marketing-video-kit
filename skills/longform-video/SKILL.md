---
name: longform-video
description: Làm video YouTube DÀI 10–60 phút kiểu phim tài liệu du lịch (16:9, 1080p/4K) — kịch bản chương → câu, giọng đọc, footage ~3s/cảnh từ Envato/Storyblocks (tải tay có trang hỗ trợ) hoặc Pexels/Pixabay (tự động), nhạc nền, tiêu đề chương, phụ đề .srt, mốc chương YouTube. Dùng khi người dùng nói "video dài", "phim tài liệu", "video YouTube 15/30/60 phút", "footage Envato/Storyblocks".
---

# Video dài từ footage (longform)

KIT = <ĐƯỜNG DẪN TỚI THƯ MỤC kit>   ← cài bằng `python tools/install_skill.py` (tự điền). Tài liệu: `KIT/docs/11-video-dai.md` (đọc trước khi làm), giá: `KIT/docs/10-chi-phi.md`. Kịch bản mẫu: `KIT/templates/longform/script.json`.

## Luật bắt buộc
1. **Hình phải khớp lời TỪNG CÂU.** Câu nói "Cầu Rồng phun lửa" thì cảnh lúc đó phải là Cầu Rồng phun lửa — không phải
   cảnh Đà Nẵng bất kỳ. Câu nào có chủ thể cụ thể (công trình, lễ hội, món ăn, hoạt động) → ghi `"q"` riêng cho câu đó
   và tải clip vào đúng câu (xem bước 4). Câu chung chung (cảm xúc, chuyển ý) mới dùng clip chung của chương.
2. **Không tự động tải từ Envato Elements / Storyblocks** (không có API cho gói cá nhân; bot đăng nhập + bấm tải hàng loạt
   vi phạm điều khoản → khoá tài khoản của KHÁCH). Chỉ dùng `collect` — người bấm Download, tool lo phần còn lại.
   Envato: khi tải chọn đăng ký license theo **tên kênh của khách**.
3. **Không bịa** số liệu, năm, kỷ lục. Kịch bản kèm nguồn cho mỗi con số (cột `"src"` trong câu) để khách kiểm.
4. **Bạn không nghe được âm thanh** → người dùng nghe duyệt giọng + nhạc. **Bạn nhìn được ảnh** → luôn Read
   `footage/_sheet_*.jpg` và khung cắt từ MP4 trước khi báo xong.
5. Khách duyệt kịch bản (bản tiếng Việt nếu song ngữ) rồi mới tải footage + dựng.

## Viết kịch bản `script.json` (để tìm ĐÚNG footage)
- Chương = 1 địa danh. `"place"`: tên địa danh tiếng Anh như người đăng footage hay gõ (`"Da Nang"`, `"Ha Long Bay"`).
- Mỗi câu: `"text"` (lời đọc), `"kw"` (2–4 từ hình ảnh tiếng Anh), `"q"` khi câu có chủ thể cụ thể.
- Cách viết `"q"` (từ khoá tìm trên Envato/Storyblocks, tiếng Anh, 3–6 từ): **chủ thể + địa danh + kiểu quay/thời điểm**.
  Tốt: `"dragon bridge fire breathing da nang night"`, `"hoi an lantern river boat night"`, `"ha long bay kayak cave aerial"`.
  Tệ: `"vietnam beautiful"`, `"travel"`, `"city"` (ra cảnh nước khác). Không viết lời đọc về thứ không quay được.
- Song ngữ: `"text"` = bản đọc (tiếng Anh nếu giọng Adam), `"text_vi"` = bản tiếng Việt cho khách duyệt.
- 4K: `"res": "4k"` ở gốc script.json.

## Quy trình
1. `python KIT/tools/check_env.py` (máy mới) · dự án = thư mục có `script.json` (+ `.env` nếu dùng Pexels/Pixabay).
2. Giọng: Gemini → `python KIT/tools/longform.py tts <dự án>` (→ `audio/timing.json`). → **người dùng nghe**.
3. Nhạc: file Epidemic khách cấp → `bgm/…` + `"bgm": {"file": …}`; không có thì `lyria_bgm.py` (KIT/docs/06).
4. Footage tải tay: `python KIT/tools/longform.py collect <dự án>` → trang http://127.0.0.1:8765 mở ra.
   Hướng dẫn người dùng: bấm vào **câu** (hoặc tiêu đề chương cho clip chung) → bấm nút Envato/Storyblocks → chọn clip →
   Download. File tải về tự vào `footage/local/<chương>/<số câu>/`; mỗi thẻ hiện số clip đã có / cần (xanh = đủ).
   Mỗi clip cắt tối đa 4 cảnh ở 4 đoạn khác nhau → 15 phút cần ~70–100 clip, không phải 300.
   Footage miễn phí (demo): bỏ qua bước này, `footage` tự gọi Pexels/Pixabay theo `queries`/`must`.
   **Chỉ nhận content** (editor bên khách dựng): `longform.py collect <dự án> --links` → người dùng mở clip, dán link vào
   ô dưới từng câu → bàn giao `footage_sheet.csv` + kịch bản + file giọng. Không chạy footage/render.
5. `python KIT/tools/longform.py footage <dự án> [--nvenc]` → Read `footage/_sheet_*.jpg`: cảnh sai → id vào
   `footage/blacklist.txt` (id `lcxxxxxxxx` = cả clip, `lcxxxxxxxx-2` = 1 đoạn) → chạy lại.
6. `python KIT/tools/longform.py render <dự án> --out <tên>.mp4 [--nvenc]` → kèm `.srt`, `youtube_chapters.txt`,
   `footage_credits.txt`.
7. Kiểm: ffprobe (độ phân giải, thời lượng), cắt 5–10 khung ở các câu có chủ thể cụ thể → Read → đối chiếu lời.
   `--nvenc` báo "driver ≥ 610" → tool tự dùng CPU (chậm hơn); nhắc người dùng cập nhật driver NVIDIA.

## Khi người dùng góp ý
Đổi lời → `tts --only <id câu>` rồi `footage` + `render` · đổi cảnh → blacklist / tải thêm vào đúng câu → `footage` + `render`.
