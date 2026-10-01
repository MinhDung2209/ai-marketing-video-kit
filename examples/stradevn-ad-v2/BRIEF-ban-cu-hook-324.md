# StradeVn — Video quảng cáo v2 (kịch bản sản xuất chi tiết)

Ngày: 30/09/2026 · Trạng thái: **bản sản xuất v2** (người phụ trách duyệt lời đọc trước khi đăng).
Dùng kèm: `voice.json` (giọng), `cues.json` (âm thanh), `index.src.html` (dựng cảnh).

---

## 0. Thông số

| Mục | Giá trị |
| --- | --- |
| Mục tiêu | Người làm Sales XNK / chủ DN nhỏ dừng lướt → nhắn Zalo đặt demo |
| Kênh | Facebook/Instagram Reels, TikTok, Facebook Ads (feed dọc) |
| Khung | **9:16 · 1080×1920 · 30 fps** (bản 1:1 và 16:9 xuất sau từ cùng dự án) |
| Độ dài | 42–48 giây (theo thời lượng giọng thật) |
| Giọng | Gemini-TTS `gemini-3.1-flash-tts-preview` · giọng **Kore** (nữ, miền Bắc) — người phụ trách chốt 30/09 |
| Nhạc nền | Lyria (Vertex) tạo riêng, không lời, ~110 BPM; dự phòng: `bgm/mixkit/house-vibez.mp3` |
| Phụ đề | Luôn bật (≥ 70% người xem tắt tiếng): theo cụm câu, chữ trắng nền tối, vùng y 1480–1720 |
| Nhận diện | Logo thật `logo.jpg` (S cam + sao vàng) — **chỉ chèn file thật**, không để AI vẽ; indigo #4F46E5, cam #F97316, vàng #FBBF24; font Be Vietnam Pro 800 / IBM Plex Sans |
| Dữ liệu thật | Tổ chức "Công ty XNK Demo", chiến dịch **Dứa đóng lon HS 200820**: 988 công ty · 36 quốc gia · 324 Top 1–2; chiến dịch 102 cty: Top 1 = 69, Top 2 = 10 |

**Luật nội dung (bắt buộc):** không bịa số liệu; không hứa kết quả ("chắc chắn có đơn"); không nêu tên nguồn
dữ liệu; không lộ email/SĐT thật (làm mờ); không nói "AI truy xuất" (truy xuất là hệ thống, AI chỉ chấm điểm);
không ghi "miễn phí" khi chưa có chính sách.

---

## 0b. KOL — nhân vật dẫn chuyện (dùng xuyên suốt, PHẢI đồng bộ)

| Mục | Quy định |
| --- | --- |
| Vai | **Người dẫn chuyện / MC của StradeVn** — nói với người xem. **Không** đóng vai khách hàng, không nói "tôi đã kiếm được…" (lời chứng thực giả). |
| Ngoại hình | Nữ Việt ~28 tuổi, tóc búi cao, gương mặt như ảnh gốc `01-kol-met.png` |
| Trang phục | Áo sơ mi xanh nhạt. Cảnh "trước" (nỗi đau): áo trơn. Cảnh "sau" (dùng StradeVn) + kết: áo có **logo thêu nhỏ ngực trái** (như `03-kol-cuoi.png`). |
| Giọng | Giọng đọc Gemini TTS Kore là "giọng" của KOL — cảnh KOL nhìn máy quay thì lời đọc là lời của cô ấy. |
| Ảnh gốc để giữ mặt | `01-kol-met.png` → link `https://images.plenxai.com/cdn-cgi/imagedelivery/kdQv2TNFsgg6nS5bfVdpTg/45347969-633f-4bf3-8837-e80371103700/format=png,quality=100` · `03-kol-cuoi.png` → `.../0cbb890e-3641-4156-bad9-285e49ddbd00/format=png,quality=100` |
| Cách giữ đồng bộ | Mọi ảnh/clip mới: `references_urls` (ảnh) hoặc `input_image_url` / `reference_images` (clip omni-flash) = 2 link trên + logo; prompt luôn có "the SAME woman as the reference, keep her face, hairstyle and light-blue shirt". Kiểm mặt bằng mắt trước khi dùng. |
| Xuất hiện | C1/C2 (hook, nỗi đau) · C6 (liên hệ) · C8 (kêu gọi) — tối thiểu 4 cảnh để người xem nhớ mặt. |

