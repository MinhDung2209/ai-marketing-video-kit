---
name: news-explainer
description: Theo dõi tin tức và video đang lan truyền, đề xuất đề tài hằng ngày cho người xem Việt Nam, rồi sản xuất video giải thích WHY hoặc tường thuật clip thật bằng video kit.
---

# News explainer

Người dùng muốn hai dạng nội dung. Đọc `references/editorial.md` khi chọn đề tài hoặc viết kịch bản. Cấu hình lịch và nền tảng ở `../../newsroom/config.json`.

## Ba dạng (người dùng chốt 20/10/2026)

- **Tin nóng (`hot_news`):** sự kiện đang diễn ra (vd biểu tình). Ảnh/video thời sự thật từ báo/đài là chính; tóm tắt nhanh: chuyện gì, ở đâu, khi nào, vì sao đáng chú ý, điều chưa xác minh.
- **Giải thích / kiến thức (`why_explainer`):** mục WHY bên dưới.
- **Trend / giải trí (`viral_clip_amuse`):** clip hài đang lan truyền (vd thanh niên can bà cụ cãi nhau trên tàu, bị chửi lại thì chỉ nhại theo). Clip gốc là nội dung chính, lời dẫn ngắn, phụ đề sát lời thoại; chêm meme TỰ DỰNG (zoom giật, dừng hình, tua lại khoảnh khắc đắt, chữ sticker, vẽ tay, tiếng hài từ audio-library) thay vì ảnh meme của người khác. Mục "Tường thuật clip" bên dưới áp dụng.

- **WHY:** Nghiên cứu nguyên nhân gốc rễ, hoàn cảnh, cơ chế, kết quả và hệ quả. Kiểm tra tiền đề trước: đừng giải thích một sự kiện chưa xảy ra. Dẫn từ trải nghiệm đời thường vào cơ chế; tách dữ kiện, diễn giải và giả định. Đối tượng là người xem phổ thông.
- **Tường thuật clip:** Tìm video gốc, dịch đúng lời thoại, xác minh diễn biến và kể thật dễ hiểu. Clip thật là nội dung chính. Giữ những đoạn đối đáp tạo sức hút, không thuyết minh đè lên điểm hài. Không bắt mọi clip phải mang bài học xã hội.

## Bắt sóng và đề xuất

Theo dõi báo chí và các nguồn công khai truy cập được của Facebook, TikTok, YouTube, X, Reddit. Công cụ tìm kiếm chỉ là phương tiện phát hiện; việc không tìm thấy bài không chứng minh nó không tồn tại. Ghi rõ nền tảng nào chưa truy cập được hoặc thiếu dữ liệu.

Phân biệt ngày xảy ra, ngày đăng, ngày cập nhật và thời điểm quan sát. Clip cũ được chia sẻ lại không phải sự kiện vừa xảy ra. Truy vết bản gốc, kiểm tra clip có bị cắt ngữ cảnh, dàn dựng hoặc tạo bằng AI hay không trước khi kể như sự thật.

Chọn đề tài dựa trên sức hút sẵn có, mức liên quan tới người xem Việt Nam, câu hỏi gây tò mò, khả năng tìm bằng chứng/tư liệu và giá trị người xem nhận được. Đừng chọn chỉ vì đề tài thuận tiện cho sản xuất hoặc thiên về công nghệ. Biểu tình, sự kiện xã hội và khoảnh khắc đời thường có thể là ứng viên tốt nếu có bằng chứng.

