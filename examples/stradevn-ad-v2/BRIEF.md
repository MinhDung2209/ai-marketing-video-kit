# StradeVn — Video quảng cáo v2 · Hook "Đừng tuyển thêm Sales nữa"

Ngày: 30/09/2026 · Trạng thái: **ĐÃ DUYỆT 30/09 — đang sản xuất** (clip AI 1080p).

> Comment người phụ trách khi duyệt: hook cần bắt cả **Sales cá nhân** (vd Sales logistics) → câu 2 nói từ góc nhìn
> nhân viên: *"việc nhiều lên mà công ty không tuyển thêm người"*, sau đó phô diễn hết công cụ. Clip AI không tiếng —
> nhạc/SFX lồng khi mix. Nhép miệng theo giọng: thử sau. Dữ liệu mẫu thật làm mờ nhẹ cho uy tín. Video 1080p.
Bản cũ (hook "324 nhà nhập khẩu"): `BRIEF-ban-cu-hook-324.md`. Thư viện hook: `kit/library/hooks/THU-VIEN-HOOK.md` mục 6.

---

## 0. Thông số

| Mục | Giá trị |
| --- | --- |
| Ý tưởng lớn | **"Đừng tuyển thêm người — hãy để đội Sales hiện tại chỉ việc chốt đơn."** Hook gây tranh cãi → lý do (Sales đang mất thời gian vào việc tay chân) → StradeVn làm phần đó → đội Sales rảnh tay chốt đơn. |
| Người xem chính | **Chủ DN / trưởng phòng KD** (câu hook) **+ nhân viên Sales XNK / Sales logistics** (câu 2: "việc nhiều mà không tuyển thêm") |
| Kênh | Facebook/Instagram Reels, TikTok, Facebook Ads (feed dọc) |
| Khung | 9:16 · 1080×1920 · 30 fps |
| Độ dài | ~45–50 giây (chốt theo giọng thật) |
| Giọng | Gemini-TTS `gemini-3.1-flash-tts-preview` · **Kore** (đã chốt) — là "giọng" của KOL |
| Nhạc | Lyria `bgm/lyria-110.wav` (người phụ trách đã nghe và ưng) — hạ nhỏ khi có giọng |
| Clip AI | plenxai **`omni-flash-video`** (không tiếng → mình lồng tiếng + SFX) |
| Ảnh AI | plenxai **`gpt-image-2.5-flare`** 2k, giữ mặt KOL bằng ảnh tham chiếu |
| Nhận diện | Logo **file thật** `logo.jpg`; indigo #4F46E5 · cam #F97316 · vàng #FBBF24; Be Vietnam Pro 800 / IBM Plex Sans |
| Ví dụ thật (mờ, làm nền bằng chứng) | "Công ty XNK Demo" · Dứa đóng lon HS 200820: 988 công ty · 36 quốc gia · 324 Top 1–2; bảng Top 1 = 69 / Top 2 = 10 |

**Luật nội dung:** không bịa số/kết quả · KOL là **người dẫn chuyện**, không nói lời chứng thực ("tôi đã chốt…") ·
không nêu tên nguồn dữ liệu · làm mờ email/SĐT · không nói "AI truy xuất" (truy xuất là hệ thống; AI chấm điểm) ·
không ghi "miễn phí" · câu "đừng tuyển thêm Sales" là **lời khuyên có điều kiện** ("cho đến khi xem hết video"),
không khẳng định StradeVn thay thế con người.

---

## 1. KOL — người dẫn chuyện (đồng bộ xuyên suốt)

| Mục | Quy định |
| --- | --- |
| Vai | MC / người dẫn chuyện của StradeVn, nói thẳng với người xem |
| Ngoại hình | Nữ Việt ~28 tuổi, tóc búi cao — **mặt theo ảnh gốc** `01-kol-met.png` |
| Trang phục | Sơ mi xanh nhạt. Cảnh "trước" (C2): áo trơn. Hook (C1) + "sau" (C7–C9): áo có **logo thêu nhỏ ngực trái** |
| Link tham chiếu giữ mặt | `01-kol-met.png`: `https://images.plenxai.com/cdn-cgi/imagedelivery/kdQv2TNFsgg6nS5bfVdpTg/45347969-633f-4bf3-8837-e80371103700/format=png,quality=100` · `03-kol-cuoi.png`: `https://images.plenxai.com/cdn-cgi/imagedelivery/kdQv2TNFsgg6nS5bfVdpTg/0cbb890e-3641-4156-bad9-285e49ddbd00/format=png,quality=100` · logo: `https://stradevn.gnud.io.vn/assets/stradevn-logo-C7tWm8Le.jpg` |
| Câu bắt buộc trong mọi prompt ảnh/clip | "The SAME woman as the reference image — keep her exact face, bun hairstyle and light-blue shirt." |
| Xuất hiện | C1 · C2 · C7 · C8 · C9 (5/9 cảnh) |

