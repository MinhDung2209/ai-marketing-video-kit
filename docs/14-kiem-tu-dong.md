# 14 · Kiểm tự động (VQA) — Bộ lint bảo vệ chất lượng video

Bộ công cụ kiểm tra tự động (**VQA - Video Quality Assurance / Lint**) cho video demo sản phẩm (`screendemo/`).
Mục tiêu cốt lõi: **"Một mô hình AI yếu không thể xuất ra một video hỏng"**. Toàn bộ bài học thực tế, góp ý từ chủ dự án (như ghi lại trong nhật ký `BRIEF.md`) được mã hoá thành các quy tắc kiểm tra tự động theo 4 giai đoạn sản xuất.

---

## 1. Hợp đồng gọi lệnh (Contract)

Mọi agent và quy trình CI/CD gọi bộ kiểm qua lệnh chuẩn:

```bash
python tools/vqa/run.py <thư_mục_clip> --stage brief|shots|build|render [--json]
```

### Quy ước đầu ra:
- **Mã thoát (Exit code):** `0` nếu đạt (`ok: true`), `1` nếu có ít nhất 1 lỗi (`ok: false`).
- **Khi có cờ `--json`**, in ra duy nhất cấu trúc chuẩn:
```json
{
  "ok": true,
  "stage": "brief",
  "errors": [
    {
      "check": "forbidden_phrases",
      "where": "voice.json line V2 (text)",
      "msg": "Chứa cụm từ bị cấm: 'tờ khai hải quan'",
      "fix_hint": "Thay thế cụm 'tờ khai hải quan' bằng 'dữ liệu xuất nhập khẩu toàn cầu'."
    }
  ],
  "warnings": [
    {
      "check": "overflow",
      "where": "index.html #tg ('Tìm khách xuất khẩu bằng dữ liệu thật')",
      "msg": "Chữ 'Tìm khách xuất khẩu bằng dữ liệu thật' lấn vào safe band phải 140px (mép phải: 999px > 940px)",
      "fix_hint": "Thu nhỏ cỡ chữ, thêm ngắt dòng hoặc chỉnh CSS right/padding để nội dung nằm gọn trong vùng an toàn (right ≤ 940px)."
    }
  ]
}
```
- **`fix_hint`** luôn là hướng dẫn hành động cụ thể, súc tích (bằng tiếng Việt hoặc tiếng Anh) để mô hình AI hoặc người dựng có thể áp dụng sửa chữa ngay lập tức mà không cần đoán.

---

## 2. Bốn giai đoạn kiểm tra (4 Stages)

Quy trình kiểm tra được chia thành 4 chốt chặn độc lập:

```
[ Ý tưởng / Kịch bản ] ──> stage: brief  (voice.json, clip.json, BRIEF.md)
           │
           ▼
[ Quay màn hình web  ] ──> stage: shots  (shots.json, assets/screen/*/marks.json)
           │
           ▼
[ Dựng HTML timeline ] ──> stage: build  (index.html, cues.json, audio/SFX)
           │
           ▼
[ Render MP4 cuối    ] ──> stage: render (final/*.mp4, FFmpeg ebur128/blackdetect)
```