**Quét trend (kênh "Ít xem TikTok nhưng muốn cập nhật trend", 3 lần/ngày 07:30 · 12:00 · 19:30):**
`python <kit>/tools/social_radar.py scan` → Google Trends VN + YouTube thịnh hành + TikTok Creative Center top 100 hashtag VN
(độ phổ biến 7 ngày: `rise` +100 = đang lên mạnh) + Weibo 热搜 và bài/video hot → `newsroom/signals/<ngày>/`. Rồi với hashtag ứng viên:
`social_radar.py tiktok "#<hashtag>"` (đã đăng nhập; ra clip + lượt xem) để hiểu trend là gì, `clips <dự án>/media/tiktok <link…>` tải clip gốc.
Cần đăng nhập 1 lần (`social_radar.py login`, tài khoản PHỤ): TikTok, **Creative Center (TikTok for Business — đăng nhập riêng)**, Weibo, Facebook.
Loại khỏi đề xuất: quảng cáo/chiến dịch thương hiệu (vd #danhthucbanlinh = Tiger Beer), trend xoay quanh ngoại hình trẻ vị thành niên.
Weibo: clip tình huống hài/lạ → dịch phụ đề, giữ tiếng gốc, không nêu tên người thường.

Lưu hai quan sát tương tác trở lên trước khi gọi một clip là tăng tốc. Không có dữ liệu tương tác thì ghi 'tín hiệu định tính', không bịa lượt xem, tốc độ lan truyền hay thứ hạng trend. Nhiều trang đăng lại cùng một nguồn không phải nhiều xác nhận độc lập.

Đầu ra mỗi ngày: 5 đề tài (nếu đủ tốt), đề xuất ưu tiên 1–2, từng đề tài có link gốc, thời điểm, góc kể, dạng video, mở đầu dự kiến, nguồn hình, trạng thái kiểm chứng và lý do đáng xem. Chỉ sản xuất khi người dùng đã yêu cầu sản xuất; đề xuất hằng ngày không tự mở rộng thành đăng YouTube.

## Sản xuất bằng kit

Kit root là thư mục hai cấp trên skill. Hướng dẫn giọng: `../../docs/04-giong-doc.md`. Dùng **Gemini 3.1 Flash TTS Preview** theo lựa chọn của người dùng; số đọc bằng chữ, chỉ đạo giọng tự nhiên và nhịp gọn. Nếu model không còn hoạt động, báo rõ; không âm thầm đổi model.

Mỗi đề tài một thư mục mới `projects/<dạng>-<chủ-đề>-<YYYY-MM-DD>/`; không ghi đè dự án cũ. Bản 19/10 (`why-lai-suat`: thẻ chữ tĩnh, ảnh Wikimedia chung chung — cảng Hamburg cho tin VN) bị người dùng chê "không đúng thực tế" → không làm theo kiểu đó.

### Quy trình dựng (mẫu đầy đủ: `examples/why-giam-lai-suat.voice.json` + `examples/why-giam-lai-suat.plan.json`, video 20/10/2026)

1. `voice.json` (giống mẫu: profile, `lines` V01… có `text` đọc số bằng chữ + `caption` hiện số; thẻ biểu cảm TIẾNG ANH ngắn `[curious]` `[serious]` — thẻ tiếng Việt bị đọc thành lời) → `python <kit>/tools/tts_script.py voice.json audio` → **`python <kit>/tools/tts_qa.py voice.json audio`** (nghe lại bằng máy: thẻ bị đọc, nhịp lố, sai chữ) → câu ⚠ sửa rồi `--only`. Trend: câu `{"id": "C01", "pause": 5.8, "caption": "…"}` = khoảng lặng cho TIẾNG GỐC clip (cảnh video `"sound": 1.0` neo `at: C01`).
2. Hình thật — thứ tự ưu tiên:
   - **Ảnh/video trong bài báo đưa tin chính sự kiện** (người dùng chọn, 20/10/2026): `python <kit>/tools/news_media.py search "<từ khoá>" --days 3` → `grab <link> media --shot --video`. `media.json` giữ báo, link, giờ đăng, chú thích, tác giả ảnh → ghi nguồn trên hình (`credit: "Ảnh: SBV · Dân trí"`) và trong mô tả. Không xoá logo/watermark.
   - `--shot` = ảnh chụp tiêu đề bài → cảnh `headline` có bút dạ quang tô câu chính.
   - Bối cảnh chung (tiền, quầy giao dịch, phố, xưởng): Storyblocks/Envato qua `tools/stock_dl.py` (nhánh `feat/free-audio-ambience`, chưa merge vào main), rồi Pexels. Chuyển clip về H.264 1080p30 trước khi đưa vào HTML.
   - Xem contact sheet (`news_media.py sheet media`), loại ảnh sai sự kiện/sai nơi/quá cũ. Không ảnh AI giả hiện trường.
3. Đồ họa: **chỉ motion HTML** (người dùng chê thẻ tĩnh) — `templates/news-motion` (số chạy, cột tụt, mốc thời gian, chữ viết tay có đầu bút, khoanh/gạch chân, trích dẫn hiện theo từ). Số liệu trên đồ họa phải có trong nguồn; không dựng "ví dụ" bằng số tự đặt.
4. `plan.json`: mỗi cảnh neo vào câu (`at`) + cụm chữ (`phrase`) để hình đổi ĐÚNG lúc giọng nói tới — xem docstring `tools/news_video.py`. Đổi hình 3–6 giây/lần; ảnh/video thật là nền, motion đè lên hoặc xen giữa.
5. `python <kit>/tools/news_video.py all <dự án>` → phụ đề khớp giọng (khoảng lặng thật, không ước lượng), index.html, `review/scenes.jpg`, `video.mp4` (nhạc `bgm.lyria.news-explainer-100bpm` tự duck dưới giọng + SFX tự khớp hiệu ứng), `QA.json`. Xem `review/scenes.jpg` trước khi render dài (~3 s render / 1 s video).

Ảnh AI chỉ dành cho minh họa phù hợp, không giả làm bằng chứng hay hiện trường. Chỉ gọi công cụ tạo ảnh khi cần, không mặc định mọi video phải dùng AI image.

Lời đọc quyết định thời gian dựng. Kiểm tra số liệu và phép tính, xem ảnh contact sheet và khung từ MP4. Kiểm tra độ dài, khung đen, âm lượng, phụ đề và mô tả nguồn. Người dùng xem/nghe đánh giá bản mẫu trước khi tự đăng hoặc yêu cầu đăng.

## Lịch chạy

Cấu hình yêu cầu: 07:30 mỗi ngày, Asia/Ho_Chi_Minh. File cấu hình không tự tạo một lịch thực thi. Chỉ báo đã kích hoạt khi scheduler/runner thực sự được cài và đã kiểm tra. Cần ghi nhận môi trường chạy, quyền truy cập nguồn, nơi lưu đề xuất và lỗi từng nguồn. Không báo 'đang theo dõi realtime' chỉ vì đã viết hướng dẫn.
