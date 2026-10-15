# 05 · Ảnh & clip AI (plenxai qua MCP)

## 1. Luật làm việc
- **Mọi request ảnh/clip gửi người duyệt trước** (prompt, model, tỉ lệ, ảnh tham chiếu). Không "gen bừa".
- **Hạn mức credit** mỗi dự án (vd 700) + sổ chi `credits.md` (ghi cả lần timeout — có thể đã bị trừ).
- Logo cần CHÍNH XÁC → **chèn file thật khi dựng**; logo AI vẽ lên áo chỉ gần giống (đạt được: S cam + sao vàng).
- Không bịa số liệu trên ảnh (lần đầu AI tự thêm "98% độ chính xác", "120 quốc gia" → phải cấm trong prompt).

## 2. Model đã dùng (30/09–01/10/2026)
| Việc | Model | Tham số | Kết quả đo |
| --- | --- | --- | --- |
| Ảnh chân thực | **`gpt-image-2.5-flare`** | `resolution: 2k`, `aspect_ratio: 9:16`, `references_urls` | 2048×3584, 7 credit, giữ mặt tốt, viết đúng chữ tiếng Việt có dấu |
| Ảnh rẻ hơn | `gpt-image-2` | 2k | ra 1024×1792 (không phải 2k thật), 5 credit |
| Clip từ ảnh | **`omni-flash-video`** (`generate_video_omni`) | `video_mode: i2v`, `input_image_url`, `resolution: 1080p`, `duration: 4/6/8/10` | 1080×1920, 24 fps, 6s, có track âm (tắt đi) |

## 3. Giữ đồng bộ nhân vật (KOL)
1. Tạo **1 ảnh gốc** đẹp (chân dung rõ mặt) → đó là "mỏ neo". Giữ link công khai của nó (plenxai `images.plenxai.com/...`).
2. Mọi ảnh sau: `references_urls = [link ảnh gốc, link logo]` + câu bắt buộc:
   *"The SAME woman as the first reference image — keep her exact face, bun hairstyle and light-blue shirt with the small
   embroidered logo (from the second reference image) on the left chest."*
3. Clip: ảnh đầu (`input_image_url`) phải là ảnh đã đúng mặt → clip giữ mặt theo.
4. **Không xoá ảnh gốc trên plenxai** — plenxai không có upload; mất link là mất mỏ neo.
5. KOL là **người dẫn chuyện**, không đóng vai khách hàng (docs/03).

## 4. Prompt ảnh — công thức
`Photorealistic vertical commercial photo. [NHÂN VẬT — câu SAME…]. [HÀNH ĐỘNG + BIỂU CẢM]. [BỐI CẢNH]. [ÁNH SÁNG], [ỐNG KÍNH 35/50/85mm], shallow depth of field, realistic skin texture. [CHỮ nếu có, trong ngoặc kép]. No other text.`
Negative: `different person, different face, misspelled text, extra text, cartoon, 3D render, plastic skin, distorted hands, extra fingers, large logo, blue logo`
Ví dụ thật (I-C1): *"… holding up a large printed A3 sheet with the bold black Vietnamese text "TUYỂN SALES XUẤT KHẨU" facing
the camera, a confident slight smirk, looking straight into the camera. Soft natural daylight, 35mm …"* → đúng chính tả.

## 5. Prompt clip — **MỖI CLIP CHỈ 1 ĐỘNG TÁC ĐƠN GIẢN**
Bài học: prompt "nghe điện thoại → ăn mừng → kẹp máy vào vai → viết" cho ra 2 clip lỗi liền (điện thoại lơ lửng, "dịch
chuyển" từ tay phải sang vai trái). Clip 1 động tác (xé đôi tờ giấy; hạ tay thở dài) thì đạt ngay.
Công thức: `The same woman [1 ĐỘNG TÁC]. [CHUYỂN ĐỘNG MÁY: slow push-in / dolly-in / handheld]. [BỐI CẢNH]. Realistic natural motion, keep her face, hairstyle and outfit unchanged. No added text, no subtitles.`
- Dùng lại đoạn đẹp của clip lỗi: `data-offset` / `data-end` (docs/07) — vd lấy 0–3,1s và 3,9–6,0s của cùng clip.
- Clip ngắn hơn cảnh: phát chậm `data-rate="0.75"` và/hoặc giữ khung cuối.

## 6. Timeout & lấy kết quả
- Ảnh flare/clip thường lâu hơn giới hạn chờ MCP (~4 phút) → MCP báo *"The operation timed out"* nhưng **vẫn đang tạo**.
- Gọi **tuần tự từng cái**, không gọi song song (song song hay timeout cả loạt).
- Lấy kết quả: vào web plenxai → copy link. Link ảnh dạng `.../w=400,quality=70,format=auto` là bản thu nhỏ → đổi đuôi thành
  `format=png,quality=100` để tải bản gốc. Clip: link `cdn.plenxai.com/.../omni_vids_1080p_....mp4`.
- Endpoint `get_credit_balance` / `list_my_jobs` của MCP có lúc lỗi → tự ghi sổ.
- Tên model phải đúng mã (`gpt-image-2.5-flare`, không phải `gpt-image-2-5-flare`); model ngoài gói tài khoản báo "không khả dụng trong gói".

## 7. Ảnh chụp sản phẩm thật (bằng chứng)
Chụp màn hình app/sản phẩm bằng Chrome headless (2x) — xem ví dụ `assets/img/map-988.png`, `ranking.png`. Dùng dữ liệu của
tài khoản demo, không dữ liệu khách thật; làm mờ phần nhạy cảm. Ảnh app thật tạo độ tin cậy mà ảnh AI không thay được.

## 8. Ảnh/clip stock miễn phí (Pexels, Unsplash) — không tốn credit
Hợp với video du lịch, ẩm thực, phong cảnh: không cần nhân vật đồng bộ thì dùng stock thật thay ảnh AI.
- Key: `PEXELS_API_KEY`, `UNSPLASH_ACCESS_KEY` trong file `.env` ở thư mục dự án (hoặc biến môi trường). Không commit.
- Tìm: `python KIT/tools/stock_media.py search "dalat" --type video` → in ứng viên + ảnh ghép `_stock_sheet.jpg` (đánh số)
  để xem bằng mắt. Ảnh: `--type photo`, thêm `--source unsplash` để lấy Unsplash.
- Tải: `python KIT/tools/stock_media.py get pexels:video:<id> assets/clips/x.mp4` — tự chọn bản dọc gần 1080×1920,
  ghi tác giả + link vào `stock_credits.json`.
- **Đúng địa danh:** tìm theo tên địa danh vẫn ra cảnh nơi khác (đo 15/10/2026: "tea plantation" toàn Ấn Độ, "night market"
  ra Hà Nội khi làm video Đà Lạt). Đọc link/mô tả từng clip; không chắc nơi chụp thì lời đọc nói chung chung, không gọi tên.
- Clip Pexels hay là 60 fps, GOP dài → render tua chậm. Chuẩn hoá trước khi dựng:
  `ffmpeg -i in.mp4 -t 15 -an -vf "fps=30,scale=1080:1920" -c:v libx264 -crf 18 -g 15 -pix_fmt yuv420p out.mp4`
