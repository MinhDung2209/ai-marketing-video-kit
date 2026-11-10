# 16 · Thiết kế âm thanh tự động (Sound Plan & HyperFrames Mixing)

Tài liệu này tóm tắt các quy tắc phối âm chuẩn chuyên nghiệp (HyperFrames media-use) cho video screen-demo, và cách một mô hình AI (kể cả model yếu) áp dụng tự động vào clip.

---

## 1. Bản tóm tắt quy tắc (Core Audio Rules)

### A. Nhạc nền (BGM) theo Narrative Archetype
Mỗi thể loại video cần một archetype âm nhạc phù hợp với tâm lý người xem:
* **PAS (Problem → Agitation → Solution):** Cấu trúc hợp âm chuyển từ **MINOR sang MAJOR** (tạo căng thẳng ở vấn đề và bừng sáng khi đưa ra giải pháp).
* **Feature Cascade:** Tăng tốc **+~10 BPM** (nhịp dồn dập, tạo động lực khám phá nhiều tính năng liên tiếp).
* **Demo / Loop Clip:** Giảm **-~8 BPM** (âm điệu tối giản, groove nhẹ nhàng, nhịp đập ổn định, loop mượt).
* **SaaS / Tech Mặc định:** Uplifting corporate tech, piano sáng kết hợp synth pad ấm, ~108 BPM.
* **Promo:** Brightness $\ge 0.7$, scale trưởng (Major).

**Prompt Lyria tự động:**
Hệ thống tự động sinh prompt tiếng Anh theo công thức:
`"<base instrument & feel>, <archetype modifiers>, <scale>, <tempo> BPM, instrumental, no vocals"`
kèm negative prompt: `"vocals, singing, speech, heavy distortion, harsh noise, muddy mix"`.

### B. Best Entry (Điểm vào nhạc sạch nhất)
* Dùng `ffmpeg ebur128` quét các cửa sổ 5s (từ 0s đến 30s).
* Nếu đoạn đầu intro quá nhỏ/rề rà ($< -25$ LUFS) trong khi đoạn sau có drop/beat mạnh mẽ, tự động dịch `offset` đến điểm vào chắc chắn nhất.
* **Fade:** Clip thường dùng fade-in 0.5s, fade-out 2.2s.
* **Loop clip (video nối vòng):** Fade-in 0.05s, fade-out 0.15s để âm thanh liền mạch tuyệt đối khi lặp lại, phủ kín toàn bộ độ dài không có khoảng lặng cuối.

### C. Accent SFX theo nhịp (Beat-aligned Accents)
* **Riser (Swell):** Phải kết thúc **chính xác tại thời điểm reveal** (`start = reveal_time - riser_duration`, đo bằng thời lượng thực qua ffprobe).
* **Hit / Impact:** Nổ chính xác vào từ khoá xuất hiện (reveal word). Nếu chưa có bảng khớp từ (word alignment), ước lượng theo tỉ lệ ký tự trong câu (`estimated_per_char`).
* **Tránh va chạm:**
  * **TUYỆT ĐỐI KHÔNG** đặt accent đè hoặc cách meme $< 0.6$s.
  * Khoảng cách giữa 2 accent tối thiểu $0.6$s.
  * Giữ nguyên whoosh chuyển cảnh của engine, không nhân đôi.
* **Trần mật độ (Density Cap):** $\le 1$ cụm accent trong mỗi khoảng 4s ($\le 15$ accents/phút), không bao giờ đè to hơn giọng đọc.
* **Tìm kiếm SFX cụ thể:** Luôn tìm theo tên âm thanh cụ thể (ví dụ `'camera shutter'`, `'cash register'`, `'chime'`, `'sparkle'`, `'impact'`), không tìm bằng tính từ trừu tượng như `'dramatic'`.

### D. Chuẩn trộn âm lượng (HyperFrames Compliant Mixing)
* **Voice (Giọng đọc):** Bus âm lượng chuẩn 1.0 (chuẩn -0 dBFS tham chiếu).
* **BGM (Nhạc nền):** Bed volume $\approx 0.12$. Tự động **ducking** xuống multiplier $0.35$ (khoảng -9 dB thêm) khi đang có giọng đọc, nhả về nguyên bản trong khoảng nghỉ.
* **Voice-band Carve:** Cắt giảm dải tần số giọng nói ($1\text{–}4$ kHz, peak EQ tại 2500 Hz, width 2000 Hz, gain -4 dB) trên track BGM trong lúc người đọc đang nói.
* **SFX Bus:** Chuẩn đỉnh $-6$ dB rồi nhân volume $\approx 0.35$ (nằm êm dưới giọng đọc).
* **Output Master:** True Peak $< -1$ dBTP (alimiter limit = 0.891), Integrated Loudness $-14$ LUFS $\pm 1$.

---

## 2. Cách khai báo trong `story.py` (Dành cho AI / Model yếu)

### Cách 1: Bật tự động nhận diện
Chỉ cần thêm `sound='auto'` khi khởi tạo `Story`:
```python
st = Story(HERE, variant=V, brand=BR, sound="auto")
```
Engine sẽ tự động phân tích `clip.json`, `BRIEF.md`, các cụm lời nói trong `st.pieces`, tự tìm các từ khoá thương hiệu / tính năng để bố trí riser & hit.

### Cách 2: Khai báo reveals tường minh (Khuyên dùng)
Gọi hook `st.sound_plan(reveals=[...])`:
```python
st.sound_plan(reveals=[
    # 1. Reveal tại mốc giây cụ thể (t=0s mở màn ấn tượng)
    {"time": 0.0, "hit": "impact", "riser": False},

    # 2. Reveal theo ID câu đọc và từ khoá (tự tính vị trí từ, kèm riser build-up)
    {"line": "V2", "word": "StradeVn", "hit": "impact", "riser": "riser"},

    # 3. Reveal nhẹ nhàng (chime/chuông) cho đáp án
    {"line": "V5", "word": "Harris", "hit": "chime", "riser": False},

    # 4. Reveal điểm nhấn email / tính năng tự động (sparkle)
    {"line": "V7", "word": "email", "hit": "sparkle", "riser": False},

    # 5. Dạng viết tắt tuple ("V9", "StradeVn") hoặc số thực
    ("V9", "StradeVn"),
])
```

---

## 3. Quy trình build & Kiểm định chất lượng (VQA)

Khi chạy build, hệ thống tự sinh `sound_plan.json` chứa đầy đủ brief BGM, offset Best Entry, danh sách accent và ma trận mixing.

Kiểm tra tự động bằng bộ công cụ VQA:
```bash
python tools/vqa/run.py <thư_mục_clip> --stage build
```

Các bài kiểm tra tự động bao gồm:
1. `sfx_timing`: Kiểm tra riser kết thúc trong vòng $\pm 0.15$s quanh mốc reveal; không có 2 accent cách nhau $< 0.6$s; không accent nào lấn vào vùng meme; mật độ accent $\le 1 / 4$s.
2. `bgm_entry`: Nhạc nền không vào muộn quá 0.5s; nhạc phủ trọn vẹn thời lượng video không để đuôi cụt; loop clip có fade out $\le 0.25$s.
