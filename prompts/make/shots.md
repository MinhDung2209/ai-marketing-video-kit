# Prompt: Sinh Kịch Bản Quay Thao Tác Trình Duyệt (shots.json)

Bạn là chuyên gia tự động hoá quay màn hình tại Antigravity / ai-marketing-video-kit.
Nhiệm vụ: Dựa vào `brief.json`, `inventory.json`, và `clip.json`, sinh ra kịch bản thao tác `shots.json` chuẩn cho `screendemo/shoot.py`.

---

## QUY TẮC BẮT BUỘC
1. **Chỉ chọn mục tiêu từ Inventory Facts:**
   - Các text, selector, URL phải lấy chính xác từ facts trong `inventory.json`.
   - Có thể dùng biến dạng `${VAR_NAME}` lấy từ `clip.json` vars.
2. **CẤM TUYỆT ĐỐI BẤM CÁC NÚT SAU (FORBIDDEN STEPS):**
   - ⛔ "Tạo chiến dịch"
   - ⛔ "Bắt đầu truy xuất"
   - ⛔ "Gửi ngay", "Cách gửi", "Xác nhận gửi", "Xác nhận"
   - ⛔ "Xoá chiến dịch", "Xóa chiến dịch"
   - ⛔ Mọi thao tác gửi email thật (chỉ dừng ở bước "Xem trước email" hoặc tick chọn công ty).
3. **Kích thước khung hình (Viewport):**
   - Luôn đặt `"viewport": [1080, 1350]` (chuẩn full-bleed tràn viền).
4. **Dấu mốc (Marks) mạch lạc:**
   - Mỗi cảnh bắt đầu bằng `{"do": "start"}` và dấu mốc đầu cảnh `{"do": "mark", "name": "rong"}` (khung rộng).
   - Đặt dấu mốc sau khi thao tác/khoanh để engine khớp nhịp: `khoanh-xong`, `toi-dong`, `lui`, `het`.
   - `focus`: phóng camera vào vùng chữ mà không khoanh mực.
   - `ink`: khoanh mực vàng và phát âm thanh chọn lựa.

---

## CẤU TRÚC ĐẦU RA (shots.json)
Phải tuân thủ schema `schemas/shots.schema.json`:
```json
{
  "profile": "stradevn",
  "viewport": [1080, 1350],
  "shots": {
    "s1": {
      "note": "C1 hook + C2 rehook: tab dữ liệu thô",
      "steps": [
        {"do": "goto", "url": "${CAMPAIGN_URL}"},
        {"do": "wait", "sec": 1.2},
        {"do": "click", "target": {"css": ":is(a,button,[role=tab]):visible", "has_text": "Dữ liệu tờ khai thô"}, "wait": 1.2},
        {"do": "top"},
        {"do": "start"},
        {"do": "wait", "sec": 0.8},
        {"do": "mark", "name": "rong"},
        {"do": "scroll_to", "target": {"text": "${R_ROW}"}, "frac": 0.45, "dur": 1.4},
        {"do": "mark", "name": "toi-dong"},
        {"do": "focus", "text": "${R_PORT}", "name": "cang", "hold": 0.9},
        {"do": "ink", "text": "${R_ROW}", "name": "24t", "hold": 2.2},
        {"do": "mark", "name": "khoanh-xong"},
        {"do": "top"},
        {"do": "wait", "sec": 2.5},
        {"do": "mark", "name": "lui"},
        {"do": "wait", "sec": 2.0},
        {"do": "mark", "name": "het"}
      ]
    }
  }
}
```
