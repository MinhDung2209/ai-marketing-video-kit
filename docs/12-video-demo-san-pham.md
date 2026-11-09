# 12 · Video demo sản phẩm (quay màn hình thao tác thật) — `screendemo/`

Loại video: **một ngày làm việc thật** của người dùng sản phẩm, quay màn hình web thật (con trỏ, gõ phím như người),
giọng Gemini kể chuyện, camera phóng đúng con số lời đọc đang nói, phụ đề, sticker, nhạc. Chuẩn làm từ clip
StradeVn "Sầu riêng 0810.60" (04/11/2026, 2 bản: đầy đủ 3:56 + demo dữ liệu cho khách 2:59).

## 1. Ba tầng — ai lo phần nào
| Tầng | Ở đâu | Đổi khi nào |
| --- | --- | --- |
| **Bộ máy** (chung mọi doanh nghiệp) | `KIT/screendemo/` — quay (`rec.py`, `shoot.py`), dựng (`engine.py`, `blocks.py`), hậu kỳ (`produce.py`) | Gần như không đổi |
| **Hồ sơ doanh nghiệp** | `KIT/profiles/<dn>/` — thương hiệu, cách đọc tên, **nút cấm bấm**, luật nội dung, thao tác riêng (`actions.py`), mẫu thể loại (`genres/`) | 1 lần / doanh nghiệp |
| **Clip** | thư mục clip — `clip.json` (biến + chữ trên thẻ), `voice.json` (lời), `shots.json`, `story.py`, bản quay, giọng | Mỗi video |

Đổi mặt hàng / chủ đề **trong cùng thể loại** = chỉ sửa `clip.json` + `voice.json`, chạy lại → không viết code.
Doanh nghiệp mới = thêm 1 hồ sơ (mục 4).

## 2. Clip mới trong 8 bước (vd StradeVn, thể loại "Mã HS hot")
| # | Việc | Lệnh / file | Người duyệt |
| --- | --- | --- | --- |
| 1 | Tạo clip từ mẫu | `python KIT/screendemo/new_clip.py <clip> --profile stradevn --genre ma-hs --slug 02-thanh-long-081040` | |
| 2 | Nghiên cứu: chọn 2 bài báo **cùng chiều thông điệp**, copy NGUYÊN VĂN câu/số sẽ phóng/khoanh → `clip.json` vars `Q_*`, `ART*` | WebSearch + đọc bài | ✋ chốt mặt hàng + bài |
| 3 | Viết lời `voice.json` (giữ số dấu câu như mẫu — mỗi dấu = 1 cụm khớp 1 mốc) + `story` trong `clip.json` | | ✋ duyệt lời |
| 4 | Đọc giọng → nghe | `python KIT/tools/tts_script.py voice.json audio` · `python KIT/screendemo/chunks.py <clip>` (xem cụm) | ✋ nghe |
| 5 | Mở Chrome quay video, **người dùng tự đăng nhập** → quay phần không tốn gì | `python KIT/screendemo/shoot.py <clip> --list` rồi `shoot.py <clip> h2 h5` | |
| 6 | Việc thật (tạo chiến dịch + truy xuất) — **chỉ khi người dùng đồng ý** | `shoot.py <clip> h5 h5b --set CREATE=1` → in `CAMPAIGN_URL` → điền clip.json | ✋ cho phép |
| 7 | Chờ truy xuất xong → đọc số thật → điền `R_*`, `NEWS_COUNT`, `REPORT_*` → quay phần kết quả | `python KIT/screendemo/status.py <CAMPAIGN_URL>?tab=companies 3000` · `shoot.py <clip> h7 h6 h10 h11` | |
| 8 | Soát → render | xem `assets/screen/*/sheet.jpg` · `produce.py <clip> --snap 3,40,90` (Read ảnh) · `produce.py <clip>` | ✋ xem video |

Sau mỗi `shoot.py` có `sheet.jpg` = khung ngay sau mỗi mốc khoanh/phóng → kiểm vòng đỏ đúng chữ, không dính quảng cáo.
`produce.py` render **lần lượt từng bản**, ghi file tạm rồi mới đổi tên (bị dừng giữa chừng không mất bản cũ), in độ dài + LUFS.

