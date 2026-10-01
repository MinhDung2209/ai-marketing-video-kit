# 06 · Âm thanh: nhạc nền, hiệu ứng, trộn

## 1. Nhạc nền
**Lyria (Vertex AI) — nhạc riêng, không đụng hàng** (người duyệt chọn bản này cho StradeVn v2):
```bash
python <kit>/tools/lyria_bgm.py "Uplifting modern corporate tech background music for a B2B SaaS social media ad, bright piano with warm synth pads, light driving percussion, confident and optimistic, 110 BPM, instrumental, no vocals" bgm/a.wav --seed 11
python <kit>/tools/lyria_bgm.py "<cùng prompt>" bgm/b.wav --seed 12          # seed khác để 2 đoạn không giống hệt
ffmpeg -i bgm/a.wav -i bgm/b.wav -filter_complex "acrossfade=d=3:c1=tri:c2=tri" bgm/nhac.wav   # nối mềm → ~62s
```
Công thức prompt: **thể loại + mục đích + nhạc cụ + cảm xúc + BPM + "instrumental, no vocals"**; negative mặc định
"vocals, singing, speech, heavy distortion". Mỗi lần ~32s, 0,06 USD. (Lyria 3 / Lyria 3 Pro rẻ hơn / tạo cả bài — chưa thử.)

**Nhạc mở có sẵn:** `python <kit>/tools/sfx_search.py --kind bgm` → 4 bài Mixkit (house, hip hop) + bản Lyria mẫu.
Nguồn thêm (tự kiểm giấy phép từng bài): Mixkit Music, Pixabay Music; Kevin MacLeod (CC-BY, **phải ghi nguồn**);
FMA/ccMixter (tránh bài **NC** = cấm thương mại).

## 2. Hiệu ứng âm thanh (SFX) — thư viện `audio-library/`
| Nguồn | Số file | Giấy phép |
| --- | --- | --- |
| `sfx/pixabay/` (từ HyperFrames) | 19 | Pixabay Content License — thương mại, không cần ghi nguồn |
| `sfx/mixkit/<nhóm>/` (từ video-shotcraft) | 148 | Mixkit Free License — chỉ nhận file có URL gốc |
| `sfx/uisfx/<12 bộ>/` | 936 | CC0 1.0 |
Giấy phép + nguồn **từng file**: `audio-library/catalog.json`. KHÔNG dùng soundcn (lẫn 110 âm thanh © Blizzard).

Tìm: `python <kit>/tools/sfx_search.py typing` · `whoosh --max 1.5` · `paper` · `pop` · `click` · `riser` · `impact`

**Gợi ý theo hoạt ảnh (đã dùng trong v2):**
| Hoạt ảnh | Âm thanh |
| --- | --- |
| Gõ chữ từng ký tự | `sfx/uisfx/mechanical/typing.mp3` — **1 tiếng / ký tự**, đúng mốc |
| Chuyển cảnh | `sfx/mixkit/transition/whoosh-fast.mp3` (0.4) |
| Thẻ bật lên | `sfx/pixabay/pop.mp3` · gạch chéo: `sfx/mixkit/text/marker-pen-line.mp3` |
| Logo / cú "drop" | `sfx/pixabay/riser.mp3` (trước 1,2s) + `sfx/pixabay/impact-bass-1.mp3` |
| Xé giấy | `sfx/mixkit/paper/paper-slice-quick.mp3` + `paper-crumple-quick.mp3` |
| Dấu tích / xác nhận | `sfx/pixabay/click-soft.mp3` (0.4) — người duyệt chấm "100 điểm" |
| Ảnh màn hình bay vào | `sfx/mixkit/transition/swoosh-quick.mp3` + `sfx/mixkit/data/data-scan.mp3` (0.25) |
| Nút kêu gọi | `sfx/mixkit/ui/ui-confirm-tone.mp3` (0.35) hoặc `sfx/uisfx/soft/success.mp3` |

⚠ **Bài học "điếc tai":** `ui-success-soft.mp3` đỉnh −0,6 dB, dài 1,6s, đặt 4 lần cách 0,5s → chồng nhau, chói. Đã sửa:
(1) `mix_audio.py` **tự chuẩn hoá đỉnh mọi SFX về −6 dB** rồi mới nhân `volume`; (2) **người duyệt phải nghe trước** —
dùng file nghe thử:
```bash
python <kit>/tools/sfx_audition.py nghe-thu.mp3 sfx/pixabay/click-soft.mp3 sfx/uisfx/soft/check.mp3 sfx/uisfx/soft/snap.mp3 --repeat 4 --step 0.5
```
In ra thứ tự + giây → người duyệt chọn số. (Người làm video/AI không tự nghe được — luôn nhờ người nghe.)

## 3. Trộn — `mix_audio.py` + `cues.json`
```json
{ "duration": 54.16,
  "voice": {"file": "audio/narration.mp3", "volume": 1.0},
  "bgm":   {"file": "bgm/lyria-110.wav", "volume": 0.2, "start": 5.49, "fade_in": 1.5, "fade_out": 2.5, "duck": true},
  "sfx":   [{"t": 2.18, "file": "sfx/mixkit/paper/paper-slice-quick.mp3", "volume": 1.0}, ...] }
```
- `bgm.start`: nhạc vào muộn (v2: im lặng ở hook cho tiếng xé giấy "đanh", nhạc vào từ cảnh 2).
- `duck: true`: sidechain — nhạc tự hạ khi có giọng.
- `volume` SFX (sau chuẩn hoá): 0.3 nhẹ · 0.5 rõ · 0.8–1.0 mạnh (chỉ cho cú nhấn).
- Có limiter cuối (đỉnh ≤ −0,4 dB). Kết quả v2: trung bình −19,9 dB, đỉnh −3,1 dB.
Thường không viết cues.json tay — `build.py` sinh từ mốc giọng (docs/07).
