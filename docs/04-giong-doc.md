# 04 · Giọng đọc AI (Google Gemini-TTS)

## 1. Chọn model — đo thật 30/09/2026
| Model | Ghi chú | Giá |
| --- | --- | --- |
| **`gemini-3.1-flash-tts-preview`** ✅ | Người duyệt nghe: cảm xúc "đỉnh". Bản preview — Google có thể đổi | 1 USD/1M token chữ vào + 20 USD/1M token âm ra (25 token = 1 giây) |
| `gemini-2.5-pro-tts` | Bản chính thức, dự phòng khi 3.1 bị gỡ | như trên |
| `gemini-2.5-flash-tts` | Rẻ hơn (0,5 / 10 USD) | |
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