## 3. Viết `shots.json` (kịch bản thao tác)
Mỗi bước là 1 dict `{"do": …}`. Biến `${TEN}` lấy từ `clip.json → vars` (list giữ nguyên kiểu, vd `"words": "${HIGH}"`).
| do | Tham số | Ghi chú |
| --- | --- | --- |
| `goto` | url, settle=true | |
| `start` | | bắt đầu ghi hình (mốc `start`). Mọi thứ trước `start` không vào video (mở trang, lọc báo cáo…) |
| `mark` | name | mốc để khớp lời — đặt ngay sau thao tác mà lời đọc nhắc tới |
| `focus` | text, name, scope, scroll, hold | **phóng camera** vào cụm chữ, không vẽ — dùng cho hầu hết các ý |
| `ink` | text, name, scope, scroll, hold | tô vàng + khoanh đỏ — **~1 lần / 10–15 s**, chỉ con số lời đọc nhấn (người duyệt: "mark spam") |
| `click` / `hover` | target, wait | target: `"css"` · `{"text"}` · `{"role","name","exact"}` · `{"css","has_text","nth","last"}` · `{"after_label"}` · `{"frame"}` |
| `type` | text, cps, clear, enter | gõ từng phím có nhịp |
| `press` / `key` | key | `press` có nghỉ, `key` không |
| `fill` / `select` | target, text / label | |
| `scroll` / `scroll_to` / `top` | dy, dur / target, frac / — | |
| `pills` | label, words | ô nhập dạng thẻ (gõ + Enter từng từ) |
| `google` / `open_result` | query / href, name | tìm Google + mở đúng bài (không có bài → báo lỗi để đổi từ khoá) |
| `snap` / `hide_ads` / `dismiss_dialogs` / `wait` / `eval` | | |
| *tên hàm trong `profiles/<dn>/actions.py`* | tuỳ hàm | vd StradeVn: `tab`, `report_snapshot`, `create_campaign`, `start_crawl` |
| `"when": "${CREATE}"` | trên bất kỳ bước nào | chỉ chạy khi biến = 1 |

**An toàn (bắt buộc):** `profile.json → safety.never_click` = chữ trên nút KHÔNG BAO GIỜ bấm (gửi thư, xác nhận, xoá…);
`safety.needs_var` = nút chỉ bấm khi người dùng bật biến (`--set CREATE=1`). `shoot.py` tự chặn trước khi click.

## 4. Doanh nghiệp mới (ngoài StradeVn)
1. `cp -r KIT/profiles/_mau KIT/profiles/<dn>` → điền `profile.json` (thương hiệu, cách đọc tên, nút cấm, luật), logo.
2. Người dùng mở Chrome quay video + đăng nhập web của họ. Agent khảo sát **chỉ đọc**: `python KIT/screendemo/probe.py <url>`
   (liệt kê ô nhập/nút/tab + chữ) → viết `genres/<the-loai>/shots.json` theo luồng làm việc thật của họ.
3. `genres/<the-loai>/story.py`: dùng mẫu `_mau/genres/demo-tinh-nang` (đọc cảnh từ `clip.json → story.scenes`, không code)
   hoặc viết tay như `stradevn/genres/ma-hs/story.py` khi cần cảnh đặc biệt (vd bản demo cắt ngắn đoạn chờ).
4. Làm clip đầu tiên kỹ (mỗi bước người dùng duyệt) → chỗ nào người dùng chê thì ghi thành LUẬT trong `profile.json`
   (`story_rules`, `safety`) để clip sau không lặp lại.

## 5. Bộ dựng (`engine.py`) — điều cần biết khi sửa `story.py`
- `st.screen(rec, from, to, items, badge)` — `items` = `P(câu, i, j, at=(mốc, ±giây), hint, meme)` và `Kf(cụm, at)`.
  Lời bắt đầu nói đúng lúc mốc hiện; đoạn thao tác dài hơn lời → **tua nhanh** (nhãn "⏩ tua nhanh ×N" khi ≥1.8×);
  `hint` > 1 cho phép tua nhanh tới mốc. Lời dài hơn thao tác → đứng hình (0.8×).
- Camera tự phóng vào khung ở mỗi mốc có `focus`/`ink`, lùi ra ở mốc chuyển trang hoặc sau 4,5 s không có mốc mới.
- Cảnh thẻ chữ dựng sẵn (`blocks.py`): `hook_number` (số đếm lên, không sticker), `question`, `clock`, `timeskip`, `recap`, `logo_end`.
- Biến thể: `VARIANT=demo` → `<clip>/demo/` dùng chung assets. Trong story: `if DEMO:` cắt cảnh/đổi `hint`.
- Lỗi "mốc cắt không nằm ở khoảng lặng" → gộp cụm (vd `P("V5", 4, 6)` thay vì 2 cụm) hoặc đọc lại câu đó có ngắt rõ hơn.

