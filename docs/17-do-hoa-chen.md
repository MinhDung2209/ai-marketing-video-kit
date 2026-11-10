# 17 · Đồ hoạ chèn (Motion Graphics Inserts) — `screendemo/templates/inserts/`

Đồ hoạ chèn (motion inserts) là các thành phần đồ hoạ chuyển động ngắn (HTML + CSS + GSAP) được tích hợp trực tiếp vào luồng quay màn hình demo sản phẩm (`screendemo`). Mục đích là giúp các con số mấu chốt (reveal numbers), khối so sánh hoặc lộ trình số liệu tạo ấn tượng thị giác mượt mà, chuyên nghiệp chuẩn Opus/Apple, trong khi tổng thể video vẫn giữ tính chân thực của màn hình thao tác thật.

---

## 1. Nguyên tắc sử dụng (Quy định bắt buộc)

1. **Tần suất & thời điểm xuất hiện:**
   - **Tối đa 1 đồ hoạ chèn / ~15 giây**. Tuyệt đối không lạm dụng hoặc spam liên tục làm loãng nhịp demo phần mềm.
   - **Chỉ xuất hiện khi có con số mấu chốt (reveal numbers)**: khoảnh khắc giọng đọc hé lộ dữ liệu quyết định (ví dụ: số tấn hàng xuất khẩu, số lượng buyer tìm được, mức chênh lệch giá so với đối thủ).
   - Không chèn đồ hoạ chỉ để "trang trí cho đẹp" nếu không gắn liền với thông tin trọng tâm của lời thoại.

2. **Dữ liệu thật từ màn hình (Real recorded data only):**
   - **Tuyệt đối không bịa đặt số liệu**: Tất cả con số, tên công ty, đơn giá, địa danh truyền vào `st.insert(...)` **bắt buộc** phải lấy từ dữ liệu quay thật của clip (khai báo trong `clip.json`, dữ liệu trích xuất từ DOM qua `marks/_dom`, hoặc bảng số liệu hiển thị trong video quay `screen.mp4`).
   - Nhất quán với kịch bản `story.py` và lời dẫn thoại `voice.json`.

3. **Vùng an toàn (Safe Areas) & Thị giác:**
   - Khung hình chuẩn: dọc 1080x1920 (9:16).
   - Canh lề nghiêm ngặt trong vùng an toàn:
     - `safe-top`: `150px` (tránh thanh tiêu đề / solid sharp band trên cùng).
     - `safe-bottom`: `420px` (tránh phụ đề, thanh tiến trình, caption và UI TikTok/Reels).
     - Bảng đồ hoạ (`insert-panel`) luôn được **căn giữa đối xứng theo chiều ngang** (lề trái = lề phải = 60px, chiều rộng chuẩn 960px). Chiều cao bảng ôm sát nội dung (auto-fit), được căn giữa theo chiều dọc trong vùng an toàn, tuyệt đối không để khoảng trống thừa.
   - Thiết kế dạng kính mờ thương hiệu (glassmorphism: nền đen/tím chàm mờ `rgba(30, 27, 75, 0.95)` đến `rgba(11, 16, 32, 0.96)` với viền phát sáng tinh tế), giữ người xem thấy một phần màn hình nền phía sau.
   - **Không dùng emoji** trong đồ hoạ chèn; dùng typography sắc nét, badge phân hạng và SVG vector sạch.
   - Chuyển động 60fps mượt mà, sử dụng easing chuẩn GSAP (`power3.out`, `back.out(1.5)`).

---

## 2. API trong kịch bản `story.py`

Hàm được gọi trực tiếp trên đối tượng `st` (Story instance):

```python
st.insert(kind, t=None, dur=1.6, hold=True, sfx=None, mode="overlay", **data)
```

### Tham số:
- `kind` *(str)*: Loại đồ hoạ chèn. Hỗ trợ 4 loại:
  - `"counter"`: Đếm số lớn kèm nhãn và đơn vị.
  - `"card_stack"`: Xếp chồng 2–4 thẻ bay vào so le (xếp hạng, đối tác, buyer...).
  - `"route"`: Bản đồ vector tối giản với cung đường bay (arc) nối 2 địa điểm.
  - `"compare"`: So sánh 2 chỉ số/đơn giá kèm thanh tiến trình và mũi tên chênh lệch.