---

## 1. Cấu trúc (công thức Hook → Nỗi đau → Giải pháp → Bằng chứng → Kêu gọi)

| Cảnh | Nhịp | Vai trò | Cảm xúc người xem |
| --- | --- | --- | --- |
| C1 | 0–~4s | **HOOK**: con số thật khổng lồ | "Hả? 324 khách?" |
| C2 | ~4–10s | Nỗi đau cách làm cũ | "Đúng mình rồi" |
| C3 | ~10–15s | Giải pháp: nhập mã HS | "Dễ vậy à" |
| C4 | ~15–21s | Bản đồ thị trường thật | "Xịn" |
| C5 | ~21–27s | Xếp hạng + lý do | "Tin được" |
| C6 | ~27–32s | Liên hệ có sẵn | "Dùng được ngay" |
| C7 | ~32–38s | Bằng chứng số liệu | "Có thật" |
| C8 | ~38–46s | Kêu gọi hành động | "Nhắn thử xem" |

### Phương án hook — CHỜ DUYỆT (xem đầy đủ các kiểu ở `kit/library/hooks/THU-VIEN-HOOK.md`)

Nhận xét của người phụ trách 30/09: hook "324 nhà nhập khẩu…" (D1) bắt được người **đã quan tâm**, người lướt bình
thường sẽ bỏ qua → cần hook **rộng** ở 3 giây đầu, rồi **rehook** để lọc đúng khách.

| PA | Kiểu (thư viện) | 0–3s: lời nói | 0–3s: chữ trên hình | Hình / clip AI | Rehook (~4–8s) |
| --- | --- | --- | --- | --- | --- |
| **HA (đề xuất)** 🌊 | A1 Điều lạ có thật + A2 câu hỏi bỏ ngỏ + G1 gián đoạn thị giác | "Người Mỹ, người Nga, người Tây Ban Nha… đang mua dứa đóng lon Việt Nam." | "🇺🇸 🇷🇺 🇪🇸 → 🍍 Việt Nam" (cờ vẽ bằng HTML) | **Clip omni-flash**: lon dứa lăn trên băng chuyền → cửa container đóng → tàu rời cảng; cắt sang bản đồ thật, luồng cam từ Việt Nam tới Mỹ/Nga/Tây Ban Nha/Mexico (đúng Top nước của chiến dịch 988) | KOL nhìn thẳng: "Vậy… ai đang bán cho họ?" → số **324** bật lên: "324 nhà nhập khẩu đang chờ người liên hệ." |
| HB 🌊🎯 | E1 giữa hành động + B1 lọc tệp | "Làm Sales xuất khẩu mà vẫn lật tờ khai bằng tay?" | "Dừng lại 3 giây." | **Clip omni-flash**: KOL hất xấp tờ khai, giấy bay chậm | "Xem cái này." → màn hình bản đồ thật bật ra (G4) |
| HC 🎯 | D1 con số (bản hiện tại) | "324 nhà nhập khẩu dứa đóng lon… đang chờ bạn liên hệ." | "324" đếm lên | Bản đồ thật nền tối | Nỗi đau C2 |

Số liệu dùng trong HA đều thật: Top nước của chiến dịch 988 = Mỹ 393 · Nga 106 · Mexico 87 · Tây Ban Nha 50
(ảnh `map-988.png`). Không nói "nhiều nhất thế giới", chỉ nói "đang mua".

Nếu duyệt HA: lời V1 đổi thành 2 câu (HA-1 hook + HA-2 rehook), phần thân C2→C8 giữ nguyên; clip P-H1 ở mục 3.2.

---

## 2. Kịch bản chi tiết từng cảnh

> Mốc thời gian trong ngoặc là DỰ KIẾN; mốc thật lấy từ `audio/timing.json` sau khi đọc giọng.
> Âm thanh ghi đường dẫn trong `kit/audio-library/` (xem giấy phép ở `LICENSES.md`).

### C1 — HOOK: "324" (0 → ~4,5s)
- **Lời (V1):** "Ba trăm hai mươi bốn nhà nhập khẩu dứa đóng lon [short pause] đang chờ bạn liên hệ."
  - Đạo diễn: bí ẩn, hạ giọng ở con số, rồi mở ra ở "đang chờ bạn liên hệ".
