# 02 · Quy trình từng bước — từ ý tưởng tới MP4

Ví dụ xuyên suốt: `examples/stradevn-ad-v2/` (54 giây, 9 cảnh, 4 clip AI). Khung trống: `templates/video-project/`.
Ký hiệu `<kit>` = đường dẫn thư mục kit.

## Bước 0 — Tạo dự án
```bash
python <kit>/tools/new_project.py projects/<khach-hang>/<video>
cd projects/<khach-hang>/<video>
```

## Bước 1 — Kịch bản (BRIEF.md) · 30–60 phút · người duyệt: chủ dự án
1. Viết 1 câu ý tưởng lớn + người xem chính (docs/03).
2. Chọn hook trong `library/hooks/THU-VIEN-HOOK.md` — viết 3 phương án, chọn 1.
3. Chia cảnh theo công thức **Hook → Nỗi đau → Lời giải → Bằng chứng → Kêu gọi**; mỗi cảnh ghi: lời · hình · chữ
   trên hình · âm thanh.
4. Liệt kê ảnh/clip AI cần tạo + prompt → **gửi duyệt trước khi tạo** (tốn credit).
5. Người duyệt đọc BRIEF → sửa → duyệt.

## Bước 2 — Giọng đọc · 5 phút · ~vài trăm đồng
1. Điền `voice.json`: `profile` (giọng chung), mỗi câu `text` + `direction` (docs/04).
2. `python <kit>/tools/tts_script.py voice.json audio`
3. **Người duyệt nghe** `audio/narration.mp3`. Sửa câu nào → sửa voice.json → `--only V3` chỉ đọc lại câu đó.

## Bước 3 — Ảnh & clip AI · 30–90 phút (chờ plenxai) · credit
1. Ảnh nhân vật (KOL) gốc trước → dùng làm tham chiếu cho mọi ảnh/clip sau (docs/05).
2. Tạo ảnh cảnh → kiểm mặt + chữ trong ảnh → tạo clip từ ảnh (**1 động tác / clip**).
3. Tải bản gốc về `assets/img`, `assets/clips` (link plenxai: đổi đuôi `w=400,...` thành `format=png,quality=100`).
4. Ảnh chụp sản phẩm thật (màn hình app, sản phẩm) vào `assets/img` — là "bằng chứng", có thể làm mờ chi tiết nhạy cảm.

## Bước 4 — Nhạc nền · 2 phút
`python <kit>/tools/lyria_bgm.py "<prompt tiếng Anh>" bgm/a.wav --seed 11` (docs/06) — tạo 2 đoạn rồi nối nếu video > 32s,
hoặc chọn nhạc có sẵn: `python <kit>/tools/sfx_search.py --kind bgm`. **Người duyệt nghe.**

## Bước 5 — Dựng cảnh
- **Cách nhanh (khung mẫu):** điền `scenes.json` (mỗi câu 1 cảnh, 4 kiểu: media/screenshot/logo/cta) → `python build.py`.
- **Cách tuỳ biến (như ví dụ):** sửa `index.src.html` (HTML + GSAP) và `build.py` (mốc, hiệu ứng) — docs/07.
- `build.py` sinh `index.html` (có phụ đề) + `cues.json` (danh sách hiệu ứng âm thanh theo mốc).

## Bước 6 — Trộn âm
`python <kit>/tools/mix_audio.py cues.json assets/final_audio.mp3` → giọng + nhạc (tự hạ khi có giọng) + hiệu ứng (tự cân độ to).
Hiệu ứng nào nghi chói tai → ghép file nghe thử `sfx_audition.py` cho người duyệt chọn (docs/06).

## Bước 7 — Xem thử & render
```bash
python <kit>/tools/render.py . --snap 1,5,12,20          # _snap_*.png — MỞ RA XEM từng khung
python <kit>/tools/render.py . --fps 30 --audio assets/final_audio.mp3 --out video.mp4   # ~5 phút / 50s video
```

## Bước 8 — Kiểm tra & sửa vòng lặp (docs/08)
Cắt khung từ MP4, đo âm lượng, xem trên điện thoại, người duyệt xem bản đầy đủ → sửa → chạy lại từ bước bị ảnh hưởng:
| Sửa gì | Chạy lại |
| --- | --- |
| Lời đọc 1 câu | tts `--only` → build → mix → render |
| Chữ / bố cục / chuyển động | build → render |
| Hiệu ứng âm thanh | build → mix → render |
| Thay ảnh/clip | build → render |

## Thời gian & chi phí thực tế (video StradeVn v2, 54s)
Kịch bản + duyệt ~2 giờ (nhiều vòng hook) · giọng 9 câu ~0,05 USD · nhạc 3 lần Lyria 0,18 USD · 3 ảnh flare ~21 credit +
4 clip omni-flash · render mỗi lần ~5 phút. Xem docs/10.
