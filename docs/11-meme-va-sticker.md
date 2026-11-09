# 11 · Meme & sticker động

Thư viện: `meme-library/` (giống `audio-library/`: file + `catalog.json` ghi nguồn, giấy phép từng file).

## 1. Luật dùng (người duyệt chốt 04/11/2026)
- **Không lạm dụng, chỉ chỗ PHÙ HỢP** (người phụ trách 06/11/2026: "phù hợp, spam ko hay"). Tối đa **1 meme / 10–15 giây** (tính cả meme tiếng lẫn meme hình), chỉ đặt ở nhịp cảm xúc (hỏi xoáy, wow, chốt, kêu gọi). Meme dạng tiếng hay video đều được — chọn dạng hợp cảnh.
  **Không** đặt sticker ở cảnh mở đầu chỉ để "cho vui" — hook phải mạnh bằng chữ + số thật.
- Sticker **không che** số liệu / chỗ đang thao tác / phụ đề / vùng nút TikTok (phải 170 px, dưới 1570 px).
- **Meme thật từ web** (người phụ trách quyết định 06/11/2026: "cần meme thật, không cần icon"): lấy từ các kho lớn trong
  `meme-library/sources_web.json` (greenscreenmemes, memescreens, memes-download, tiengdong — tiếng Việt, myinstants — âm thanh,
  imgflip — ảnh). **Chỉ lưu LINK** vào `meme-library/web.json`, không tải sẵn; lúc dựng, `engine.finish()` gọi
  `tools/meme_web.py` → ffmpeg đọc link, cắt đoạn (`ss`/`t`), tách nền xanh + tự cắt khung → `<clip>/assets/meme/<id>.webm`,
  tiếng meme → SFX (thay tiếng pop, cắt theo thời lượng sticker).
  Bản quyền: người phụ trách đã tự lo (06/11/2026) — không cần nhắc lại. Dùng **đa dạng**: meme Việt (tiengdong: "10 điểm",
  "ối dồi ôi", "bất ngờ chưa bà già"…) lẫn quốc tế (vine boom, bruh, emotional damage, GTA…), cả **tiếng** lẫn **mp4**.
  Meme chỉ có tiếng: `st.add_meme_sound("vn-10-diem", t)` (không hiện hình); meme có hình: `st.add_sticker(id, t, dur=…)`.
- Emoji Noto (`sources.json`) vẫn dùng được cho chỗ cần nhỏ, gọn.
- Tem/stamp kiểu "+25%" dán đè lên ảnh chụp bài báo: **không dùng** (người duyệt chê "bố láo", 04/11/2026). Muốn nhấn số
  thì khoanh + tô **đúng con số trên trang thật** lúc quay (`recorder/rec.py → Session.mark_text`) rồi phóng sát vào đó.
- **Khoanh/tô số cũng không spam** (người duyệt 04/11/2026: "cái mark tôi thấy bạn spam"): mỗi cảnh chỉ 1–2 lần khoanh
  có mực, đúng con số giọng đọc đang nhấn (~1 lần / 10–15 s). Chỗ khác chỉ phóng camera tới (`Session.focus`, không vẽ).
- Dùng nguồn CC BY (Noto) → thêm dòng ghi nguồn vào mô tả bài đăng: *"Animated emoji: Google Noto Emoji (CC BY 4.0)"*.

## 2. Nguồn đang có
| Nguồn | Giấy phép | Dùng cho | Ghi chú |
| --- | --- | --- | --- |
| Google Noto Animated Emoji | CC BY 4.0 (thương mại OK, ghi nguồn) | 40 emoji động: suy nghĩ, wow, tiền, hot, tăng, chốt, ăn mừng, cà phê… | Một số mã không có bản động (404) → ghi ở `_khong_co_ban_dong` |

Muốn thêm nguồn (vd Pixabay video, LottieFiles free): thêm khối vào `sources.json` kèm `license` + `license_url`, viết hàm tải
tương ứng trong `meme_fetch.py`. Chỉ thêm nguồn **ghi rõ cho phép dùng thương mại**.

## 3. Lệnh
```bash
python tools/meme_web.py chờ                                   # tìm trong danh mục link (web.json)
python tools/meme_web.py --search "waiting" [--site memescreens] # tìm TRỰC TIẾP trên các kho → link tải thẳng
python tools/meme_web.py --search "bất ngờ" --site tiengdong --add 1,3 --tags "bất ngờ, wow"   # ghi link vào web.json
python tools/meme_web.py --preview mr-bean-waiting              # 1 khung đã tách nền để kiểm bằng mắt
# story.py: P("V7", 0, 1, meme="cat-shocked")  hoặc  st.add_sticker("gta-mission-passed", t, dur=3, w=420)
```
```bash
python tools/meme_fetch.py                          # tải / cập nhật thư viện (bỏ qua file đã có)
python tools/meme_search.py tiền                    # tìm theo từ khoá (có dấu / không dấu)
python tools/meme_search.py --copy noto/fire noto/check <dự án>   # chép vào <dự án>/assets/meme/
```

## 4. Đặt vào cảnh (index.html)
```html
<div class="clip" data-start="12.7" data-duration="2.2">
  <video class="meme" src="assets/meme/thinking.webm" muted playsinline preload="auto" data-loop="1"
         style="position:absolute;left:760px;top:520px;width:220px"></video>
</div>
```
- File là **WebM VP9 có kênh alpha** (nền trong suốt). Không dùng GIF/WebP động trong `<img>`: chúng chạy theo đồng hồ thật nên
  mỗi lần render khác nhau, không khớp nhịp. `render.py` tua `<video>` từng khung; `data-loop="1"` = phát lặp.
- Hoạt ảnh vào/ra bằng GSAP trên phần tử bao (`scale` 0→1 `back.out`, lắc nhẹ `rotation`), kèm 1 SFX `pop` nhỏ.
