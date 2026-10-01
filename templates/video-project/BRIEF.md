# [Tên sản phẩm] — Video [số] · Hook "[câu hook]"

Ngày: [ngày] · Trạng thái: [NHÁP / CHỜ DUYỆT / ĐÃ DUYỆT]
Ví dụ đầy đủ đã làm thật: `kit/examples/stradevn-ad-v2/BRIEF.md` — đọc trước khi viết.

## 0. Thông số
| Mục | Giá trị |
| --- | --- |
| Ý tưởng lớn (1 câu) | |
| Người xem chính / phụ | |
| Kênh | Reels / TikTok / Facebook Ads |
| Khung | 9:16 · 1080×1920 · 30 fps |
| Độ dài | 30–60 giây |
| Giọng | Gemini-TTS `gemini-3.1-flash-tts-preview` · giọng … |
| Nhạc | Lyria (prompt ở mục 5) / nhạc mở trong audio-library |
| Nhận diện | logo FILE THẬT · màu … · font … |
| Số liệu thật dùng làm bằng chứng | (nguồn, ngày chụp) |

**Luật nội dung:** không bịa số/kết quả · KOL AI là người dẫn chuyện, không nói lời chứng thực · không hứa kết quả ·
không lộ dữ liệu cá nhân · không dùng chữ "miễn phí"/"số 1" khi chưa có căn cứ.

## 1. KOL (nếu có)
| Mục | Quy định |
| --- | --- |
| Vai | Người dẫn chuyện |
| Ngoại hình / trang phục | |
| Link ảnh gốc giữ mặt | (link công khai — plenxai) |
| Câu bắt buộc trong prompt | "The SAME woman/man as the reference image — keep exact face, hairstyle and outfit." |

## 2. Dòng chảy (Hook → Nỗi đau → Lời giải → Bằng chứng → Kêu gọi)
| Cảnh | Giây | Nhịp cảm xúc |
| --- | --- | --- |
| C1 HOOK | 0–4 | |
| C2 | | |

## 3. Chi tiết từng cảnh (chép khối này cho mỗi cảnh)
### C1 — [tên cảnh]
- **Lời (V1):** "…"  · Đạo diễn: …
- **Hình:** ảnh / clip AI (mã P-…) / ảnh chụp sản phẩm thật
- **Chữ trên hình:** …
- **Âm thanh:** `sfx/...` (tìm: `python tools/sfx_search.py <từ khoá>`; nghe thử: `tools/sfx_audition.py`)
- **Phụ đề:** theo lời

## 4. Ảnh & clip AI cần tạo — GỬI DUYỆT TRƯỚC, ghi sổ credit
| Mã | Loại | Model | Tham chiếu / ảnh đầu | Prompt |
| --- | --- | --- | --- | --- |
| I-… | Ảnh 9:16 2k | gpt-image-2.5-flare | | |
| P-… | Clip 6s | omni-flash-video (i2v) | | **1 động tác đơn giản / clip** |

## 5. Nhạc & mix
- Prompt Lyria: *thể loại + mục đích + nhạc cụ + cảm xúc + BPM + "instrumental, no vocals"*
- Nhạc vào lúc: … · hạ khi có giọng · fade out 2,5s

## 6. Kiểm tra trước khi đăng
- [ ] Nghe hết: không đọc sai / lẫn lời đạo diễn
- [ ] Mặt KOL đồng bộ; chữ trong ảnh AI đúng chính tả; logo là file thật
- [ ] Số trên hình khớp nguồn; có nhãn "ví dụ thật"
- [ ] Không SFX chói tai (đã nghe thử); giọng rõ, nhạc không lấn
- [ ] Xem trên điện thoại thật; chữ không bị nút nền tảng che
