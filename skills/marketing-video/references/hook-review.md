# Rà hook: lời hứa, bằng chứng, phần nhận được

Dùng khi chọn hook trong `BRIEF.md`; kiểm lại trên bản dựng.
Đọc cùng [thư viện hook](../../../library/hooks/THU-VIEN-HOOK.md) và luật trong
[SKILL.md](../SKILL.md). Ví dụ tiếng Việt được viết mới, không nhập hay chép corpus hook.
Ví dụ minh họa không chứng minh tính năng thật.

## Kiểm 0–3 giây đầu

| Điểm kiểm | Câu hỏi để duyệt | Cách sửa khi chưa rõ |
| --- | --- | --- |
| **Promise — lời hứa** | Đúng người xem có hiểu mình sẽ giải quyết việc gì? | Giữ một việc cụ thể, bỏ lời chào và tính từ chung chung. |
| **Proof — bằng chứng** | Khung mở có cho thấy thao tác, vật hoặc dữ liệu liên quan trực tiếp đến lời hứa? | Đưa chi tiết thật lên sớm; nếu chưa có, đánh dấu thiếu bằng chứng, không bịa. |
| **Payoff — phần nhận được** | Người xem biết ở lại để nhận cách làm hay kết quả nào? Phần sau trả ở đâu? | Ghi rõ cảnh/mốc trả lời; bỏ vòng tò mò nếu video không trả được. |

Trong 0–3 giây, làm rõ lời hứa và dấu hiệu bằng chứng; payoff có thể ở cảnh sau.
Mốc này không cam kết giữ chân. Xem **tắt tiếng**: hình/chữ đủ ngữ cảnh chưa?
Nhờ người nghe kiểm lời tự nhiên, đọc kịp, khớp hình. Chữ nhấn bổ sung thông tin;
phụ đề giữ đúng lời, đủ dấu tiếng Việt.

## Ví dụ tự viết: nối lời mở với phần trả

Chỉ dùng khi đã xác nhận tính năng thật. Thay mốc dự kiến bằng thời gian thực khi rà bản dựng.

| Tình huống | Lời + hình trong 0–3 giây | Proof cần có | Payoff phải trả |
| --- | --- | --- | --- |
| Chủ shop tìm đơn chưa đóng gói | Lời: “Đơn nào còn chờ gói?” Chữ: “Lọc trạng thái”. Hình: con trỏ mở bộ lọc trên dữ liệu mẫu có nhãn. | Quay thật thao tác chọn trạng thái và danh sách tương ứng; làm mờ thông tin khách. | Cảnh kế, dự kiến 3–8s: chỉ đúng điều kiện lọc và cách trở lại danh sách đầy đủ. |
| Người dựng sửa phụ đề | Lời: “Tên riêng bị sai dấu?” Chữ: “Sửa ngay trên dòng chữ”. Hình: chọn từ sai trong bản nháp mẫu. | Quay thật thao tác sửa chữ và xem lại phụ đề; không dùng ảnh AI làm bằng chứng tính năng. | Cảnh kế, dự kiến 3–8s: lưu sửa, phát lại đoạn đó để thấy đúng tên và đúng thời điểm. |

## Anti-patterns: nhận ra và sửa

| Lỗi | Ví dụ cần loại/sửa | Hướng sửa |
| --- | --- | --- |
| Mở bằng giới thiệu dài | “Chào mọi người, hôm nay mình xin giới thiệu giải pháp rất hay…” | Mở ngay cảnh đơn chờ gói cùng câu hỏi cụ thể ở trên. |
| Hứa kết quả chưa có chứng cứ | “Bật nút này là đơn về gấp đôi.” | Thu hẹp về điều quay được: “Lọc các đơn đang chờ gói.” Không suy diễn thao tác thành doanh thu. |
| Tò mò không trả lời | “Có một bí mật mà cuối video bạn mới biết…” rồi chỉ hiện logo. | Nêu việc sẽ học và chỉ rõ cảnh trả lời; bỏ hook nếu không có phần trả. |
| Hình chứng minh chuyện khác | Nói sửa phụ đề nhưng chỉ chạy cảnh văn phòng đẹp. | Quay đúng từ sai → thao tác sửa → kết quả; cảnh trang trí không thay bằng chứng. |
| Kích thích bằng chê người xem | “Chỉ người thiếu chuyên nghiệp mới gửi báo giá kiểu này.” | Nói về bước kiểm: “Trước khi gửi, xem lại mục phí giao.” |
| Lời chứng thực giả hoặc số tự đặt | Người dẫn AI nói “Tôi dùng rồi, tiết kiệm đúng hai giờ mỗi ngày.” | Cho người dẫn giới thiệu thao tác; chỉ nêu thời gian khi có phép đo, điều kiện và nguồn thật. |
| Chữ/hình quá tải, sai hướng | Chữ kín màn hình, sticker che bộ lọc; lời nói tăng trưởng nhưng bài báo nói suy giảm. | Giữ một điểm nhấn đọc được; bỏ vật che proof, chọn nguồn cùng chiều và đúng ngữ cảnh. |

## Ghi kết quả vào lần rà hiện tại

Ghi từng phương án trong `BRIEF.md`; không tự sửa bản đã duyệt:

```text
Hook / tệp người xem / lời + chữ + hình 0–3s:
Lời hứa:
Proof: đường dẫn clip/nguồn + mốc thật; hoặc “thiếu bằng chứng”:
Payoff: cảnh + mốc trả lời thật; hoặc “chưa dựng, mốc dự kiến …”:
Tắt tiếng: … / người nghe-xem xác nhận: … / lỗi cần sửa: …
Kết luận: đạt để trình duyệt | cần sửa | thiếu bằng chứng
```

Chọn “đạt để trình duyệt” khi lời hứa rõ, proof đúng, payoff có chỗ trả; bản dựng phải xem phần trả.
Giữ cổng duyệt của kit: rà hook chưa thay duyệt kịch bản/âm thanh; để người dùng nghe/xem duyệt.
