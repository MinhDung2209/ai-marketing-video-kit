# 09 · Lỗi thường gặp (đều đã gặp thật)

| Hiện tượng | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `UnicodeEncodeError: 'charmap'` khi chạy công cụ | Cửa sổ lệnh Windows không in được tiếng Việt | Đã sửa trong mọi công cụ; tự viết script thì đặt `PYTHONIOENCODING=utf-8` |
| TTS `400 … violates Vertex AI's usage guidelines` | Bộ lọc Google chặn nhầm, ngẫu nhiên | `tts_script.py` tự thử lại + dự phòng; vẫn lỗi → đổi vài chữ, `--only` |
| Model ảnh "không khả dụng trong gói" | Sai mã model / gói tài khoản | Mã đúng: `gpt-image-2.5-flare`; kiểm gói plenxai |
| MCP "The operation timed out" | Tạo lâu hơn ~4 phút | Vẫn đang tạo → lấy link trên web plenxai; gọi tuần tự; không gọi lại ngay |
| omni-flash báo lỗi duration | Chỉ nhận 4/6/8/10 | Chọn 6 |
| Clip: đồ vật lơ lửng / dịch chuyển | Prompt nhiều động tác | 1 động tác / clip; cắt đoạn đẹp bằng `data-offset`/`data-end` |
| Logo AI vẽ sai màu/hình | AI tự vẽ lại | Chèn file logo thật khi dựng |
| AI tự thêm số liệu vào ảnh | Prompt không cấm | Thêm "no statistics, no percentages" + negative |
| Khung render trắng/đen trơn | Khung gốc không có kích thước | `render.py` tự gán px theo data-width/height |
| Cảnh đầu bị phủ trắng | `fromTo` áp "from" sớm | `immediateRender:false` |
| Phụ đề kéo dài xuống đáy | `.clip` inset:0 + định vị riêng | `inset:auto` |
| Video không bị bo góc | border-radius + transform | `clip-path: inset(0 round …)` |
| Thẻ/chữ không khớp lời | Ước lượng theo ký tự | `speech_segments.py` đo khoảng lặng |
| SFX chói tai | File gốc quá to, chồng nhau | Chuẩn hoá đỉnh (tự động) + `sfx_audition.py` cho người duyệt nghe |
| Giọng "lỏ", đều đều | Dùng Chirp3-HD | Gemini-TTS + profile/direction |
| Sửa tốc độ ngược ý người duyệt | Hiểu nhầm "chậm/nhanh" | Hỏi lại / nghe lại trước khi đọc lại cả bài |
| `npx hyperframes` bị chặn | Quyền auto mode Claude Code | `/permissions` thêm `Bash(npx hyperframes:*)` hoặc dùng `render.py` |
| Không lấy lại được ảnh đã tạo | `list_my_jobs` của MCP lỗi | Người duyệt copy link từ web; đổi đuôi `format=png,quality=100` |
