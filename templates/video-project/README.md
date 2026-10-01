# Dự án video (tạo từ khung mẫu)

1. Viết kịch bản: `BRIEF.md` (xem ví dụ thật ở `kit/examples/stradevn-ad-v2/BRIEF.md`).
2. Lời đọc: `voice.json` → `python <kit>/tools/tts_script.py voice.json audio`
3. Ảnh/clip vào `assets/img`, `assets/clips`; logo thật vào `assets/img/logo.png`; nhạc vào `bgm/`.
4. Cảnh: `scenes.json` (mỗi câu 1 cảnh) → `python build.py`
5. Âm thanh: `python <kit>/tools/mix_audio.py cues.json assets/final_audio.mp3`
6. Xem thử: `python <kit>/tools/render.py . --snap 1,5,10` → mở `_snap_*.png`
7. Xuất: `python <kit>/tools/render.py . --fps 30 --audio assets/final_audio.mp3 --out video.mp4`
Chi tiết: `kit/docs/02-quy-trinh-tung-buoc.md`.
