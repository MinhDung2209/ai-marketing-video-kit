# Soát bản dựng trước khi giao duyệt

Dùng cho bản marketing ngắn của KIT: soát preview trước `owner-review`, rồi kiểm lại **MP4 thật** sau render. Đây là checklist biên tập, không thay quyền duyệt của chủ dự án hay checklist KWF. Đọc [luật KIT](../SKILL.md), [kiểm tra đầu ra](../../../docs/08-kiem-tra-va-xuat-ban.md), [luật meme](../../../docs/11-meme-va-sticker.md) và luật riêng của job trước; tỷ lệ, thời lượng, vùng an toàn và mức âm theo job đã chốt.

## Checklist ngắn

- [ ] **Hook có bằng chứng:** những giây đầu cho thấy vấn đề/kết quả đã hứa, rồi vào công cụ; không mở bằng logo hay sticker trang trí. Số, đơn vị và lời khẳng định truy về ảnh/quay thật, đúng chiều thông điệp. Ví dụ: nói “Lọc ra nhóm khách phù hợp” thì hiện thao tác lọc và kết quả thật; không tự thêm “tăng gấp ba”.
- [ ] **Chữ đọc được:** giữ phụ đề sửa tay trong `voice.json` và bản Studio; kiểm dấu tiếng Việt, tên riêng, số, ngắt cụm, lúc vào/ra theo lời. Xem trên điện thoại đúng tỷ lệ và preset vùng an toàn của job: không che thao tác, số liệu, CTA hoặc nút nền tảng. Câu “Chọn thị trường, rồi xem kết quả” phải đủ thời gian đọc ở tốc độ thường; chia cụm nếu quá dày. Không áp cứng số ký tự/tốc độ đọc của nguồn tham khảo.
- [ ] **Âm lượng đo thật:** đo bản MP4 cuối, lưu lệnh, log, LUFS tích hợp và true peak; đối chiếu mức đã chốt. KWF product-demo hiện yêu cầu gần **-14 LUFS**, không biến nó thành ngưỡng chung cho mọi job. Giữ phép đo `volumedetect` theo docs/08; `mean_volume`/`max_volume` theo dBFS không phải LUFS/dBTP. Gain đặt trong code, trạng thái normalize hay một log cũ không chứng minh mức của bản xuất mới.
- [ ] **Đầu, điểm cắt, đuôi:** kiểm khung đầu, hai phía mỗi điểm cắt, lúc phụ đề/đồ họa xuất hiện và khung cuối hợp lệ từ MP4. Đối chiếu duration/fps với timeline; không ló nền trống, lặp cảnh, mất chữ, giật zoom hay cắt ngang từ/động tác ngoài ý đồ. Kiểm cả seek xuôi/ngược ở preview. Hold có chủ đích được giữ; đoạn đen/im lặng hoặc đuôi đứng hình ngoài ý đồ phải sửa. Nghe câu cuối và đuôi nhạc/SFX để phát hiện cụt tiếng, click, fade lỗi.
- [ ] **Meme thưa, đúng nhịp:** theo luật KIT hiện có, tối đa **1 meme / 10–15 giây**, tính cả tiếng lẫn hình; không ở cảnh 1, không che bằng chứng/phụ đề. Liệt kê mốc thực tế, kể cả meme/nét khoanh đã ghi trong video; ưu tiên focus, tránh khoanh liên tục. Người xem xác nhận meme giúp câu nói và SFX không lấn từ khóa.
- [ ] **Gói giao và ghi nguồn sẵn:** MP4, tiêu đề, mô tả, CTA, thumbnail, phụ đề và bằng chứng QA đúng bản. Chuẩn bị attribution từ metadata tài sản đã dùng (ID, nguồn, giấy phép); dùng Noto thì kèm “Animated emoji: Google Noto Emoji (CC BY 4.0)” trong mô tả. Giữ `BRIEF.md`, `voice.json`, sổ chi `credits.md` theo KIT; sổ chi credit không thay dòng ghi nguồn. Gói local không đồng nghĩa đã được phép đăng/tải lên.

