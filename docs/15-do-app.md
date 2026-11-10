# 15 · Dò app (`discover.py`) và chạy thử kịch bản thao tác (`dryrun.py`)

Bộ đôi công cụ hỗ trợ quy trình sản xuất video demo màn hình (`screendemo/`):
- `screendemo/discover.py`: Tự động duyệt ứng dụng web theo chế độ **chỉ đọc (read-only)**, thu thập toàn bộ cây phần tử tương tác, bộ chọn (`target`) chuẩn hóa theo định dạng của `shoot.py`, và trích xuất số liệu / sự thật thật (`facts`) từ bảng và thẻ thống kê.
- `screendemo/dryrun.py`: Chạy thử toàn bộ các bước thao tác trong `shots.json` **không ghi hình (không ffmpeg/screencast)**, kiểm tra tính duy nhất của từng selector và sự tồn tại của mọi mốc chữ phóng/khoanh trước khi quay thật.

Mục tiêu cốt lõi: **Mô hình AI hay người viết kịch bản không bao giờ phải đoán selector hay bịa số liệu.**

---

## 1. Nguyên tắc an toàn (SAFETY - Bắt buộc)

Duyệt ứng dụng web thật đòi hỏi tuân thủ nghiêm ngặt tính toàn vẹn dữ liệu:
- **Chỉ đọc (Read-only)**: Không bấm bất kỳ nút nào có nhãn chứa:
  `Tạo chiến dịch`, `Bắt đầu truy xuất`, `Gửi`, `Send`, `Xoá`, `Xóa`, `Delete`, `Lưu`, `Thanh toán`.
- **Không submit form**: Không gửi form lên server, không điền thông tin và nhấn gửi.
- **Không gửi email**: Không kích hoạt bất kỳ luồng gửi email thật nào.
- **Môi trường cách ly**: Chrome chạy trên profile riêng (ví dụ `D:/chrome-profiles/video-rec-disc`) và cổng CDP riêng (mặc định `9350`). Tuyệt đối không can thiệp vào Chrome đang dùng của người quản trị (cổng `9333`).

---

## 2. Dò app: `screendemo/discover.py`

### 2.1. Cú pháp gọi lệnh

```powershell
python screendemo/discover.py <start_url> --out <file.json> [--cdp 9350] [--max-pages 25] [--viewport 1080x1350]
```

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `<start_url>` | *(bắt buộc)* | URL trang bắt đầu dò (ví dụ: trang chiến dịch chi tiết) |
| `--out` | *(bắt buộc)* | Đường dẫn file JSON kết quả (ví dụ: `D:/agent-cache/DISC/inventory.json`) |
| `--cdp` | `9350` | Cổng CDP hoặc URL điều khiển Chrome |
| `--max-pages` | `25` | Số trang / tab tối đa cần khám phá |
| `--viewport` | `1080x1350` | Kích thước khung hình quay (`WxH`) |

### 2.2. Hợp đồng dữ liệu `inventory.json`

```json
{
  "base": "https://tools.stradevn.com/campaigns/36348c09-ff1b-414f-b42e-97282949db33",
  "viewport": [1080, 1350],
  "pages": [
    {
      "url": "https://tools.stradevn.com/campaigns/36348c09-ff1b-414f-b42e-97282949db33?tab=rawShipments",
      "title": "StradeVN Global Sales",
      "screenshot": "screenshots/page_04.png",
      "nav": [
        {
          "label": "Dữ liệu tờ khai thô",
          "target": {"role": "tab", "name": "Dữ liệu tờ khai thô", "exact": true},
          "url": null
        }
      ],
      "elements": [
        {
          "kind": "tab|button|link|input|table|number|heading",
          "label": "Dữ liệu tờ khai thô",
          "target": {"role": "tab", "name": "Dữ liệu tờ khai thô", "exact": true},
          "box": [0, 244, 260, 48],
          "safe": true
        }
      ],
      "facts": [
        {
          "text": "24000 KGS",
          "context": "SẢN PHẨM / dòng 9",
          "target": {"css": "table tr:nth-child(9) td:nth-child(9)"}
        },
        {
          "text": "HARRIS SPICE ASIA PACIFIC LTD",
          "context": "CÔNG TY / dòng 9",
          "target": {"text": "HARRIS SPICE ASIA PACIFIC LTD", "exact": true}
        }
      ],
      "text_path": "texts/page_04.txt"
    }
  ]
}
```

Song song với file JSON, công cụ tự động sinh file `inventory.md` cùng thư mục chứa bảng tổng quan các trang đã dò và danh sách các sự thật mẫu để người phụ trách dễ đọc.

### 2.3. Quy tắc xếp hạng bộ chọn (`target`)