---

## 2. Dòng chảy

| Cảnh | Thời gian (dự kiến) | Nhịp cảm xúc |
| --- | --- | --- |
| C1 HOOK | 0 – 4s | Sốc: "Hả, sao lại không tuyển?" |
| C2 LÝ DO | 4 – 11s | "Ừ đúng, Sales của mình mất thời gian vào việc này thật" |
| C3 REHOOK / LỜI GIẢI | 11 – 14s | "À, có công cụ làm thay" |
| C4 NHẬP MÃ HS | 14 – 18s | "Dễ vậy à" |
| C5 BẢN ĐỒ | 18 – 23s | "Xịn" |
| C6 XẾP HẠNG | 23 – 28s | "Tin được" |
| C7 LIÊN HỆ | 28 – 33s | "Dùng được ngay" |
| C8 CHỐT Ý (nối lại hook) | 33 – 39s | "Không cần thêm người — đội hiện tại chỉ việc chốt đơn" |
| C9 KÊU GỌI | 39 – ~47s | "Nhắn thử xem" |

---

## 3. Kịch bản chi tiết từng cảnh

### C1 — HOOK: xé tin tuyển dụng (0 → ~4s)
- **Lời (V1):** "Đừng tuyển thêm Sales nữa. [short pause] Ít nhất là cho đến khi xem hết video này."
  - Đạo diễn: dứt khoát, hơi "chơi lớn" ở câu đầu; câu sau hạ giọng, tinh nghịch, như đang nháy mắt.
- **Hình:** **clip AI P-C1** (omni-flash, i2v từ ảnh **I-C1**): KOL đứng giữa văn phòng sáng, cầm tờ giấy in to
  "TUYỂN SALES XUẤT KHẨU", xé đôi dứt khoát, nhìn thẳng máy quay, nhướng mày.
- **Chữ trên hình:** 0,0s chữ to trắng viền đen: **"Đừng tuyển thêm Sales nữa."** (110px, trên cùng) — lời và chữ
  giống nhau ở câu hook là chủ ý (người tắt tiếng vẫn hiểu); câu thứ hai chỉ có ở phụ đề.
- **Âm thanh:** 0,0s `sfx/mixkit/paper/paper-slice-quick.mp3` hoặc `paper-crumple-quick.mp3` đúng khung xé (vol 0.9) ·
  nhạc **chưa vào** (im lặng cho tiếng xé "đanh").
- **Phụ đề:** theo lời.

### C2 — LÝ DO: Sales đang mất thời gian vào đâu (~4 → ~11s)
- **Lời (V2):** "Việc ngày càng nhiều, mà công ty không tuyển thêm ai? [short pause] Vì thời gian của Sales đang mất vào lật tờ khai, copy từng cái tên, rồi… đoán mò."
  - Đạo diễn: câu hỏi đầu như nói hộ nỗi lòng nhân viên (hơi than thở); vế sau đồng cảm, liệt kê có nhịp, mỉa mai nhẹ ở "đoán mò".
- **Hình:** **clip AI P-C2** (omni-flash, i2v từ `01-kol-met.png`, áo trơn): KOL mệt mỏi giữa chồng tờ khai lúc đêm,
  hạ tay khỏi thái dương, thở dài; giấy khẽ bay. Ken Burns chậm nếu clip ngắn.
- **Chữ động:** "Hàng giờ mỗi ngày" (vàng) bật lên; 3 thẻ bay vào rồi bị gạch chéo đỏ: "Lật tờ khai" · "Copy tên" · "Đoán mò".
- **Âm thanh:** nhạc **vào nhỏ** (vol 0.12) từ đầu cảnh · `sfx/mixkit/counter/clock-tick-single.mp3` lặp nhẹ (không khí
  "mất thời gian") · mỗi thẻ: `sfx/pixabay/pop.mp3` · mỗi gạch: `sfx/mixkit/text/marker-pen-line.mp3`.
- **Chuyển sang C3:** `sfx/pixabay/riser.mp3` 1,2s trước cắt → chớp trắng.

### C3 — REHOOK / LỜI GIẢI (~11 → ~14s)
- **Lời (V3):** "Việc đó… [short pause] để StradeVn làm."
  - Đạo diễn: chậm, tự tin, như tiết lộ; nhấn tên thương hiệu.