## Bằng chứng máy và quyết định của người

Máy ghi được probe, phép đo âm, lint, khung trích và lỗi có timestamp. Phải mở ảnh để kiểm bằng mắt; lint sạch hay contact sheet không chứng minh cả clip đúng, càng không chứng minh đã nghe. Đối với bản Studio, `index.html` là bản chính: dùng snapshot của bản đó, không chạy lại build/import đè sửa tay.

Ví dụ PowerShell chỉ đọc bản xuất (đổi đường dẫn tới file thật):

```powershell
$video = 'D:/duong-dan-clip/renders/final.mp4'
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate,sample_rate -of json $video
ffmpeg -hide_banner -nostats -i $video -map 0:a:0 -vn -af 'ebur128=peak=true' -f null -
ffmpeg -hide_banner -nostats -i $video -map 0:a:0 -vn -af volumedetect -f null -
```

Lấy `I` và `Peak` ở **Summary cuối** của ebur128, không lấy mốc đang chạy. Nếu thiếu audio, thiếu công cụ hoặc lệnh lỗi: ghi rõ `unavailable`/`failed`, lý do và phần chưa đo, không đánh dấu đạt hay điền số ước lượng. Các engine bổ sung như WhisperX, VieNeu, Cap, Streamlink là tùy chọn; thiếu thì báo `unavailable`, không tự cài, gọi provider hay đổi engine. Checklist này không cần cài các engine đó.

Người duyệt **xem và nghe trọn bản ở 1×**, kiểm thêm trên điện thoại; xác nhận giọng đúng chữ/cách đọc, không lẫn chỉ dẫn, nhạc không lấn, SFX không chói, cut/fade tự nhiên. Agent không tự ghi “đã nghe duyệt”. Ghi riêng người duyệt, thời điểm, bản/hash đã xem/nghe, quyết định và mốc cần sửa; chưa có phản hồi thì để **chờ duyệt**. Sửa hình, lời, timing hoặc audio thì kiểm lại phần ảnh hưởng và xin duyệt lại theo workflow hiện có.

KWF đang dùng `workflow-evidence/studio-qa.json` → `owner-review` → `render-review.json` → `publish-package.json`: chủ bước ghi bằng chứng vào đúng artifact, giữ hash bản chính/MP4 và log; công cụ thô không tự tạo đủ các receipt này. Xem [hợp đồng artifact](../../../docs/contracts/production-artifacts-v1.md). Chủ dự án duyệt preview trước render trong KWF; kiểm MP4 sau render vẫn bắt buộc. Không tự phê duyệt workflow hoặc đăng bài.

Với job **StradeVn** hiện tại: dùng “dữ liệu xuất nhập khẩu toàn cầu”, không dùng “tờ khai hải quan”; không lộ tên nhà cung cấp dữ liệu hay agent. Cách đọc “Strade vi-en”; short dưới hai phút, hook xong vào công cụ. Giữ số đúng lúc quay và logo file thật, che dữ liệu cá nhân. Đây là luật job, không áp tên/cụm cấm này cho job khác.

Tham khảo ý tưởng soát đo/mắt/tai từ [agent-video-editor, review-checklist.md](https://github.com/kmilo93sd/agent-video-editor/blob/8e32c0aff64c445ef1e2b87bc04408a34d68c973/skills/editing-videos/review-checklist.md) và [recipe quay màn hình](https://github.com/kmilo93sd/agent-video-editor/blob/8e32c0aff64c445ef1e2b87bc04408a34d68c973/skills/editing-videos/recipes/narrated-screen-tutorial.md). Bản tiếng Việt này viết riêng cho KIT; các ngưỡng chung về caption, shot, vùng chữ, loudness/peak của upstream không trở thành luật bắt buộc mới.