- **Hình:** ảnh chụp app thật `map-988.png` (bản đồ nền tối, luồng cam từ Việt Nam) phủ toàn khung, phóng từ
  1.35 → 1.1 tâm ở Việt Nam; lớp tối 55%.
- **Chữ/số động:** số **324** cỡ 300px màu cam #F97316 đếm 0→324 trong 1,4s (ease power2.out), rung nhẹ khi dừng;
  dưới: "nhà nhập khẩu dứa đóng lon · hạng Top 1–2" (48px, trắng 80%).
- **Âm thanh:** `sfx/pixabay/riser.mp3` (t=0, vol 0.5) · tick số `sfx/mixkit/counter/clock-tick-single.mp3`
  lặp 6 lần trong lúc đếm (vol 0.35) · khi số dừng: `sfx/pixabay/impact-bass-1.mp3` (vol 0.8).
- **Nhạc:** vào ngay tại impact (hiệu ứng "drop"), fade in 0,3s.
- **Phụ đề:** theo lời.

### C2 — NỖI ĐAU (~4,5 → ~10s)
- **Lời (V2):** "Nếu tự tìm, [short pause] bạn mất hàng giờ mỗi ngày lật tờ khai, copy từng cái tên, rồi... đoán mò."
  - Đạo diễn: đồng cảm, hơi mệt mỏi, mỉa mai nhẹ ở "đoán mò".
- **Hình:** ảnh AI `01-kol-met.png` (KOL mệt mỏi giữa chồng tờ khai, đêm). Ken Burns 1.02→1.15.
  - *Nâng cấp (tuỳ chọn, cần duyệt credit):* biến ảnh thành clip 5s bằng plenxai `omni-flash-video`
    (prompt ở mục 3.2 — P-V1). Clip AI **không có tiếng** → âm thanh do mình lồng.
- **Chữ động:** "Hàng giờ mỗi ngày" (vàng) bật lên, sau đó 3 thẻ nhỏ lần lượt bay vào rồi bị gạch chéo đỏ:
  "Lật tờ khai" · "Copy tên" · "Đoán mò".
- **Âm thanh:** `sfx/mixkit/paper/paper-page-turn-big.mp3` sột soạt giấy (vol 0.5) khi vào cảnh · mỗi thẻ bay vào:
  `sfx/pixabay/pop.mp3` (vol 0.5) · gạch chéo: `sfx/mixkit/text/marker-pen-line.mp3` (vol 0.6).
- **Chuyển cảnh sang C3:** chớp trắng 0,3s + `sfx/pixabay/whoosh.mp3`.

### C3 — GIẢI PHÁP: nhập mã HS (~10 → ~15s)
- **Lời (V3):** "Với StradeVn, [short pause] chỉ cần nhập mã HS và mặt hàng."
  - Đạo diễn: sáng lên, nhẹ nhõm, nhấn "chỉ cần".
