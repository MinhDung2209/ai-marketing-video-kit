# ai-marketing-video-kit

**Làm video quảng cáo ngắn (Reels / TikTok / Ads) bằng AI, từ kịch bản tới MP4 1080p, với Claude Code.**
Kịch bản có hook → giọng đọc Gemini-TTS có đạo diễn cảm xúc → ảnh/clip AI giữ đúng một nhân vật → nhạc nền Lyria →
hiệu ứng âm thanh khớp chuyển động → phụ đề → render bằng Chrome + FFmpeg.

> **English:** An AI short-form video ad toolkit (9:16, 30–60s) built around Claude Code: hook-driven scripts,
> directed Gemini-TTS voice-over, character-consistent AI images/clips, Lyria background music, animation-synced
> SFX, captions, and a frame-accurate HTML/GSAP → MP4 renderer (Playwright + Chrome + FFmpeg). Docs are in
> Vietnamese; code identifiers are in English.

![Các khung hình từ video ví dụ](docs/assets/preview.jpg)

Làm ra từ một dự án thật: video quảng cáo **StradeVn** 54 giây. Toàn bộ nguồn (kịch bản, lời đạo diễn giọng, prompt ảnh,
dựng cảnh, bản trộn âm, video xuất) nằm trong [`examples/stradevn-ad-v2/`](examples/stradevn-ad-v2/).

## Cài đặt

Cần: **Python 3.11+**, **FFmpeg** (bản full, có ffprobe), **Google Chrome**, Git.

```bash
git clone https://github.com/MinhDung2209/ai-marketing-video-kit.git && cd ai-marketing-video-kit
pip install -r requirements.txt
# FFmpeg không cài qua pip:  winget install Gyan.FFmpeg | brew install ffmpeg | sudo apt install ffmpeg
cp config.example.json config.json   # điền đường dẫn key Google Cloud (giọng đọc + nhạc)
python tools/check_env.py            # kiểm cả máy: ✅/❌ từng mục, kèm cách sửa
python tools/install_skill.py        # (tuỳ chọn) cài skill cho Claude Code
```

Từng bước chi tiết, kể cả tạo key Google Cloud và kết nối plenxai: [`docs/01-cai-dat.md`](docs/01-cai-dat.md).

## Làm video đầu tiên

**Với Claude Code** (khuyên dùng): cài skill xong, nói *"làm video marketing cho …"*. Agent làm theo quy trình và dừng
lại xin duyệt ở các bước tốn tiền hoặc cần tai người (ảnh/clip AI, giọng, nhạc, hiệu ứng).

**Tự chạy bằng lệnh:**
```bash
python tools/new_project.py ~/videos/san-pham-a      # tạo dự án từ khung mẫu
cd ~/videos/san-pham-a
# viết BRIEF.md · điền voice.json + scenes.json · thả ảnh/clip/logo vào assets/
python <kit>/tools/make_video.py ~/videos/san-pham-a  # CHẠY TOÀN BỘ: giọng → dựng → trộn → xem thử → render → kiểm tra
python <kit>/tools/make_video.py ~/videos/san-pham-a --from mix   # sửa xong → chạy lại từ 1 bước
```
Từng bước riêng lẻ (giọng, dựng, trộn, render): [docs/02](docs/02-quy-trinh-tung-buoc.md).

## Tài liệu

| Bạn là… | Đọc |
| --- | --- |
| Người mới hoàn toàn | [00 Tổng quan](docs/00-tong-quan.md) → [01 Cài đặt](docs/01-cai-dat.md) → [02 Quy trình từng bước](docs/02-quy-trinh-tung-buoc.md) |
| Người viết kịch bản | [03 Kịch bản & hook](docs/03-kich-ban-va-hook.md) + [Thư viện hook](library/hooks/THU-VIEN-HOOK.md) |
| Người làm hình & tiếng | [04 Giọng đọc](docs/04-giong-doc.md) · [05 Ảnh & clip AI](docs/05-anh-va-clip-ai.md) · [06 Âm thanh](docs/06-am-thanh.md) |
| Người dựng | [07 Dựng cảnh & render](docs/07-dung-canh-va-render.md) · [08 Kiểm tra trước khi đăng](docs/08-kiem-tra-va-xuat-ban.md) |
| Gặp lỗi / tính tiền | [09 Lỗi thường gặp](docs/09-loi-thuong-gap.md) · [10 Chi phí](docs/10-chi-phi.md) |

## Trong repo có gì

| Thư mục | Nội dung |
| --- | --- |
| `tools/` | 18 công cụ Python: **chạy toàn bộ 1 lệnh (`make_video.py`)**, kiểm máy, tải nguồn âm thanh, cài skill, giọng đọc, nhạc, tìm/nghe thử hiệu ứng, phụ đề, đo cụm nói, trộn âm, render, tạo dự án, đóng gói |
| `templates/video-project/` | Khung dự án mới, dựng tự động từ `scenes.json` (4 kiểu cảnh: media · screenshot · logo · cta) |
| `examples/stradevn-ad-v2/` | Video thật đã làm, đủ nguồn để dựng và render lại |
| `audio-library/` | 1.103 hiệu ứng + nhạc nền (uisfx, Pixabay, Mixkit) + nhạc Lyria — có sẵn trong repo. Nguồn + giấy phép từng file: `catalog.json` |
| `library/hooks/` | 40+ kiểu hook tiếng Việt |
| `skills/marketing-video/` | Skill cho Claude Code |
| `integrations/hypit/` | (Tuỳ chọn) cài nhanh [Hypit](https://github.com/hypit-ai/hypit): nhân bản video mẫu, mốc từng chữ — kèm kết quả đã đo |
| `docs/` | 11 tài liệu (00–10) |

## Dịch vụ cần tài khoản riêng

| Dịch vụ | Dùng cho | Chi phí 1 video ~50s (tra 30/09/2026) |
| --- | --- | --- |
| Google Cloud: Text-to-Speech (`gemini-3.1-flash-tts-preview`) + Vertex AI Lyria | Giọng đọc, nhạc nền | ~5.000–10.000đ |
| [plenxai](https://plenxai.com) qua MCP | Ảnh `gpt-image-2.5-flare`, clip `omni-flash-video` | theo credit plenxai |

Render, trộn âm, thư viện âm thanh chạy trên máy, không tốn phí. Chi tiết: [docs/10](docs/10-chi-phi.md).

**Bảo mật:** không commit file key Google Cloud. `config.json` đã nằm trong `.gitignore`; key nên để ngoài thư mục repo.

## Giấy phép

Code và tài liệu: [Apache-2.0](LICENSE). Ngoại lệ (xem [NOTICE](NOTICE)):
- **Ví dụ StradeVn** (`examples/stradevn-ad-v2/`): thương hiệu, logo, ảnh chụp sản phẩm, nhân vật AI và video © StradeVn, chỉ để minh hoạ quy trình.
- **Font:** OFL 1.1.
- **Âm thanh:** uisfx là CC0; Pixabay/Mixkit theo giấy phép của từng nguồn.

Các repo và dịch vụ bên thứ ba đã dùng, kèm giấy phép: [THIRD-PARTY.md](THIRD-PARTY.md).
