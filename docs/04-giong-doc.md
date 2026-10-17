# 04 · Giọng đọc AI (Google Gemini-TTS)

## 1. Chọn model — đo thật 30/09/2026
| Model | Ghi chú | Giá |
| --- | --- | --- |
| **`gemini-3.1-flash-tts-preview`** ✅ | Người duyệt nghe: cảm xúc "đỉnh". Bản preview — Google có thể đổi | 1 USD/1M token chữ vào + 20 USD/1M token âm ra (25 token = 1 giây) |
| `gemini-2.5-pro-tts` | Bản chính thức, dự phòng khi 3.1 bị gỡ | như trên |
| `gemini-2.5-flash-tts` | **Dự phòng tự động** khi 3.1 lỗi hẳn (`tts_fallback_model`). Cùng Cloud TTS, cùng prompt | 0,5 / 10 USD |
| `gemini-3.8-flash-tts` | Ra sau 3.1, rẻ hơn. **KHÔNG chạy qua Cloud TTS** ("not supported") — chỉ Vertex `generateContent`, location `global`. Cách prompt KHÁC hẳn → mục 2b | 0,5 / 9 USD (đến 31/12/2026; từ 2027: 1 / 18) |
| Chirp3-HD (`vi-VN-Chirp3-HD-Kore`…) | Đều, phẳng — người duyệt chê "lỏ"; miễn phí 1 triệu ký tự/tháng | 30 USD/1M ký tự |
Giọng dùng: **Kore** (nữ, miền Bắc qua lời dặn). Giọng khác: Aoede, Puck (nam), Charon (nam trầm)…

## 2. Gemini-TTS KHÔNG nhận SSML — điều khiển bằng 3 lớp
1. **`profile`** (chung mọi câu): ai đọc, vùng miền, không khí, **tốc độ**.
   > "Bạn là nữ MC quảng cáo người Việt, giọng miền Bắc chuẩn, ấm, tự tin… Tuyệt đối không đọc đều đều như máy; có nhấn nhá, có lên xuống. Nhịp hơi nhanh, gọn."
2. **`direction`** (riêng từng câu): nhấn chữ nào, cảm xúc gì.
   > "Câu đầu dứt khoát, hơi 'chơi lớn'. Câu sau hạ giọng, tinh nghịch như đang nháy mắt."
3. **Thẻ trong lời:** `[short pause]` `[medium pause]` `[long pause]` `[whispering]` `[shouting]` `[extremely fast]`
   `[sigh]` `[laughing]` `[uhm]`. `...` = ngập ngừng; chữ VIẾT HOA = nhấn (phụ đề tự đổi về chữ thường).
(Chirp3-HD thì nhận SSML: `<break> <prosody> <say-as> <sub> <p> <s> <phoneme>`, không có `<emphasis>`.)

## 2b. Gemini 3.8 Flash TTS — cách prompt KHÁC 3.1 (theo hướng dẫn Google, đọc 17/10/2026)
Gọi: `POST https://aiplatform.googleapis.com/v1/projects/<project>/locations/global/publishers/google/models/gemini-3.8-flash-tts:generateContent`
```json
{"contents": [{"role": "user", "parts": [{"text": "Imagine this... <short pause> is your TUESDAY morning.",
                                         "speechMetadata": {"style": "warm, calm documentary narration, speaking slowly"}}]}],
 "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {"voice": "Algenib"}}}}
```
Trả về WAV (base64 trong `inlineData.data`).
- **`text` = lời NGUYÊN VĂN.** Viết lời dặn vào `text` → có thể bị đọc to / đọc lan (đã gặp: thêm 30s âm thanh lạ).
- **`style` NGẮN** (vài từ): cảm xúc, nhịp ("speaking slowly"), cao độ. **Không** ghi tuổi/vùng miền/giới tính — chọn bằng giọng.
- **KHÔNG dùng profile dài** kiểu "Audio Profile / Director's Notes" của 3.1 — Google ghi đó là nguyên nhân chính làm giọng trôi (drift).
  Thử `style` trống trước; giữ 1 chuỗi style gốc giống hệt mọi lượt, chỉ thêm vài từ ở lượt cần.
