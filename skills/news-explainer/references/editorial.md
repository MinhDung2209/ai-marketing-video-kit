# Biên tập cho người xem phổ thông

## Chọn phong cách theo đề tài (agent tự quyết, ghi lý do trong đề xuất)

Không có một phong cách cố định cho kênh. Đọc đề tài rồi chọn; một ngày có thể ra nhiều phong cách khác nhau.

| Đề tài | Phong cách | Độ dài | Giọng (`profile` + nhạc) | Hình & nhịp dựng |
|---|---|---|---|---|
| Tiền, lãi suất, giá cả, chính sách kinh tế, thị trường | Kênh tài chính: theo dòng tiền, ai được/ai mất, nối chính sách ↔ túi tiền | Bản dài 10–15' + 3–4 short 60–90" | Chắc, rõ số, điềm tĩnh; nhạc news-explainer | Văn bản/tiêu đề báo tô dạ quang, số chạy, cột, mốc thời gian; đổi hình 4–6" |
| Xã hội, chính sách đời sống, khoa học, "vì sao" phổ thông | Kiến thức gần gũi, ví dụ đời thường trước, cơ chế sau | 5–8' + short | Ấm, tò mò, như kể bạn nghe | Ảnh/video thật + chữ viết tay, sơ đồ động đơn giản |
| Tin nóng đang diễn ra (biểu tình, thiên tai, sự cố) | Thời sự: chuyện gì – ở đâu – khi nào – điều chưa rõ; không suy đoán | 1–3' (dọc + ngang) | Nhanh, trung tính, nghiêm | Video hiện trường từ báo/đài là chính, mốc giờ, bản đồ; ít hiệu ứng |
| Tin hot đời thường, trend, chuyện lạ | Casual, nói chuyện như bạn bè, có chút hài | 45"–2' dọc | Tươi, nhanh, tự nhiên | Clip/ảnh thật, chữ sticker, zoom giật, nhạc vui |
| Clip hài lan truyền | Giải trí: clip gốc là chính, phụ đề sát, chêm meme tự dựng | 30"–90" dọc | Ít lời dẫn, tinh nghịch | Dừng hình, tua lại, zoom, tiếng hài; không miệt thị người thường |

Độ sâu nghiên cứu luôn cần ở mọi phong cách (sai dữ kiện thì casual cũng hỏng); thứ thay đổi là độ dài, giọng, nhịp và mức chi tiết đưa lên màn hình.

## Hook, giữ chân và vòng lặp (người dùng chốt 22/10/2026)

**Soi hook đối thủ trước khi viết.** Hook lấy từ video thật đang chạy, không đoán:
`social_radar.py tiktok "<chủ đề>"` (và `youtube "<chủ đề>" --days 30`) → `clips <scratch> <top 5 link>` → `clip_transcribe.py` → đọc 10 giây đầu + câu kết.
Ghi vào `RESEARCH.md` mục "Hook đang chạy": lượt xem, câu mở, kiểu hook, cách kết.
Ví dụ 22/10 (chủ đề lãi thả nổi):
- 1,3 triệu view mở bằng một kịch bản ngôi "bạn" có số cụ thể ("Bạn mua nhà 5 tỷ, vay 3 tỷ lãi 6%… tháng thứ 25 hoá đơn vọt lên 52 triệu… không một cuộc gọi báo trước").
- 985 nghìn view mở bằng ảnh chụp "bill" thật đang lan truyền.
- Video tên "Lãi suất thả nổi là gì?" chỉ được 1,5 nghìn view. **Định nghĩa khô không phải hook. Hệ quả, con số và nghịch lý mới là hook.**

**Công thức mở (3 giây đầu):** câu hỏi chủ đề + hệ quả gây sốc, viết thành một câu, kiểu "<Khái niệm> là gì mà <hệ quả có số cụ thể>?". Ngay sau đó là bằng chứng (người thật trong báo, tiêu đề, ảnh chụp). Rồi hứa trước "điều ít ai để ý" để giữ người xem tới giữa video.

**Giữ chân:** cứ 30–45 giây lại mở một vòng tò mò mới ("nhưng điều đáng nói là…", "câu hỏi tự nhiên là…"). Mỗi phần mở bằng câu hỏi người xem thật sự hỏi, lấy từ bình luận.

**Meme / nhấn hài:** dùng meme tự dựng, nhẹ tay với đề tài tiền bạc: zoom giật hoặc dừng hình ở con số sốc, chữ sticker ("ủa?", "khoan…"), SFX từ audio-library. Không dùng ảnh meme của người khác, không đùa trên nỗi khổ của người vay thật.