- `t` *(float, tuỳ chọn)*: Thời điểm bắt đầu (giây). Nếu `t=None`, đồ hoạ được đặt ngay sau cụm lời thoại vừa gọi (tương tự như `add_meme`).
- `dur` *(float)*: Thời lượng hiển thị (mặc định: `1.6` giây; có thể đặt `1.6s` – `2.2s` tuỳ lượng thông tin).
- `hold` *(bool)*: Nếu `True` (mặc định), giữ timeline của video nền lại để người xem kịp đọc trọn vẹn thông số; đoạn quay nền sẽ dừng hoặc nối dài tương ứng.
- `sfx` *(str, tuỳ chọn)*: Tên hiệu ứng âm thanh đi kèm (mặc định hệ thống tự chọn theo `kind`: `whoosh`, `pop`, `ping`, `chime`).
- `mode` *(str)*: `"overlay"` (mặc định — bảng kính phủ mờ trên màn hình) hoặc `"cut"` (thay thế nền hoàn toàn giữa 2 dải viền an toàn).
- `**data`: Các dữ liệu chi tiết tương ứng với từng loại `kind`.

> [!WARNING]
> Bộ dựng sẽ kiểm tra thời lượng cảnh (`scene`). Nếu đồ hoạ chèn bị đặt quá sát mép cuối của cảnh và thời lượng `t + dur` vượt quá thời lượng cảnh quay, hệ thống sẽ phát sinh lỗi `ValueError: Insert ... vượt quá cảnh kết thúc tại ...`. Để mở rộng cảnh cho vừa insert, truyền `tail=...` vào câu thoại cuối của cảnh trong `story.py`.

---

## 3. Bốn loại đồ hoạ chèn & Mẫu sử dụng

### 3.1. `counter` — Đếm số lớn kinetic
Hiển thị con số nhảy kinetic từ 0 đến giá trị đích (kích thước lớn 250px nổi bật), tự động định dạng chuẩn tiếng Việt (dấu chấm phân cách hàng nghìn, phẩy phân cách thập phân).

```python
st.insert(
    "counter",
    value=19,
    unit="người mua",
    label="Chiến dịch hồ tiêu Mỹ",
    sub="19 công ty tiềm năng xếp hạng sẵn",
    kicker="CHIẾN DỊCH THẬT",
    dur=1.6,
    sfx=S("ping"),
)
```

**Dữ liệu nhận vào (`**data`):**
- `value` *(int/float/str)*: Giá trị con số (vd: `19`, `24.5`, `9635200`).
- `unit` *(str)*: Đơn vị đo (vd: `"người mua"`, `"tấn"`, `"USD"`, `"doanh nghiệp"`).
- `label` *(str)*: Tiêu đề phía dưới số (in hoa hoặc Title Case).
- `sub` *(str, tuỳ chọn)*: Chú thích bổ sung bên dưới.
- `kicker` *(str, tuỳ chọn)*: Nhãn tag phía trên (vd: `"CHIẾN DỊCH THẬT"`).

---

### 3.2. `card_stack` — Danh sách thẻ bay vào so le
Hiển thị từ 2 đến 4 thẻ dữ liệu bay vào theo thứ tự so le (stagger), phù hợp hiển thị top đối tác, buyer nổi bật hoặc các tiêu chí đạt chuẩn.

```python
st.insert(
    "card_stack",
    title="Top người mua hồ tiêu",
    cards=[
        {"rank": 1, "title": "Harris Spice Asia Pacific", "reason": "10 lần nhập · $9,6M", "tag": "White Pepper"},
        {"rank": 2, "title": "St Charles Trading Inc", "reason": "Có email · phản hồi nhanh", "tag": "Chicago"},
    ],
    dur=1.8,
)
```

**Dữ liệu nhận vào (`**data`):**
- `title` *(str)*: Tiêu đề danh sách thẻ.
- `cards` *(list[dict])*: Danh sách 2–4 thẻ, mỗi thẻ gồm:
  - `rank` *(int/str)*: Số thứ tự hoặc thứ hạng (vd: `1`, `2`).
  - `title` *(str)*: Tên đối tượng/doanh nghiệp.
  - `reason` *(str)*: Lý do xếp hạng / mô tả ngắn.
  - `tag` *(str, tuỳ chọn)*: Nhãn phụ (vd: mặt hàng, vị trí).

---

### 3.3. `route` — Cung đường hành trình trên bản đồ
Bản đồ thế giới vector tối giản dạng toạ độ phát sáng (không dùng tile bản đồ bên ngoài), vẽ cung đường cong (SVG arc) từ điểm xuất phát đến đích kèm điểm phát sáng chuyển động và nhãn số lượng hàng hoá.
**Quy tắc:**
- Cả hai đầu cung đường phải có nhãn rõ ràng: điểm xuất phát (Origin tại toạ độ Việt Nam) và điểm đến (Destination tại toạ độ Mỹ).
- Điểm phát sáng chuyển động đúng chiều: từ điểm xuất phát sang điểm đến (Việt Nam → Mỹ).