- **Cảm xúc đổi → tách lượt riêng**, mỗi lượt một style. Câu dài → chia lượt ngắn, đừng tăng prompt.
- **Thẻ ngoặc NHỌN** trong lời (khác 3.1 dùng ngoặc vuông): `<short pause>` `<long pause>` `<breath>` `<sigh>` `<chuckle>`
  `<whispers>`… Chỉ âm thanh của người, không hiệu ứng (vỗ tay…). Lời không phải tiếng Anh vẫn để thẻ tiếng Anh.
- **Nhấn** = chữ VIẾT HOA + dấu câu (`,` `--` `...`). Viết lời như người nói thật.
- Không có tham số tốc độ: dùng style "speaking slowly/rapidly", dấu câu và thẻ ngắt. **Đừng kéo giãn (atempo) sau khi đọc** — chữ bị lề rề.
- Kiểm tra độ dài mỗi lượt: dài > ~150% so với dự kiến → tạo lại (model đôi khi đọc lan).
Nguồn: ai.google.dev/gemini-api/docs/speech-generation · docs.cloud.google.com/gemini-enterprise-agent-platform/models/text-to-speech/prompting-guide

## 2c. ElevenLabs qua AI33 (`tools/ai33.py`) — đã thử 17/10/2026
- `/v3/text-to-speech` chỉ nhận `voice_id`, `text`, `speed`, `model_id` (vd `eleven_v3`). **Bỏ qua** stability/similarity/style.
- `speed` ≠ 1 = kéo giãn SAU khi đọc (`postprocess_speed`) → chữ lề rề. Để 1.0.
- eleven_v3 hiểu thẻ ngoặc vuông `[calm]` `[pause]`, chữ HOA nhấn — nhưng nhấn nhá vẫn kém Gemini có prompt (người duyệt chê).
- Voice changer (`/v1/task/voice-changer`) nhận đủ voice_settings, giữ nhịp của file nguồn (vd Gemini → Adam); ~2.300 credit/phút.

## 3. Tốc độ — bài học
Bản đầu người duyệt thấy "hơi chậm" → thêm vào profile "nhịp hơi nhanh, gọn". **Đừng** chỉnh ngược chiều khi chưa rõ
(1 lần đã sửa chậm hơn vì hiểu nhầm). Mỗi lần đọc lại vẫn giữ cảm xúc nếu chỉ đổi dòng tốc độ.

## 4. Số & phụ đề
Số đọc bằng chữ để đọc đúng ("chín trăm tám mươi tám"); thêm `"caption": "... 988 công ty ..."` để phụ đề hiện số.
`caption` còn dùng để **đặt điểm cắt phụ đề** bằng `[short pause]` (tránh tách "tờ / khai").

## 5. Bộ lọc an toàn chặn nhầm (gặp nhiều lần)
Lỗi `400 … violates Vertex AI's usage guidelines` với câu hoàn toàn bình thường, **ngẫu nhiên**, phụ thuộc tổ hợp profile +
câu chữ (vd "kèm lý do rõ ràng cho từng công ty" bị chặn, "lý do cụ thể" thì qua). `tts_script.py` tự xử lý:
2 lần profile chính → 2 lần `profile_fallback` → 1 lần **không kèm lời đạo diễn** (in ⚠ để nghe lại). Vẫn lỗi → đổi vài chữ.

## 6. Lệnh
```bash
python <kit>/tools/tts_script.py voice.json audio                 # đọc hết
python <kit>/tools/tts_script.py voice.json audio --only V5       # chỉ đọc lại V5 (câu khác giữ nguyên cảm xúc đã duyệt)
python <kit>/tools/tts_script.py voice.json audio --model gemini-2.5-pro-tts --voice Aoede   # thử model/giọng khác
```
Ra: `audio/V1..mp3`, `audio/narration.mp3` (đã ghép, cách nhau `gap_seconds`), `audio/timing.json` (mốc bắt đầu/độ dài).

## 7. Nhép miệng (lip-sync)
Chưa làm. Clip AI hiện không nói; giọng là lời dẫn. Muốn KOL nhép theo giọng: thử tính năng lip-sync của nền tảng video AI
(chưa kiểm chứng trong bộ này).