## 5b. Sửa sau khi dựng: HyperFrames Studio (D:/Projects/video-studio)
Sau khi bản đầu đạt, chuyển sang project HyperFrames để người và agent (kể cả mô hình rẻ) sửa trực tiếp, không phải dựng lại:
`python KIT/tools/to_studio.py <clip>[/demo] D:/Projects/video-studio/<job>/<clip>-<bản>`.
Lệnh này tách mỗi cụm lời, hiệu ứng và nhạc nền thành một đoạn tiếng riêng (âm lượng sẵn ở -14 LUFS), và ghi thời gian lên chính các thẻ video.
Từ đó **index.html trong video-studio là bản chính**. Đổi lời một câu: `KIT/tools/doi_loi.py`. Xem trên trình duyệt: `npx hyperframes preview`. Xuất: `npx hyperframes render`, có thể kèm `--start/--end`.
Luật sửa cho agent: `video-studio/AGENTS.md`. Cần `cues.json` có `pieces` (engine từ 08/11/2026). Clip cũ thì chạy `produce.py --build` lại.

## 6. Lỗi đã gặp
| Hiện tượng | Cách xử lý |
| --- | --- |
| Vòng khoanh trượt sang dòng khác | rec.py vẽ vòng `position:fixed` bám chữ từng khung (đã sửa). Chữ bị cắt "…" → khoanh cụm khác |
| Quảng cáo trên trang báo lọt vào hình | CSS chặn quảng cáo chèn từ lúc trang bắt đầu dựng (`AD_CSS`). Đừng thêm selector rộng kiểu `[id^="zone-"]` (ẩn cả bài) |
| Bấm tab không ăn (tab nằm ngoài màn hình) | cuộn tab vào giữa trước khi bấm (`actions.tab`) |
| `get_by_text("Công ty")` trúng tab khác | dùng `{"role": "button", "name": "Công ty", "exact": true}` |
| Báo cáo trong iframe không khoanh được | chép DOM iframe ra trang chính trước `start` (`report_snapshot`) |
| Render bị hệ thống dừng vì thiếu RAM | đóng bớt app; `produce.py --only full` rồi `--only demo` |
| ffmpeg chạy nền treo | luôn `-nostdin` / `stdin=DEVNULL` (đã có trong produce/engine) |

## Frame QA tại mốc phóng/khoanh và đầu/cuối cảnh
Sau `--build`, chạy `python KIT/screendemo/produce.py <clip> --qa --qa-source build --only full` trước khi render.
Lệnh dùng lại runtime snapshot, không chạy lại `story.py`, không quay hay đọc giọng; mỗi bản ghi `qa/contact-sheet.jpg` + `qa/checklist.md`.
Mỗi cảnh có ảnh trong giây đầu/cuối; mọi mốc `focus`/`ink` trong đoạn được dùng có ảnh tại mốc và sau 0,35 giây để soát camera/mực.
Mốc bản quay được đổi sang giờ bản dựng bằng `data-offset`, `data-end`, `data-rate`, kể cả đoạn tua nhanh/giữ khung.
Mở contact sheet và điền đủ 4 kiểm tra: chữ/email/số bị cắt mép 1080×1920; phụ đề che số khoanh/CTA; nội dung vào vùng chết; trùng logo góc phải + `logo_end`.
Vùng chết được phủ đỏ bên phải 170px, cam phía dưới 300px. Ô ảnh có số + thời gian; bảng trong checklist ghi tên mốc, để chụp `--snap` lớn hơn khi cần.
Đã có MP4: `produce.py <clip> --qa --only full` (hoặc `--snap-cues`) tự cắt khung từ `final/<slug>-<suffix>.mp4`, không mở Chrome hay render lại.
Dùng `--qa-source video` để bắt buộc chỉ đọc MP4; thiếu MP4 thì dừng. `auto` chưa có MP4 sẽ chụp HTML bằng Chrome headless.
Ảnh từ MP4 chỉ kiểm bản đã xuất; nếu sửa HTML/mốc quay sau đó, lệnh cảnh báo và phải dùng `--qa-source build` để kiểm bản mới trước khi render.
Checklist luôn để trống cho người/agent kiểm bằng mắt, không tự công nhận đạt. `--only demo` ghi vào `<clip>/demo/qa/`.