### Giai đoạn 1: `brief` (Kịch bản & Giọng đọc)
Kiểm tra trước khi thu âm TTS hoặc quay màn hình:
1. **Từ cấm (`forbidden_phrases`)**: Không được nói hoặc viết "tờ khai hải quan", "tờ khai", tên thương hiệu nguồn dữ liệu bên thứ ba (`panjiva`, `importgenius`, `volza`...), và không chèn emoji trong thẻ tiêu đề cảnh (badge).
2. **Từ khoá bắt buộc (`required_phrases`)**: Nhắc nhở sử dụng cụm định vị chuẩn "dữ liệu xuất nhập khẩu toàn cầu" ở câu giải pháp hoặc badge cảnh 2.
3. **Thời lượng ước tính (`speech_length`)**: Tổng thời lượng nói ước tính < `max_seconds` (mặc định 115s cho định dạng short/reels).
4. **Mã câu thoại (`line_ids`)**: Mỗi câu thoại bắt buộc có mã định dạng `V#` duy nhất (`V1`, `V2`...).
5. **Profile giọng đọc & chỉ dẫn sắc thái (`profile_direction`)**:
   - `voice.json` phải có trường `profile` chi tiết ≥ 40 từ (chân dung persona, năng lượng energy, giọng vùng miền accent, bối cảnh scene, cách phát âm thương hiệu).
   - Mỗi câu thoại phải có `direction` riêng biệt, không được sao chép y hệt câu liền trước.
   - Hướng dẫn sắc thái của Hook (câu mở đầu) và CTA (câu kết) phải khác nhau.
6. **Số viết bằng chữ (`number_words`)**: Trong trường `text` của `voice.json`, mọi con số phải viết bằng chữ (vd: "hai mươi tư", "không chín không bốn, mười một", "sáu phẩy sáu tư đô") để TTS đọc chuẩn nhịp; chữ số chỉ dùng trong trường `caption`.
7. **Video lặp vòng (`loop`)**: Nếu clip là dạng loop (`clip.json loop=true`), câu cuối phải kết thúc bằng dấu `:` hoặc bỏ lửng dẫn vào V1; cảnh đầu và cảnh cuối phải dùng cùng một bản quay và mốc zoom.

---

### Giai đoạn 2: `shots` (Bản quay màn hình)
Kiểm tra sau khi chạy `screendemo/shoot.py`:
1. **Khớp số liệu & tên riêng (`spoken_numbers_dom`)**:
   - Mọi con số và tên riêng đọc trong `voice.json` gắn với cảnh đó phải xuất hiện trên DOM thật của bản quay.
   - Tích hợp bộ chuẩn hoá số tiếng Việt: `24.000` / `24000` / `24 tấn` / `"hai mươi tư"` → `24000`; `$6,64` vs `6,64 đô` vs `"sáu phẩy sáu tư"`; mã HS `"không chín không bốn, mười một"` → `0904.11`.
2. **Quét thông tin cá nhân (`pii_scan`)**:
   - Quét toàn bộ DOM snapshot và text tại các mốc khoanh (`marks.json`).
   - Bắt lỗi nếu lộ email cá nhân của chủ sở hữu (vd: Gmail cá nhân), số điện thoại riêng, hoặc tên riêng có trong danh sách riêng tư của `rules.json`. Báo chính xác tên cảnh và tên mốc vi phạm.
3. **Chuẩn khung hình (`viewport`)**: Khung hình quay phải tuân theo chuẩn profile (đối với layout tràn viền `fullbleed` là `1080x1350`).
4. **Mật độ khoanh mực (`ink_marks`)**: Tối đa 2 lần khoanh mực (`ink: true`) mỗi cảnh (bài học từ chủ dự án: mark quá dày là spam, các vị trí khác dùng `focus()` để camera phóng sát mà không vẽ mực).

---

### Giai đoạn 3: `build` (Bản dựng Timeline)
Kiểm tra trang HTML dựng sẵn (`index.html`), `cues.json`, và tài nguyên âm thanh:
1. **Thời lượng tổng (`duration`)**: Thời lượng timeline < `max_seconds` (115s).
2. **Đo tràn chữ bằng Chrome headless (`overflow`)**:
   - Dùng Playwright render trang headless kích thước 1080x1920.
   - Đo `scrollWidth > clientWidth` (chữ tràn hộp).
   - Đo phần tử nằm ngoài khung 1080px (bị cắt mép).
   - Đo lấn vào dải an toàn bên phải **140px** (`--safe-right`): phụ đề `.cap` và badge `.step` bắt buộc không được chạm vào vùng nút bấm của TikTok/Reels (`right <= 940px`).