- **Hình:** nền ảnh cảng `02-cang.png` làm mờ 14px; logo thật + chữ "StradeVn" hạ xuống; thẻ giao diện tối
  giống app (nền #161B26, viền #2B3240) với ô "Mã HS" gõ **200820**, ô "Từ khoá chính" gõ **pineapple**,
  nút indigo "Bắt đầu truy xuất & phân loại" nhấn xuống + gợn sóng.
- **Âm thanh:** logo vào: `sfx/pixabay/chime.mp3` (vol 0.5) · **mỗi ký tự gõ 1 tiếng**
  `sfx/uisfx/mechanical/typing.mp3` (vol 0.6) — đặt đúng mốc từng ký tự · nhấn nút:
  `sfx/mixkit/ui/ui-select-click.mp3` (vol 0.8).

### C4 — BẢN ĐỒ THỊ TRƯỜNG (~15 → ~21s)
- **Lời (V4):** "Hệ thống tự truy xuất tờ khai hải quan thật, [short pause] và cho bạn thấy ngay khách đang ở nước nào."
  - Đạo diễn: tự tin, nhấn "thật", "thấy ngay" gọn.
- **Hình:** ảnh AI `02-cang.png` (cảng container giờ xanh) kéo lùi 1.25→1.05; thẻ ảnh chụp app thật `map-988.png`
  bay lên từ dưới, nghiêng 3D 35°→0°, viền phát sáng cam.
- **Chữ động:** "Thấy ngay khách / ở những nước nào" (dòng 2 màu vàng).
- **Âm thanh:** thẻ bay lên: `sfx/mixkit/transition/swoosh-quick.mp3` · khi thẻ dừng:
  `sfx/mixkit/data/data-scan.mp3` (vol 0.35).

### C5 — XẾP HẠNG + LÝ DO (~21 → ~27s)
- **Lời (V5):** "Từng công ty được xếp hạng Top 1, Top 2, [short pause] kèm lý do cụ thể."
  - Đạo diễn: đếm nhịp "Top 1, Top 2", nhấn "lý do".
- **Hình:** nền gradient navy→tím; ảnh chụp app thật `ranking.png` (thẻ Top 1 = 69, Top 2 = 10, bảng có cột Hạng,
  Tần suất, Giá trị NK, Lý do) — lia ngang từ thẻ đếm sang cột **Lý do**, khung vàng phát sáng khoanh cột Lý do.
  Tên công ty trong bảng là dữ liệu thương mại công khai (không có liên hệ) — giữ.
- **Âm thanh:** lia: `sfx/mixkit/camera/zoom-swipe-fast.mp3` · khoanh Lý do: `sfx/mixkit/text/marker-pen-line.mp3`.

### C6 — LIÊN HỆ CÓ SẴN (~27 → ~32s)
- **Lời (V6):** "Chọn công ty muốn theo đuổi, [short pause] email và số điện thoại đã có sẵn."
  - Đạo diễn: nhịp nhanh, năng lượng tăng, kết dứt khoát.
- **Hình:** ảnh AI `03-kol-cuoi.png` (cùng KOL, áo có logo, cười với laptop) + thẻ liên hệ trắng trượt vào:
  badge "Top 1", 4 dòng Email / Điện thoại / Website / Mạng XH — giá trị **làm mờ**, lần lượt hiện dấu tích xanh.
- **Âm thanh:** thẻ vào: `sfx/pixabay/whoosh-short.mp3` · mỗi dấu tích: `sfx/mixkit/ui/ui-success-soft.mp3` (vol 0.6).

### C7 — BẰNG CHỨNG (~32 → ~38s)
- **Lời (V7):** "Ví dụ thật: [short pause] chín trăm tám mươi tám công ty, [short pause] ba mươi sáu quốc gia, [short pause] chỉ từ một chiến dịch."
  - Đạo diễn: công bố kết quả, hào hứng tăng dần.
- **Hình:** nền tối, bản đồ thật mờ 22% trôi ngang; nhãn "VÍ DỤ THẬT · Dứa đóng lon · HS 200820";
  số **988** công ty, **36** quốc gia, **324** Top 1–2 (vàng) lần lượt bật vào và đếm lên.
- **Âm thanh:** mỗi số: tick `clock-tick-single.mp3` lúc đếm + `sfx/pixabay/pop.mp3` khi dừng · số cuối:
  `sfx/pixabay/impact-bass-2.mp3` (vol 0.6).

### C8 — KÊU GỌI (~38 → hết)
- **Lời (V8):** "StradeVn, [short pause] trợ lý AI cho Sales xuất nhập khẩu. [short pause] Nhắn Zalo để được demo trên đúng mặt hàng của bạn."
  - Đạo diễn: ấm, tin cậy, mỉm cười, chậm lại ở "đúng mặt hàng của bạn".
- **Hình:** nửa trên ảnh AI `03-kol-cuoi.png`; logo thật + "StradeVn"; "Trợ lý AI cho Sales xuất nhập khẩu";
  nút indigo **"Nhắn Zalo đặt lịch demo"** đập nhịp; "stradevn.com · Zalo 0338 503 979".
- **Âm thanh:** logo: `sfx/mixkit/light/shimmer-sparkle-sweep.mp3` · nút xuất hiện: `sfx/pixabay/notification.mp3`.
- **Nhạc:** fade out 2,5s cuối.

---

## 3. Prompt tạo ảnh / clip AI (plenxai) — mọi request mới phải gửi duyệt trước, hạn mức 700 credit

### 3.1 Ảnh đã tạo và dùng lại (không tốn thêm)
| File | Model | Prompt tóm tắt | Credit |
| --- | --- | --- | --- |
| `01-kol-met.png` | gpt-image-2 2k | Nữ Sales Việt ~28 tuổi mệt mỏi xoa thái dương, bàn ngập tờ khai, đèn bàn ấm + cửa sổ thành phố đêm, 35mm, không chữ | 5 |
| `02-cang.png` | gpt-image-2 2k | Cảng container Việt Nam giờ xanh, cẩu giàn, tàu hàng, phản chiếu nước, 24mm, không logo | 5 |
| `03-kol-cuoi.png` | **gpt-image-2.5-flare** 2k, tham chiếu: ảnh 01 + logo | CÙNG người, áo xanh có logo thêu nhỏ, cười tự tin với laptop, văn phòng sáng, 50mm | 7 |

### 3.2 Prompt đề xuất (chưa tạo — chờ duyệt)
- **P-H1 · Clip hook HA** (`omni-flash-video`, 9:16, 6s, text-to-video, không cần ảnh đầu): "Cinematic product
  montage, photorealistic. Macro shot of golden pineapple chunks falling into shiny tin cans on a factory conveyor
  in Vietnam, cans roll forward, then a steel shipping container door swings shut, then a huge cargo ship leaves a
  Vietnamese port at golden hour. Fast, energetic cuts, shallow depth of field, no text, no brand labels."
- **P-H2 · Clip rehook KOL** (`omni-flash-video`, i2v, ảnh đầu = `03-kol-cuoi.png`, 4s): "The SAME woman turns
  to the camera, raises one eyebrow with a confident half-smile as if asking a question. Subtle push-in, bright
  office, realistic, no text."
- **P-H3 · Clip HB** (`omni-flash-video`, i2v, ảnh đầu = `01-kol-met.png`, 5s): "The SAME woman suddenly pushes the
  tall stack of customs papers off the desk, papers fly in slow motion, she looks at the camera, relieved. Realistic."
- **P-V1 · Clip C2 (ảnh → video 5s):** model **`omni-flash-video`** (người phụ trách chốt 30/09; `generate_video_omni`, `input_image_url` = ảnh đầu, `video_mode: i2v`), 9:16, 5–6s, ảnh đầu `01-kol-met.png`:
  "Cinematic slow push-in. The tired woman lowers her hands from her temples and exhales, glancing at the tall
  stacks of customs papers; loose papers flutter slightly, city lights twinkle outside, warm lamp. Realistic motion,
  natural expression, no text." (lần thử 30/09 bị timeout — thử lại khi MCP ổn định)
- **P-V2 · Clip C6:** `omni-flash-video`, ảnh đầu `03-kol-cuoi.png`: "Gentle dolly-in. The woman smiles, types briefly, then nods
  satisfied at the screen; soft daylight, subtle hair movement. Realistic, no text."
- **P-I1 · Ảnh bìa video (thumbnail):** flare 2k 9:16, tham chiếu ảnh 03 + logo: "The SAME woman holding a phone,
  looking at camera with an excited expression, bright office, space on top for a big headline. Photorealistic."

Mẹo giữ nhân vật: luôn truyền link ảnh KOL gốc vào `references_urls` + câu "the SAME woman … keep her identity".
Logo trên áo do AI vẽ chỉ gần giống — cảnh cần logo chuẩn thì chèn file thật khi dựng.

---

## 4. Nhạc nền

- Lyria prompt (đã chạy được): *"Uplifting modern corporate tech background music for a B2B SaaS social media ad,
  bright piano with warm synth pads, light driving percussion, confident and optimistic, 110 BPM, instrumental,
  no vocals"* · negative: *"vocals, singing, speech, heavy distortion, dark, sad"*.
- Lyria ra ~32s → `mix_audio.py` tự lặp + fade; hoặc tạo 2 đoạn cùng prompt, nối.
- Mức: 0.22 dưới giọng, **tự hạ khi có giọng** (sidechain), fade in 0,3s tại impact C1, fade out 2,5s cuối.

## 5. Kiểm tra trước khi đăng
- [ ] Nghe lại toàn bộ: không đọc sai / lẫn lời đạo diễn; con số đọc đúng
- [ ] Số trên hình khớp app (988 · 36 · 324 · 69 · 10)
- [ ] Logo chỉ là file thật; không lộ email/SĐT; không tên nguồn dữ liệu
- [ ] Phụ đề đúng chính tả, khớp giọng
- [ ] Âm lượng: giọng rõ, nhạc không lấn; không vỡ tiếng (đỉnh ≤ −1 dB)
- [ ] Xem trên điện thoại thật: chữ không bị che bởi nút TikTok/Reels (chừa trên 200px, dưới 300px, phải 140px)