Khi chuyển sang Studio, `to_studio.py` chép `profile.json → safety`, `story_rules` và `voice.pronounce` vào `studio.json → rules` (cách đọc nằm ở `rules.pronunciation`).

## Khối cảnh · sơ đồ luồng và chữ re-hook (bổ sung)

Hai khối trong `screendemo/blocks.py` dùng `Story.card`, nhận một `P(...)` có ít nhất ba cụm lời và trả về danh sách giờ bắt đầu **tuyệt đối** của mọi cụm. Màu nhấn bắt buộc lấy từ hồ sơ: `st = Story(HERE, brand=profile["brand"])` (hoặc `clip.json["brand"]` đã chép từ hồ sơ). Cần `hl`, `accent` dạng hex `#RGB`/`#RRGGBB`; tùy chọn `bg`, `fg`, `muted` thay màu nền/chữ trung tính.

```python
import blocks as B

# V12: [dữ liệu] [bộ lọc] [kết quả]
B.flow_diagram(st, P("V12", 0, 3),
    nodes=["Dữ liệu", "Bộ lọc", "Kết quả"],
    title="TỪ DỮ LIỆU ĐẾN HÀNH ĐỘNG",
    details=["Chọn đúng đầu vào", "Giữ điều cần thiết", "Sẵn sàng bước tiếp"])

# V13: [câu dẫn] [một số thật + đơn vị] [câu chốt]. Đặt sau cảnh demo để re-hook.
B.kinetic_rehook(st, P("V13", 0, 3),
    value=C["story"]["verified_value"], kicker="NHÌN LẠI KẾT QUẢ",
    unit="email người mua", payoff="ĐÚNG\nNGƯỜI")
```

| Hàm / tham số | Ý nghĩa |
| --- | --- |
| `flow_diagram(st, item, nodes, title="", details=None, cues=(0,1,2))` | Đúng ba nhãn `nodes`; `details` bỏ qua hoặc đúng ba nhãn phụ. Ba thẻ xếp dọc, hai đường sáng SVG vẽ đến thẻ kế tiếp theo lời. |
| `kinetic_rehook(st, item, value, kicker, unit, payoff, cues=(0,1,2))` | Dẫn → số/đơn vị → chữ cắt lớp. `value` là **một** số định dạng sẵn (`"12"`, `"17,8"`); `%` cho vào `unit`. Không đếm số giả. Các trường chữ còn lại không nhận chữ số. |
| `cues` | Ba chỉ số cụm tăng dần, tính từ đầu `item`, không phải giây hay chỉ số toàn câu. Ví dụ `P("V12",2,6), cues=(0,2,3)` chọn cụm toàn câu 2,4,5. Mặc định chọn ba cụm đầu. |

Mọi trường chữ là **plain text**, tự escape HTML và chuẩn hóa Unicode NFC; dùng `\n` để ngắt dòng, không truyền `<b>`/`<br>`. Nạp Be Vietnam Pro có bộ ký tự tiếng Việt qua `fonts.css.part` như các clip khác. Dùng nhãn ngắn (nhãn thẻ một dòng khi có nhãn phụ), payoff tối đa hai dòng ngắn; soát `--snap` nếu số/đơn vị dài. Khối không tự rút gọn hay thu nhỏ chữ.

Khung 1080×1920 dành phần nội dung chính ở x≈100–880, y≈265–1290, chừa phụ đề y=1440. Sơ đồ dùng 68/44px, re-hook dùng 148/44px (44px trùng phụ đề mặc định). GSAP `power3.out`, `immediateRender:false`, giờ tuyệt đối; không timer, ngẫu nhiên, hạt bay hay gradient. ID riêng theo từng cảnh nên gọi nhiều lần trong cùng `Story` được. Sau cue cuối giữ thêm đuôi 0,65s/0,8s để chuyển động kết thúc. SFX chuyển cảnh mặc định vẫn do `Story.card` quản lý.

Preview và kiểm thử: `python KIT/examples/blocks-demo/build.py --snap`, `python KIT/examples/blocks-demo/check.py`. Xem `examples/blocks-demo/README.md`; bốn PNG mẫu nằm ở `orchestration/reports/K02/`.