3. **Mật độ Sticker (`stickers`)**:
   - Khoảng cách giữa 2 sticker liên tiếp ≥ 10s.
   - Không xuất hiện sticker/meme trong 3 giây đầu video.
4. **File hiệu ứng âm thanh (`sfx_exist`)**: Mọi file SFX được gọi trong `story.py` / `index.html` phải tồn tại trên đĩa và có dung lượng > 0 byte.
5. **Độ mịn mối nối video lặp (`loop_seam`)**:
   - Chụp khung hình tại `t = 0.05s` và `t = duration - 0.05s`.
   - Tính độ lệch điểm ảnh trung bình qua PIL (`mean absolute pixel difference`).
   - Bắt buộc độ lệch < ngưỡng cho phép (`max_seam_pixel_diff: 25.0`), đảm bảo người xem không nhận ra điểm chuyển vòng lặp.
6. **Mốc cắt cụm lời (`chunk_silence`)**:
   - Mọi mốc chia câu thoại (`cues.json` pieces) phải rơi vào khoảng lặng thực tế (dựa trên `screendemo/chunks.py` và `tools/speech_segments.py`), không cắt ngang âm tiết đang nói.

---

### Giai đoạn 4: `render` (Video MP4 xuất xưởng)
Kiểm tra file MP4 cuối cùng trong `final/` hoặc `renders/`:
1. **Khớp thời lượng (`ffprobe_duration`)**: Thời lượng MP4 đo bằng ffprobe khớp với bản dựng (sai số cho phép ±0.5s).
2. **Tiêu chuẩn âm thanh EBU R128 (`loudness_peak`)**:
   - Độ lớn tích hợp: **-14 ± 1.5 LUFS** (đo bằng filter `ebur128=peak=true` của FFmpeg).
   - Đỉnh biên độ thực tế (**True Peak**): bắt buộc **< -1.0 dBTP** (ngăn ngừa méo vỡ tiếng khi nén trên TikTok/YouTube).
3. **Khung hình đen (`black_frames`)**: Sử dụng bộ lọc `blackdetect=d=0.3:pix_th=0.10` của FFmpeg; không được có đoạn khung hình đen kéo dài > 0.3s.
4. **Luồng âm thanh (`audio_present`)**: ffprobe xác nhận có luồng âm thanh hợp lệ (AAC/MP3, duration > 0, sample rate chuẩn).
5. **Đối chiếu nhận diện ASR (`asr_qa`)**: Tích hợp kiểm tra lại lời thoại bằng WhisperX/ASR (`tools/tts_qa.py`) nếu có sẵn môi trường offline.

---

## 3. Cấu hình quy tắc theo Profile (`rules.json`)

Mỗi profile khách hàng/doanh nghiệp có một file quy tắc riêng đặt tại `profiles/<profile>/rules.json`:

```json
{
  "profile": "stradevn",
  "max_seconds": 115,
  "safe_zones": {
    "top": 150,
    "bottom": 420,
    "right": 140,
    "width": 1080,
    "height": 1920
  },
  "viewport": {
    "fullbleed": [1080, 1350],
    "card": [720, 1080]
  },
  "forbidden_phrases": [
    "tờ khai hải quan",
    "tờ khai",
    "panjiva",
    "importgenius"
  ],
  "disallow_emoji_in_badges": true,
  "required_phrases": [
    "dữ liệu xuất nhập khẩu toàn cầu"
  ],
  "pii": {
    "private_emails": ["stradevn@gmail.com"],
    "forbidden_email_patterns": ["@gmail\\.com"],
    "allowed_emails": ["customerservice@stcharlestrading.com"]
  },
  "marks": {
    "max_ink_per_scene": 2
  },
  "stickers": {
    "min_spacing_seconds": 10.0,
    "none_before_seconds": 3.0
  },
  "loop": {
    "max_seam_pixel_diff": 25.0
  },
  "audio": {
    "target_lufs": -14.0,
    "lufs_tolerance": 1.5,
    "max_true_peak": -1.0,
    "max_black_duration": 0.3
  }
}
```