- **Hình:** nền tối; logo **file thật** phóng từ 0.6→1 + tên "StradeVn" + dòng "Trợ lý AI cho Sales xuất nhập khẩu"; hạt sáng.
- **Âm thanh:** `sfx/pixabay/impact-bass-1.mp3` đúng lúc logo chạm kích thước thật (vol 0.8) · **nhạc lên đủ** (drop)
  · `sfx/mixkit/light/shimmer-sparkle-sweep.mp3` (vol 0.4).

### C4 — NHẬP MÃ HS (~14 → ~18s)
- **Lời (V4):** "Chỉ cần nhập mã HS và mặt hàng."
- **Hình:** thẻ giao diện tối giống app: ô "Mã HS" gõ **200820**, ô "Từ khoá chính" gõ **pineapple**, nút indigo
  "Bắt đầu truy xuất & phân loại" nhấn xuống + gợn sóng. Nền: ảnh cảng mờ.
- **Âm thanh:** **mỗi ký tự 1 tiếng gõ** `sfx/uisfx/mechanical/typing.mp3` (vol 0.6) · nhấn nút `sfx/mixkit/ui/ui-select-click.mp3`.

### C5 — BẢN ĐỒ THẬT (~18 → ~23s)
- **Lời (V5):** "Hệ thống tự truy xuất tờ khai hải quan toàn cầu, [short pause] cho bạn thấy ngay khách đang ở nước nào." (01/10: người phụ trách đổi "thật" → "toàn cầu")
- **Hình:** ảnh AI cảng container (`02-cang.png`) kéo lùi; **ảnh chụp app thật** `map-988.png` (bản đồ nền tối, luồng cam
  từ Việt Nam) bay lên nghiêng 3D → phẳng, viền sáng cam. Góc dưới nhãn nhỏ mờ: "Ví dụ thật · Dứa đóng lon".
- **Chữ:** "Thấy ngay khách / ở những nước nào".
- **Âm thanh:** `sfx/mixkit/transition/swoosh-quick.mp3` · `sfx/mixkit/data/data-scan.mp3` (vol 0.35).

### C6 — XẾP HẠNG + LÝ DO (~23 → ~28s)
- **Lời (V6):** "Từng công ty được xếp hạng Top 1, Top 2, [short pause] kèm lý do cụ thể."
- **Hình:** **ảnh chụp app thật** `ranking.png` (Top 1 = 69, Top 2 = 10, bảng có cột Lý do) — lia ngang sang cột
  **Lý do**, khung vàng khoanh.
- **Âm thanh:** `sfx/mixkit/camera/zoom-swipe-fast.mp3` · `sfx/mixkit/text/marker-pen-line.mp3`.

### C7 — LIÊN HỆ CÓ SẴN (~28 → ~33s)
- **Lời (V7):** "Chọn công ty muốn theo đuổi, [short pause] email và số điện thoại đã có sẵn."
- **Hình:** `03-kol-cuoi.png` (KOL áo logo, cười với laptop) + thẻ liên hệ trắng trượt vào: badge "Top 1", 4 dòng
  Email / Điện thoại / Website / Mạng XH — giá trị **làm mờ**, lần lượt tích xanh.
- **Âm thanh:** `sfx/pixabay/whoosh-short.mp3` · mỗi tích `sfx/mixkit/ui/ui-success-soft.mp3` (vol 0.6).

### C8 — CHỐT Ý, nối lại hook (~33 → ~39s)
- **Lời (V8):** "Dù bạn làm Sales xuất nhập khẩu hay logistics, [short pause] không cần thêm người. [short pause] Đội hiện tại… chỉ việc chốt đơn."
  - Đạo diễn: ấm, chắc chắn, mỉm cười ở "chỉ việc chốt đơn".
- **Hình:** **clip AI P-C8** (omni-flash, i2v từ ảnh **I-C8**): KOL (áo logo) đang gọi điện thoại, cười tươi, gật đầu
  như vừa chốt được việc, văn phòng sáng. Nền phía sau lớp mờ: số liệu ví dụ thật "988 công ty · 36 quốc gia ·
  324 Top 1–2" (mờ 35%, trôi chậm — đúng ý người phụ trách "ví dụ thật làm mờ trong clip").
- **Chữ:** "Không cần thêm người." → "Chỉ việc chốt đơn." (vàng)
- **Âm thanh:** `sfx/pixabay/notification.mp3` khi KOL cười (như có tin nhắn khách) · `sfx/pixabay/pop.mp3` ở chữ vàng.

### C9 — KÊU GỌI (~39 → hết)
- **Lời (V9):** "StradeVn, [short pause] trợ lý AI cho Sales xuất nhập khẩu. [short pause] Nhắn Zalo để được demo trên đúng mặt hàng của bạn."
  - Đạo diễn: kết ấm, tin cậy; lời mời thân thiện, chậm lại ở "đúng mặt hàng của bạn".
