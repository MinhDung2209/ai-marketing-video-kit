# 18 · Clip "ngành hàng trước, sản phẩm sau" (genre `nganh-hang`)

Mẫu chuẩn là clip 10 ngành dừa (`stradevn-video/clips/10-nganh-dua`, ngày 12/11/2026).
Chủ app duyệt hướng này sau khi chê 9 clip đầu: cùng một mô-típ "lên webapp làm", lặp tính năng, chuyển đề tài cụt.

## Khung 60–75 giây

| Đoạn | Giây | Hình | Lời |
|---|---|---|---|
| Hook ngành | 0–5 | `st.broll` ảnh/video ngoài + thẻ chữ to | một câu hỏi/nghịch lý về ngành ("Hộp nước dừa ở châu Âu, ruột là dừa nước nào?") |
| Bằng chứng | 5–17 | quay app, 1 màn hình | trả lời hook bằng số thật trong app (Vita Coco: ~15 triệu USD, 100 lô gần nhất đều Philippines) |
| Bàn về ngành | 17–36 | 2–3 `st.broll` | 2–3 ý có nguồn báo (diện tích, kim ngạch, điểm nghẽn) → câu nối tự nhiên sang việc bán hàng |
| Tính năng | 36–53 | quay app, ĐÚNG 1 tính năng | thao tác ít, ra kết quả ngay (gõ tên công ty → họ bán gì, cho ai) |
| Chi phí / dùng thử | 53–61 | trang /pricing | "Gói Trải nghiệm chỉ từ 599.000đ/tháng" (số đọc từ app hôm quay) |
| CTA tò mò | 61–68 | `logo_end` | câu hỏi rủ người xem tự thử bằng mặt hàng/khách của họ |

## Luật

- Trước khi viết, đọc `stradevn-video/KE-HOACH-NOI-DUNG.md` và `content-db/`.
  - Chọn tổ hợp ngành × tính năng × hook chưa dùng.
  - Ghi tổ hợp đã chọn vào `ledger.json`.
- Mỗi clip dùng 1 tính năng chính, tối đa 2.
- Cấm các hook: "lô hàng X → ai mua", "khách của đối thủ", "Người ta xuất được sao mình chưa".
- Số ngành phải có link báo, ghi vào `voice.json._huong_dan`.
- Số trong app phải đọc bằng `status.py` ngay hôm quay.
- Lời đọc không nêu nguồn dữ liệu XNK và không dùng chữ "tờ khai". Thay "tờ khai" bằng "lô hàng".
- Quay web nguyên trạng. Bước `js` chỉ dùng để cuộn.

## Hình ngoài (b-roll)

1. `sources.json` liệt kê cảnh cần hình. Chạy `python KIT/tools/find_sources.py <clip>`.
   - Khoá Pexels/Pixabay đã có trong `config.json`.
   - Xem `sources/contact-sheet.jpg`, rồi chạy `--fetch id:hạng`.
2. Cắt về khung nội dung 1080×1350, không tiếng, dài 5–9 giây:
   ```
   ffmpeg -ss <s> -t 9 -i assets/src/x.mp4 -an -vf "scale=-2:1350,crop=1080:1350,fps=30" -c:v libx264 -crf 21 -pix_fmt yuv420p assets/broll/x.mp4
   ```
   - Ảnh: `scale=1200:1500:force_original_aspect_ratio=increase,crop=1200:1500`.
3. Trong `story.py`:
   ```python
   st.broll("assets/broll/x.mp4", [P("V3", 0, 3)], tags=[(1, "~200.000 ha dừa")])
   ```
   - Ken Burns chậm có sẵn.
   - Video ngắn hơn lời thì tự phát chậm, tối thiểu 0,5×.
   - `tags` = thẻ chữ to, hiện lúc bắt đầu nói cụm thứ k.
   - Mỗi thẻ ≤ 5 chữ, số giống hệt lời đọc.
4. Tránh ảnh có logo thương hiệu thật rõ. Ảnh phải khớp câu đang đọc (kệ hàng ↔ "trên kệ siêu thị").

## Bắt đầu clip mới

```
python KIT/screendemo/new_clip.py <clip> --profile stradevn --genre nganh-hang
```

Sau đó thay toàn bộ lời, `sources.json` và `shots.json` theo ngành mới. Quy trình còn lại như doc 12:
dryrun → shoot → tts_script + tts_qa → produce --build → --snap → render nền → vqa → to_studio.