```python
st.insert(
    "route",
    from_city="Vũng Tàu",
    to_city="Chicago",
    weight="24 TẤN",
    subtitle="Vũng Tàu → Chicago · Đã cập cảng",
    stat="24.000 KGS · 40 BAGS · HỒ TIÊU",
    dur=1.6,
    sfx=S("whoosh"),
)
```

**Dữ liệu nhận vào (`**data`):**
- `from_city` / `origin` *(str)*: Nơi xuất phát (vd: `"Vũng Tàu"`).
- `to_city` / `dest` *(str)*: Nơi đến (vd: `"Chicago"`).
- `weight` / `value` *(str)*: Con số khối lượng / giá trị nổi bật (vd: `"24 TẤN"`).
- `stat` / `desc` *(str)*: Thông tin chi tiết kèm theo (vd: `"24.000 KGS · 40 BAGS · HỒ TIÊU"`).
- `title` *(str, tuỳ chọn)*: Tiêu đề bản đồ (mặc định: `"HÀNH TRÌNH LÔ HÀNG"`).
- `subtitle` *(str, tuỳ chọn)*: Dòng phụ đề dưới tiêu đề.

---

### 3.4. `compare` — So sánh trực quan & Mũi tên chênh lệch
So sánh 2 mức giá hoặc 2 chỉ số giữa Việt Nam và đối thủ, hiển thị cột biểu đồ kèm mức chênh lệch và mũi tên điều hướng (`down` thể hiện giá rẻ hơn / lợi thế cạnh tranh, `up` thể hiện tăng).

```python
st.insert(
    "compare",
    title="Đơn giá theo nước xuất xứ",
    subtitle="Trung vị xuất sang Mỹ (USD/kg)",
    before={"label": "Việt Nam", "value": 6.64, "unit": "$/kg", "sub": "14 dòng dữ liệu"},
    after={"label": "Mexico", "value": 19.48, "unit": "$/kg", "sub": "11 dòng dữ liệu"},
    delta="Tiêu Việt rẻ hơn $12,84/kg",
    direction="down",
    dur=1.6,
    sfx=S("pop"),
)
```

**Dữ liệu nhận vào (`**data`):**
- `title` *(str)*: Tiêu đề so sánh.
- `subtitle` *(str, tuỳ chọn)*: Chú thích đơn vị so sánh.
- `before` / `item_a` *(dict)*: Đối tượng thứ nhất (`label`, `value`, `unit`, `sub`).
- `after` / `item_b` *(dict)*: Đối tượng thứ hai (`label`, `value`, `unit`, `sub`).
- `delta` *(str)*: Dòng chữ thể hiện mức chênh lệch.
- `direction` *(str)*: `"down"` (mũi tên xanh lá chúc xuống - giá rẻ hơn) hoặc `"up"` (mũi tên đỏ chúc lên).

---

## 4. Tích hợp Sound Plan (`insert_events`)

Mỗi khi `st.insert()` được gọi, bộ máy `Story` tự động ghi nhận vào danh sách `st.insert_events`:
```python
{
    "time": 4.90,            # Thời điểm đồ hoạ bắt đầu xuất hiện
    "reveal_time": 5.72,     # Thời điểm con số/nội dung quan trọng bung ra
    "kind": "route",         # Loại đồ hoạ
    "dur": 1.6,              # Thời lượng
    "sfx": "sfx-whoosh.mp3", # File / cue âm thanh
}
```

Các sự kiện này được xuất tự động vào `cues.json` dưới trường `insert_events`, cho phép quy trình âm thanh (`sound_plan` / `mix_audio.py`) tự động ghép hiệu ứng âm thanh trùng khớp từng khung hình chuyển động mà không cần căn chỉnh thủ công.

---

## 5. Kiểm thử & Đảm bảo chất lượng

Trước khi hoàn thiện clip, luôn chạy bộ kiểm thử chuyên biệt cho đồ hoạ chèn:

```powershell
pytest tests/test_inserts.py -v
```

Bộ kiểm thử đảm bảo:
1. Định dạng số tiếng Việt (`fmt_vi_number`) hoạt động chuẩn xác với số nguyên và số thập phân.
2. Kiểm tra ràng buộc thẻ `card_stack` (phải từ 2 đến 4 thẻ).
3. Kiểm tra tính hợp lệ của hướng mũi tên `compare` (`up` hoặc `down`).
4. Kiểm tra phát hiện lỗi vượt quá thời lượng cảnh (`scene overrun`).
5. Render thực tế qua Chrome không đầu (headless Playwright/Chrome) để xác nhận toàn bộ mã JavaScript và timeline GSAP chạy hoàn toàn không có lỗi console (`0 errors`).