---

## 4. Kiến trúc Registry: Thêm bài học mới = Thêm 1 file

Khi có bài học mới từ góp ý của người duyệt, lập trình viên hoặc agent chỉ cần tạo 1 file check mới trong thư mục stage tương ứng mà không cần sửa runner trung tâm:

```python
# tools/vqa/checks/brief/new_lesson.py
from tools.vqa.registry import register_check, Issue
from tools.vqa.context import VQAContext

@register_check(stage="brief", name="new_lesson")
def check_new_lesson(ctx: VQAContext) -> list[Issue]:
    issues = []
    # Logic kiểm tra...
    if something_bad:
        issues.append(Issue(
            check="new_lesson",
            where="voice.json",
            msg="Phát hiện lỗi theo bài học mới...",
            fix_hint="Cách khắc phục cụ thể...",
            level="error"
        ))
    return issues
```
Cơ chế tự động khám phá (`pkgutil.iter_modules`) của VQA Registry sẽ tự động nạp check này vào quy trình kiểm tra!

---

## 5. Bảng bài học thực tế từ Clip 05 (`05-gioi-thieu-090411`)

| Bài học từ BRIEF.md Clip 05 | Chốt chặn VQA | Cách VQA phát hiện | Hướng khắc phục (`fix_hint`) |
|---|---|---|---|
| **Không nói "tờ khai hải quan"** | `brief/forbidden_phrases` | Quét chuỗi trong `voice.json` và badge | Thay bằng "dữ liệu xuất nhập khẩu toàn cầu" |
| **Không nhắc hãng dữ liệu đối thủ** | `brief/forbidden_phrases` | Quét danh sách brand bên thứ 3 | Bỏ tên riêng nguồn dữ liệu |
| **Không dùng emoji trong badge** | `brief/forbidden_phrases` | Regex phát hiện unicode emoji trong badge | Bỏ emoji (🇻🇳 → 🇺🇸), dùng chữ in hoa |
| **Số trên hình phải là số thật lúc quay** | `shots/spoken_numbers_dom` | Parse số tiếng Việt và so sánh với DOM | Điền đúng số liệu thực tế trên app lúc quay |
| **Mark khoanh mực bị spam** | `shots/ink_marks` | Đếm số mốc có `ink: true` trong scene | Khoanh ≤ 2 lần/cảnh, còn lại dùng `focus()` |
| **Không lộ Gmail cá nhân** | `shots/pii_scan` | Quét regex email & danh sách đen trong DOM | Che thông tin cá nhân, bỏ tab Email cá nhân |
| **App tràn viền 1080x1350** | `shots/viewport` | Kiểm tra kích thước viewport bản quay | Đặt `viewport: [1080, 1350]` trong shots.json |
| **Chữ không lọt vào dải che TikTok** | `build/overflow` | Đo toạ độ Playwright với cột phải 140px | Thêm margin hoặc giảm cỡ chữ để right ≤ 940px |
| **Meme thưa, không có ở cảnh 1** | `build/stickers` | Đo mốc thời gian xuất hiện sticker | Sticker cách nhau ≥ 10s, không đặt trước 3s |
| **Loop hook quay vòng liền mạch** | `brief/loop` & `build/loop_seam` | Check câu cuối có ':', đo pixel diff khung đầu/cuối | Câu cuối kết thúc bằng ':', cảnh đầu/cuối cùng vị trí zoom |
| **Âm thanh chuẩn -14 LUFS, không vỡ tiếng**| `render/loudness_peak` | Đo FFmpeg ebur128 (I và True Peak) | Chuẩn hoá loudness -14 LUFS, True Peak < -1 dBTP |
| **Không đen màn hình lúc chuyển cảnh** | `render/black_frames` | Đo FFmpeg blackdetect | Kiểm tra không hẫng video > 0.3s giữa các cảnh |
