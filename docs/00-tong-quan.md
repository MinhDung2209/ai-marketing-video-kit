# 00 · Tổng quan: video được làm ra như thế nào

## 1. Dây chuyền

```
① KỊCH BẢN (BRIEF.md) ── hook · nỗi đau · lời giải · bằng chứng · kêu gọi; mỗi cảnh ghi lời + hình + âm thanh
      │
② GIỌNG ĐỌC ── Gemini-TTS (Google) đọc từng câu có "đạo diễn" → audio/V1..Vn.mp3 + timing.json (mốc thật)
      │
③ HÌNH ── ảnh AI (plenxai gpt-image-2.5-flare) · clip AI (plenxai omni-flash-video) · ảnh chụp sản phẩm thật
      │
④ NHẠC NỀN ── Lyria (Google Vertex AI) tạo riêng, hoặc nhạc mở trong audio-library
      │
⑤ DỰNG CẢNH ── 1 trang HTML + GSAP: chữ, số, ảnh, clip chuyển động; MỌI mốc lấy từ timing.json (build.py)
      │          → sinh luôn phụ đề + danh sách hiệu ứng âm thanh (cues.json)
⑥ TRỘN ÂM ── giọng + nhạc (tự hạ khi có giọng) + hiệu ứng (tự cân độ to) → final_audio.mp3 (mix_audio.py)
      │
⑦ RENDER ── Chrome tua từng khung hình → FFmpeg ghép hình + tiếng → MP4 1080×1920 (render.py)
      │
⑧ KIỂM TRA ── xem khung hình, nghe, đo âm lượng, checklist → đăng
```

Nguyên tắc cốt lõi: **giọng đọc là "đồng hồ" của video.** Đọc giọng trước, đo thời lượng thật từng câu, rồi mọi cảnh,
chữ, hiệu ứng âm thanh, phụ đề đều suy ra từ đó → sửa lời / đổi giọng chỉ cần chạy lại, không căn tay.

## 2. Công nghệ (tech stack) — đã chạy thật 30/09–01/10/2026

| Tầng | Công nghệ | Vai trò | Chi phí |
| --- | --- | --- | --- |
| Điều khiển | **Claude Code** + skill `marketing-video` | Viết kịch bản, gọi công cụ, dựng, kiểm tra | theo gói Claude |
| Giọng đọc | **Google Cloud Text-to-Speech — Gemini-TTS** `gemini-3.1-flash-tts-preview` (giọng Kore) | Giọng có cảm xúc, điều khiển bằng lời đạo diễn | ~850đ / video 60s |
| Nhạc nền | **Vertex AI Lyria** (`lyria-002`) | Nhạc không lời theo mô tả, ~32s/lần | 0,06 USD / lần |
| Ảnh AI | **plenxai** `gpt-image-2.5-flare` (2k) | Ảnh chân thực, giữ mặt nhân vật bằng ảnh tham chiếu | 7 credit / ảnh |
| Clip AI | **plenxai** `omni-flash-video` (1080p, 4/6/8/10s) | Ảnh → clip chuyển động (không tiếng) | theo bảng plenxai |
| Dựng cảnh | **HTML + CSS + GSAP 3** theo định dạng **HyperFrames** (heygen-com, Apache 2.0) | Chữ/số/ảnh/clip chuyển động theo thời gian | 0 |
| Render | **Playwright (Python) + Google Chrome + FFmpeg** (`tools/render.py`) | Tua từng khung → MP4 H.264 + AAC | 0 |
| Âm thanh | **FFmpeg** (`mix_audio.py`): sidechain ducking, chuẩn hoá đỉnh, limiter | Trộn giọng + nhạc + hiệu ứng | 0 |
| Thư viện âm | Pixabay (19) · Mixkit (148 + 4 nhạc) · uisfx CC0 (936) | Hiệu ứng âm thanh sạch giấy phép | 0 |
| Phụ đề | `captions.py` (theo cụm câu) + `speech_segments.py` (đo khoảng lặng) | Phụ đề + canh hoạt ảnh đúng cụm nói | 0 |
| Font | Be Vietnam Pro + IBM Plex Sans (SIL OFL) | Chữ tiếng Việt đẹp, đủ dấu | 0 |

## 3. Bản đồ thư mục
```
kit/
├── docs/                 00–10 (bạn đang đọc)
├── tools/                công cụ Python (mục 4)
├── templates/            khung dự án mới + font
├── examples/             video StradeVn v2 đầy đủ
├── audio-library/        sfx/ bgm/ catalog.json
├── library/hooks/        thư viện hook
├── skills/               skill cho Claude Code
├── config.example.json   → chép thành config.json
└── requirements.txt
```

## 4. Công cụ
| Công cụ | Làm gì | Tài liệu |
| --- | --- | --- |
| `new_project.py` | Tạo dự án từ khung mẫu | 02 |
| `tts_script.py` | Đọc `voice.json` → mp3 từng câu + narration.mp3 + timing.json (`--only V3` đọc lại 1 câu) | 04 |
| `lyria_bgm.py` | Tạo nhạc nền bằng Lyria | 06 |
| `sfx_search.py` | Tìm hiệu ứng theo từ khoá | 06 |
| `sfx_audition.py` | Ghép file nghe thử nhiều hiệu ứng để chọn | 06 |
| `captions.py` | Phụ đề theo cụm từ timing.json | 07 |
| `speech_segments.py` | Tách cụm nói theo khoảng lặng (canh hoạt ảnh đúng lời) | 07 |
| `mix_audio.py` (+ `mix_audio_peak.py`) | Trộn giọng + nhạc + hiệu ứng | 06 |
| `render.py` | Chụp khung thử (`--snap`) / render MP4 (hỗ trợ clip: data-rate/offset/end) | 07 |
| `gcp.py` | Lấy token Google Cloud từ key (dùng chung) | 01 |
| `build_library.py` | Gom lại thư viện âm thanh từ repo gốc (hiếm khi cần) | 06 |
| `make_package.py` | Đóng gói bộ này thành zip | 01 |
