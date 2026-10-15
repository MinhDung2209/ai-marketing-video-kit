# 11 · Video dài (10–60 phút, 16:9) — phim tài liệu du lịch từ footage stock

Kiểu video: giọng dẫn + footage đổi ~3 giây/cảnh + nhạc nền + tiêu đề chương (mẫu khách đưa: "Wonders of Sri Lanka",
Epic Explorations TV — 57 phút, 25 chương theo địa danh, flycam, chuyển mờ, không chữ chạy). 15 phút ≈ 275 cảnh.
Ví dụ đã làm: dự án "Kỳ quan Việt Nam" (15/10/2026) — 14,5 phút, 11 chương, 275 cảnh.

Khác `render.py` (Chrome chụp từng khung — hợp video ngắn có hoạt ảnh): `tools/longform.py` ghép bằng FFmpeg.

## Quy trình
```bash
python <kit>/tools/new_project.py ...            # hoặc tạo thư mục trống
cp <kit>/templates/longform/script.json .        # viết kịch bản: chương → câu → từ khoá footage
# .env: PEXELS_API_KEY=… (bắt buộc) · PIXABAY_API_KEY=… (tuỳ chọn)
python <kit>/tools/longform.py tts .             # ~83 câu đọc song song 4 luồng, ~5 phút
python <kit>/tools/lyria_bgm.py "<prompt>" bgm/p1.wav --seed N   # 5–6 đoạn → acrossfade → bgm/nhac-nen.wav, ghi vào script.json "bgm"
python <kit>/tools/longform.py footage .         # chọn + tải + cắt; ~8 GB nguồn cho 275 cảnh, ~20 phút lần đầu
#   → MỞ footage/_sheet_*.jpg (mỗi chương 1 ảnh, số vàng = đúng địa danh) — ghi id cảnh sai vào footage/blacklist.txt → chạy lại footage
python <kit>/tools/longform.py render . --out video.mp4   # + video.srt (phụ đề YouTube) + youtube_chapters.txt + footage_credits.txt
```
Xem nhịp dựng của video mẫu: `yt-dlp --skip-download --write-info-json <link>` (tên chương, mô tả), tải 1–2 đoạn ngắn
`--download-sections "*0:00-1:30"` rồi `ffmpeg -vf "select='gt(scene,0.12)',showinfo"` để đếm điểm cắt.

## Nguồn footage — đo 15/10/2026
| Nguồn | Key | Lọc đúng địa danh bằng | Ghi chú |
| --- | --- | --- | --- |
| Pexels | có | đường dẫn `/video/<mô-tả-tự-sinh>-id/` | Giới hạn 25.000 lượt/giờ. Ha Long 80/160 clip ghi đúng tên; Huế 1/160, Phú Quốc 2/160 |
| Pixabay | có | tag do người đăng tự gõ | **Tag rác**: 1 clip thác nước gắn cả hanoi, saigon, sapa… → tool loại clip ghi địa danh của ≥2 chương. Bị Cloudflare chặn tạm theo IP (429 `cf-mitigated: challenge`, cả n8n/Docker cùng IP cũng dính) → tool gọi chậm 1,2s/lượt, gặp chặn thì bỏ Pixabay ở lượt đó |
| Wikimedia Commons | không | tên file/mô tả/danh mục có dấu | Hà Nội 156 video, Hội An 87, Hạ Long 62 — nhưng kết quả tự động lẫn nhiều rác (màn chữ "Present", logo kênh khác, tin bão lũ có chữ, dashcam, quảng cáo) → chỉ bật bằng `wm_queries` rồi duyệt tay. Tải file phải có User-Agent (thiếu → 403). Bắt buộc ghi tác giả + giấy phép |
| Pinterest | — | — | **Không dùng**: ảnh không thuộc Pinterest, không giấy phép → rủi ro bản quyền YouTube. Chỉ làm moodboard |

Viết kịch bản THEO footage có thật: chương nào kho miễn phí thiếu (Huế, Phong Nha, Phú Quốc) thì bỏ, hoặc mua footage.
Footage trả phí có API (Storyblocks, Shutterstock, Adobe Stock, Pond5) — giá + rủi ro: xem `docs/10-chi-phi.md`.

## Giọng một người đọc
Mỗi câu 1 lần gọi TTS → độ to chênh tới 5 dB giữa các câu (đo 15/10), nghe như đổi người. Tool cắt lặng đầu/cuối và
`loudnorm=I=-18` từng câu (còn chênh ~0,5 dB), ghép bằng WAV (mp3 nối concat lệch ~26 ms/file → 160 file lệch vài giây).
Cùng 1 giọng (`voice`) + 1 `profile` cho cả bài; vẫn phải nghe lại vài chương.

## Upscale
GTX 1650 4GB chạy được Real-ESRGAN (`realesrgan-ncnn-vulkan`) / Video2X (~1–3 khung/giây). Video "Kỳ quan Việt Nam" chỉ
6/275 cảnh nguồn < 1920px (thấp nhất 1280) → không cần; đáng làm khi nguồn ≤ 720p hoặc xuất 4K.

## Rủi ro báo khách
YouTube có thể xếp video ghép stock + giọng AI vào "nội dung tái sử dụng" (không bật kiếm tiền) → kịch bản riêng, lời bình
có quan điểm, dựng có chủ đích. Không nói sai địa danh: clip không chắc nơi quay thì lời đọc nói chung chung.