Để đảm bảo bộ chọn có thể chuyển thẳng sang `shots.json` của `shoot.py`:
1. **Ưu tiên 1**: `role` + `name` (chính xác `exact: True`, sau đó đến `exact: False`).
2. **Ưu tiên 2**: Cụm chữ hiển thị `text` (nếu ngắn và duy nhất trên trang).
3. **Ưu tiên 3**: CSS selector (ID `#id`, data attribute `[data-testid=...]`, semantic class + text, hoặc XPath/nth).
4. **Bắt buộc**: Mọi target tạo ra đều được kiểm tra trong DOM thực tế để đảm bảo **chỉ khớp đúng 1 phần tử đang hiển thị (`is_visible`)**. Các phần tử ẩn (`display: none`, `visibility: hidden`, `width=0`, hoặc `mobile-only`) tự động bị loại bỏ.

---

## 3. Chạy thử kịch bản: `screendemo/dryrun.py`

### 3.1. Cú pháp gọi lệnh

```powershell
python screendemo/dryrun.py <clip_dir> [shots...] [--cdp 9350] [--json]
```

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `<clip_dir>` | *(bắt buộc)* | Thư mục chứa `shots.json` và `clip.json` |
| `shots...` | *(tất cả)* | Danh sách cảnh muốn chạy thử (ví dụ: `s1 s3`) |
| `--cdp` | `9350` | Cổng CDP Chrome |
| `--json` | `False` | Xuất kết quả thuần JSON ra stdout (chuẩn công cụ QA) |

### 3.2. Hợp đồng kết quả JSON

Khi toàn bộ bộ chọn và chữ khoanh hợp lệ:
```json
{
  "ok": true,
  "errors": []
}
```

Khi có lỗi bộ chọn mơ hồ hoặc thiếu dữ liệu:
```json
{
  "ok": false,
  "errors": [
    {
      "check": "selector",
      "where": "s3 step 2",
      "msg": "Target {'css': ':is(a,button,[role=tab]):visible', 'has_text': 'Dữ liệu công ty'} resolved to 2 visible elements (ambiguous)",
      "fix_hint": "Disambiguate with role+name, container, or exact text"
    }
  ]
}
```

Quy tắc thoát mã (`exit code`):
- `0`: Khi `ok == true` (không có lỗi).
- `1`: Khi `ok == false` (có lỗi bộ chọn, thiếu biến, hoặc vi phạm an toàn).

---

## 4. Kiểm thử đơn vị (Unit Tests)

Bộ kiểm thử tại `tests/test_discover.py` vận hành **hoàn toàn offline**:
- Sử dụng `http.server` chạy nền nội bộ phục vụ fixture HTML tĩnh `StradeVn Fixture App`.
- Khởi động Chrome headless qua `executable_path="D:/Apps/Google/Chrome/Application/chrome.exe"` mà không cần tải thêm driver qua mạng.
- Bao phủ 6 nhóm kiểm tra:
  1. `test_is_safe_action`: Kiểm tra bộ lọc từ khóa cấm theo nguyên tắc an toàn.
  2. `test_target_uniqueness_ranking_prefers_role_name`: Ưu tiên `role` + `name`.
  3. `test_target_uniqueness_ranking_disambiguation`: Tự động giải quyết phần tử trùng tên qua `text` hoặc ID.
  4. `test_every_extracted_element_has_unique_target`: Mọi target trích xuất đều khớp đúng 1 phần tử hiển thị.
  5. `test_inventory_json_shape`: Định dạng JSON đầy đủ các trường, loại bỏ phần tử ẩn, trích xuất sự thật chuẩn.
  6. `test_dryrun_verification_on_fixture`: Khả năng phát hiện lỗi selector mơ hồ / chữ khoanh không tồn tại của `dryrun.py`.

Chạy kiểm thử:
```powershell
.venv\Scripts\python.exe -m pytest tests/test_discover.py -v
```

---

## 5. Quy trình áp dụng thực tế khi làm clip mới

1. **Khởi động Chrome riêng**:
   ```powershell
   D:\Apps\Google\Chrome\Application\chrome.exe --remote-debugging-port=9350 --user-data-dir=D:\chrome-profiles\video-rec-disc
   ```
2. **Khảo sát webapp**:
   ```powershell
   python screendemo/discover.py https://tools.stradevn.com/campaigns/... --out D:/agent-cache/DISC/inventory.json --cdp 9350 --max-pages 12
   ```
3. **Mở `inventory.md`**:
   - Chọn các số liệu thật (`24000 KGS`, `HARRIS SPICE`, `19 công ty`, `$9,635,200`...) để đưa vào `clip.json` vars.
   - Sao chép các target đã được kiểm định tính duy nhất vào `shots.json`.
4. **Kiểm tra trước khi quay**:
   ```powershell
   python screendemo/dryrun.py <clip_dir> --cdp 9350 --json
   ```
   Nếu `ok: true`, kịch bản sẵn sàng quay thật với `shoot.py`.