**Vòng lặp (loop):** câu cuối viết để **nối thẳng vào câu đầu**. Người xem xem hết, video tự phát lại, và cảm giác câu chuyện chưa dứt.
- Ví dụ: kết "…Và bạn có biết, vì sao chỉ bốn chữ trong hợp đồng lại khiến tiền trả mỗi tháng tự tăng?" (cắt luôn, không chào) → mở "Lãi suất thả nổi là gì mà…".
- Câu kết đọc giọng lửng, không hạ giọng chốt (ghi ở `direction`). Hình cuối khớp được với hình đầu.
- Lời mời comment (mục Câu kết trong SKILL) đặt **ngay trước** câu loop, không đặt sau.
- Câu đầu vẫn phải đứng được một mình cho người xem lần đầu.

## WHY

**Xâu chuỗi trước, viết sau (người dùng chốt 20/10/2026).** Tin tức hay nằm ở bối cảnh nối các tin lại với nhau, không ở một bài báo. Trước khi viết kịch bản, nghiên cứu song song 3 nhánh rồi ghi `RESEARCH.md` (timeline có ngày + số hiệu văn bản, chuỗi nhân quả, nguồn từng dữ kiện, điều chưa xác minh) và cho người dùng duyệt góc nhìn:
- Kênh chính thức: NHNN, Chính phủ, Quốc hội, bộ ngành — văn bản, số liệu, họp báo.
- Thị trường & chuyên gia: báo kinh tế, báo cáo công ty chứng khoán, số liệu theo mốc thời gian.
- Mạng xã hội & dư luận: voz, Reddit, Facebook chuyên gia, bình luận báo, TikTok/YouTube — người xem đang lo, đang hỏi gì.
Kịch bản phải giải được nghịch lý người xem thấy (vd "chính sách bảo giảm, sao lãi tiết kiệm vừa tăng?") bằng chuỗi nguyên nhân có số liệu, và chỉ ra điều không phải ai cũng thấy. Bản lãi suất 20/10 lần đầu chỉ thuật lại tin họp 19/10 → bị chê "chưa sâu".

Mở bằng hệ quả người xem cảm nhận được hoặc một nghịch lý có thật. Dẫn về 2–4 cơ chế chính, rồi giải thích các điều kiện làm chúng mạnh/yếu đi. Chốt bằng dấu hiệu cần theo dõi, không dự báo chắc chắn điều chưa biết.

Ví dụ tiền đề cần sửa: 'NHNN vừa tăng lãi suất' có thể thực ra là ngân hàng thương mại tăng lãi tiền gửi trong khi lãi điều hành giữ nguyên. Tách sự kiện đã xác minh trước khi tìm nguyên nhân.

Mỗi số liệu cần đơn vị, thời điểm, phạm vi và nguồn gốc. So sánh cùng cơ sở. Phân biệt phần trăm với điểm phần trăm, tồn lượng với tốc độ tăng, chỉ đạo với kết quả. Ví dụ giả định phải gắn nhãn cả lời nói lẫn hình.

Nói 'tiền để thanh toán' trước khi dùng 'thanh khoản'; nói 'giá một đồng tiền bằng đồng tiền khác' khi giải thích tỷ giá. Không lạm dụng ẩn dụ làm sai cơ chế, như ngân hàng chỉ cho vay lại một kho tiền gửi có sẵn.

Điều tra nguồn chính thức lẫn phân tích độc lập. Nêu điểm bất đồng đáng kể, không tạo cân bằng giả. Không đủ chứng cứ định lượng thì đừng gán phần trăm đóng góp cho từng nguyên nhân. Với vấn đề nhiều nguyên nhân, đừng dựng một thủ phạm duy nhất cho dễ kể.

## Clip tường thuật

Xem toàn bộ phần video truy cập được, ghi đoạn nào thiếu. Không bịa lời thoại hoặc nguyên nhân trước lúc máy quay bắt đầu. Chọn tình huống mở đầu ngắn, để clip tự chứng minh diễn biến, dịch phụ đề sát nghĩa và dùng lời dẫn để nối chỗ khó hiểu.

Phân biệt phản ứng quan sát được với suy đoán tâm lý. Tránh nhãn miệt thị, truy tìm danh tính người thường không cần thiết. Câu chuyện có thể chỉ cần hài và dễ hiểu, không phải mỗi lần đều có kết luận đạo đức.

## Mẫu đề xuất

Mỗi ứng viên gồm:
- Tên câu chuyện; dạng WHY / tường thuật.
- Thời điểm sự kiện và link nguồn gốc.
- Tín hiệu quan tâm: số liệu đo được theo thời gian hoặc ghi rõ định tính.
- Vì sao người xem Việt Nam sẽ quan tâm.
- Góc kể, câu mở đầu và điều người xem nhận được.
- Video/ảnh có thật: link, mức xác minh, quyền tái sử dụng.
- Khoảng trống nghiên cứu; có thể sản xuất hôm nay hay phải chờ.

Tin tổng hợp chỉ để phát hiện. Bản đề xuất không được lấy clip cũ hoặc caption của trang đăng lại làm toàn bộ bằng chứng.
