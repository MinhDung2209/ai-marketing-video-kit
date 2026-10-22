# Lệnh chạy đề xuất hằng ngày

Dùng skill `skills/news-explainer/SKILL.md` và `newsroom/config.json`. Đọc cấu hình và xác định thời điểm chạy thực tế theo Asia/Ho_Chi_Minh. Tìm tin 24–48 giờ qua; mở rộng 7 ngày nếu cần ngữ cảnh. Ưu tiên nguồn chính thức và sự kiện đang được thảo luận trên Facebook, TikTok, YouTube, X, Reddit mà công cụ thực sự truy cập được.

Tạo thư mục `newsroom/reports/YYYY-MM-DD/`. Lưu `proposals.md` và `evidence.json`, gồm: thời điểm quan sát, link, nền tảng, ngày xảy ra/đăng, nguồn gốc, tương tác nếu quan sát được, tình trạng xác minh và quyền sử dụng tư liệu. Ghi nguồn nào không truy cập được. Không suy đoán lượt xem hoặc tự gọi nội dung là viral chỉ vì tìm kiếm ra.

Đưa ra tối đa 5 đề tài đủ mạnh; chọn ưu tiên 1–2, không cố điền đủ số lượng. Mỗi đề tài có dạng WHY hoặc tường thuật clip, câu hỏi trung tâm, nguyên nhân đáng nghiên cứu hoặc điểm hài hấp dẫn, hook 10 giây, thời lượng dự kiến, ảnh/clip thật có thể dùng, dữ kiện còn thiếu. Tách tin mới với clip cũ được chia sẻ lại. Không bắt mọi clip hài có bài học xã hội.

Đề xuất phải dễ đọc với người làm nội dung phổ thông. Lưu báo cáo để người dùng duyệt. Không tự gọi API tạo video hoặc đăng YouTube chỉ từ lịch đề xuất. Khi người dùng chọn đề tài và yêu cầu sản xuất, dựng trong một thư mục dự án mới theo video mẫu.

Lịch mong muốn: 07:30 mỗi ngày giờ Việt Nam. Chỉ đánh dấu schedule_active=true sau khi có runner/scheduler thật và đã kiểm tra một lượt chạy, đồng thời xác định nơi người dùng nhận báo cáo.
