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

## Footage trả phí tải tay — Envato Elements, Storyblocks (đo 15/10/2026)
Envato Elements **không có API tải** (API ở build.envato.com chỉ cho Envato Market — món mua lẻ); Storyblocks có API nhưng
cho gói doanh nghiệp. Bot đăng nhập + bấm tải hàng loạt vi phạm điều khoản → khoá tài khoản của khách. Nên:
```bash
python <kit>/tools/longform.py collect .          # trang http://127.0.0.1:8765 — mỗi chương 1 thẻ, mỗi câu 1 dòng
#   bấm vào CÂU (vd "Cầu Rồng phun lửa") → nút Envato/Storyblocks mở trang tìm theo "q" của câu → chọn clip → Download
#   tool canh thư mục Downloads: tải xong tự chuyển vào footage/local/<chương>/<số câu>/ (zip tự giải nén lấy video)
#   bấm tiêu đề chương = clip chung của chương. Thẻ hiện "đã có/cần" (xanh = đủ)
python <kit>/tools/longform.py footage .          # chương có footage/local/… → không gọi API; --source stock để bỏ qua
```
- **Khớp lời từng câu**: clip trong thư mục của câu chỉ dùng cho câu đó (dùng trước), clip chung lấp phần còn lại; clip
  của câu khác không bao giờ bị lấy (bài học video 14/10: câu "Cầu Rồng phun lửa" ra cảnh khác vì chỉ lọc theo chương).
- Mỗi clip cắt tối đa 4 cảnh ở 4 đoạn khác nhau → video 15 phút cần ~70–100 clip (≈ 45–60 phút bấm tải), không phải 300.
- Từ khoá tìm `"q"` của câu: chủ thể + địa danh + kiểu quay (`"dragon bridge fire breathing da nang night"`).
  Thiếu `"q"` thì ghép `"place"` của chương + 2 `kw` đầu.
- **Chỉ làm content (bàn giao cho editor khác dựng)**: `collect . --links` — cùng trang nhưng không tải; dưới mỗi câu có
  ô dán link trang clip (Envato/Storyblocks). Tự lưu `footage/links.json` + xuất `footage_sheet.xlsx` (Google Sheets:
  Tệp → Nhập) và `footage_sheet.csv`, theo mẫu khách: **Number · English · VN · Footage EN · File name EN · ID · Status**.
  Số câu chạy liên tục cả video; dòng tiêu đề chương (EN = `title`, VN = `title_vi`) tô xanh; ID lấy từ link
  (Envato `…-QS9NYFF`, Storyblocks `SBV-…`), File name = `<số>-<ID>`; câu có 2 link → dòng phụ `12.2`; dòng "chung" =
  clip chung của chương. Thẻ TTS `[short pause]` tự bỏ. Status để trống cho editor ghi.
  Editor tải theo sheet bằng tài khoản của họ (license theo tài khoản người tải).
- Cài trình duyệt lưu thẳng vào Downloads (không hỏi chỗ lưu); thư mục khác: `--downloads <thư mục>`.
- Envato: đăng ký license theo tên kênh của khách; `footage_credits.txt` giữ danh sách file làm bằng chứng.

## 4K
`"res": "4k"` trong script.json → cắt cảnh, ghép, xuất ở 3840×2160 (cảnh để riêng `footage/seg_2160p/`, `render/2160p/` —
không lẫn bản 1080p). Tiêu đề chương tự phóng theo. `--nvenc` (footage, render) mã hoá bằng card NVIDIA; đo 15/10/2026
GTX 1650 driver 591.86 báo "Required: 13.1 Found: 13.0" (FFmpeg mới cần driver ≥ 610) → tool tự chuyển CPU:
1 chương 108s/34 cảnh ở 4K mất ~1,5 phút cắt + ~3 phút dựng bằng CPU.

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
