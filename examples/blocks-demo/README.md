# Khối cảnh: preview cục bộ

`index.html` là preview độc lập 1080×1920, dùng GSAP và phông Be Vietnam Pro đã có trong kit, chép vào `assets/` khi build. Không cần mạng, TTS, video quay hay FFmpeg. Mở file trực tiếp; dùng `?t=9.8` hoặc phím ←/→ để tua 0,1 giây. Trang không tự phát theo đồng hồ.

Từ thư mục kit:

```powershell
.venv/Scripts/python.exe -X utf8 examples/blocks-demo/build.py --snap
.venv/Scripts/python.exe -X utf8 examples/blocks-demo/check.py
# Khi đã có HyperFrames CLI:
npx hyperframes lint examples/blocks-demo
```

`build.py` dùng `Story.card/place/chunk_onset` thật; chỉ thay dữ liệu đọc giọng bằng ba mốc giả lập cho mỗi câu. Không gọi `Story.finish` (vốn ghép audio/tải SFX). Màu lấy trực tiếp từ `profiles/stradevn/profile.json → brand`. Số **3** chỉ số thẻ thật trong demo, không phải số liệu khách hàng. Preview không có giọng, phụ đề, logo hoặc nhạc.

`--snap` gọi nguyên `tools/render.py --snap`, tạo bốn PNG ở đây và chép bản giao vào `orchestration/reports/K02/`:

| Giây | Khung |
| --- | --- |
| 2,0 | Đường nối đầu đang vẽ, thẻ kế tiếp chưa xuất hiện |
| 4,5 | Đủ ba thẻ và hai đường nối |
| 9,8 | Chữ re-hook đang mở mask, lớp viền lệch |
| 10,4 | Giữ số và chữ sau khi chuyển động kết thúc |

`check.py` kiểm hợp đồng tham số, cue tùy chọn, ID khi lặp block, palette, escaping/NFC, thời điểm hiện thẻ, vùng an toàn và hai cỡ chữ. Browser check so PNG byte-for-byte giữa seek tiến/lùi và mở trang mới tại thời điểm rời rạc. Chrome dùng `VIDEOKIT_CHROME`, nếu chưa đặt thì dùng vị trí D:/Apps khi tồn tại, sau đó theo bộ dò của kit.

Hai cảnh giữ cấu trúc `section.clip` của `Story.card`. HyperFrames 0.9.23 lint báo hai cảnh báo `nested_structure_needs_subcomposition` về cách tổ chức timeline Studio, không có lỗi. Không cần sửa engine/converter để dùng block trong `story.py`.

Ý tưởng chuyển động tham khảo các mục [Explainers](https://github.com/yihui-dev/awesome-opus5-5-videos#explainers) và [motion graphics](https://github.com/yihui-dev/awesome-opus5-5-videos#motion-graphics) của danh mục MIT; GSAP/SVG/CSS của hai block tự viết theo giấy phép Apache-2.0 của kit. Không chép video, hình, lời, nhạc hay code từ các tác giả được dẫn trong danh mục. Tài sản GSAP/phông trong preview được chép từ kit; xem `THIRD-PARTY.md` của kit cho giấy phép riêng.