- **Hình:** nửa trên `03-kol-cuoi.png`; logo thật + "StradeVn"; "Trợ lý AI cho Sales xuất nhập khẩu"; nút indigo
  **"Nhắn Zalo đặt lịch demo"** đập nhịp; "stradevn.com · Zalo 0338 503 979".
- **Âm thanh:** `sfx/mixkit/ui/ui-confirm-tone.mp3` khi nút hiện · nhạc fade out 2,5s cuối.

---

## 4. Ảnh & clip AI cần tạo (plenxai) — CHỜ DUYỆT, trong hạn mức 700 credit

| Mã | Loại | Model | Tham chiếu / ảnh đầu | Prompt |
| --- | --- | --- | --- | --- |
| **I-C1** | Ảnh 9:16 2k | gpt-image-2.5-flare (~7 cr) | `03-kol-cuoi` + logo | "Photorealistic vertical photo. The SAME woman as the reference image — keep her exact face, bun hairstyle and light-blue shirt with the small embroidered logo from the logo reference on the left chest. She stands in a bright modern open-plan office, holding up a large printed A3 sheet with bold black Vietnamese text 'TUYỂN SALES XUẤT KHẨU' facing the camera, confident slight smirk, looking straight at the camera. Soft daylight, 35mm, shallow depth of field, realistic skin. No other text." |
| **P-C1** | Clip 5s | omni-flash-video (i2v) | ảnh đầu = I-C1 | "The SAME woman firmly rips the printed sheet in half, lets the two pieces fall, then looks straight into the camera and raises one eyebrow with a knowing half-smile. Handheld camera, slight push-in, realistic motion, bright office. No added text." |
| **P-C2** | Clip 5–6s | omni-flash-video (i2v) | ảnh đầu = `01-kol-met.png` | "Cinematic slow push-in. The SAME tired woman lowers her hands from her temples and exhales, glancing at the tall stacks of customs papers; loose papers flutter slightly, city lights twinkle outside, warm desk lamp. Realistic motion, natural expression, no text." |
| **I-C8** | Ảnh 9:16 2k | gpt-image-2.5-flare (~7 cr) | `03-kol-cuoi` + logo | "Photorealistic vertical photo. The SAME woman as the reference — exact face, bun hairstyle, light-blue shirt with the small embroidered logo — sitting at a bright tidy desk, talking on her phone with a big genuine smile, laptop open (screen facing away), notebook with a checklist. Warm daylight, 50mm, shallow depth of field. No text." |
| **P-C8** | Clip 5s | omni-flash-video (i2v) | ảnh đầu = I-C8 | "The SAME woman laughs softly on the phone, nods, and gives a small fist pump of success, then writes a quick note. Gentle dolly-in, realistic motion, bright office, no text." |

Dự kiến credit: 2 ảnh × ~7 = ~14 cr + 3 clip omni-flash (giá chưa biết — lần gọi đầu sẽ ghi lại vào sổ chi).
Ảnh/clip mới phải kiểm mặt KOL + chữ "TUYỂN SALES XUẤT KHẨU" đúng chính tả trước khi dùng; sai → tạo lại (ghi sổ).

---

## 5. Nhạc & mix
- Nhạc: `bgm/lyria-110.wav`. C1 im lặng (tiếng xé giấy) → C2 vào nhỏ 0.12 → **C3 drop lên 0.22** → tự hạ khi có giọng
  → fade out 2,5s cuối.
- Giọng 1.0 · SFX 0.3–0.9 tuỳ loại · giới hạn đỉnh −1 dB (`mix_audio.py` có sẵn limiter).

## 6. Phụ đề
- Theo cụm (`captions.py`), chữ trắng nền tối, vùng y 1480–1720; chừa vùng an toàn TikTok/Reels (trên 200px, dưới 300px, phải 140px).

## 7. Kiểm tra trước khi đăng
- [ ] Nghe hết: không đọc sai / lẫn lời đạo diễn; "StradeVn" đọc rõ
- [ ] Mặt KOL giống nhau ở mọi cảnh; chữ trên tờ tuyển dụng đúng chính tả
- [ ] Số trên hình khớp app; ví dụ thật có nhãn "Ví dụ thật"
- [ ] Logo chỉ là file thật; không lộ email/SĐT; không tên nguồn dữ liệu
- [ ] Âm lượng: giọng rõ, nhạc không lấn; tiếng xé giấy ở giây 0 rõ
- [ ] Xem trên điện thoại thật: chữ không bị nút nền tảng che
