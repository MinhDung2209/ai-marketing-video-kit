# 13 · Tìm nguồn trước khi thu giọng và dựng

Chạy sau khi BRIEF/kịch bản đã được duyệt, trước bước giọng đọc và dựng cảnh. Ghi nhu cầu theo cảnh vào `<project>/sources.json`, tìm ứng viên, xem contact sheet/nghe thử, rồi chọn file để tải. Tìm kiếm không tự chạy generator.

## Thứ tự nguồn

1. Thư viện kit: `audio-library/catalog.json` (sfx/bgm, khớp path + note như `sfx_search.py`), `meme-library/catalog.json` và `web.json` (id + tags, bỏ dấu như `meme_search.py`). Riêng `kind: meme` chỉ tìm duy nhất trong thư viện kit này (không tìm qua Openverse hay Wikimedia để tránh lẫn nội dung rác). File có sẵn được chép; mục web chỉ có URL sẽ được tải khi chọn.
2. Không cần khóa: Openverse audio/images với `license_type=commercial` và loại lại giấy phép NC; Wikimedia Commons ảnh/video, giữ metadata giấy phép và tác giả. (Bỏ qua cho `kind: meme`).
3. Có khóa, tùy chọn: Pexels video/photo, Pixabay video/image, Freesound sfx. Điền `pexels_api_key`, `pixabay_api_key`, `freesound_api_key` trong config riêng của bạn theo `config.example.json`. Khóa trống được bỏ qua im lặng. Khi tìm `broll_video` mà chưa có khóa Pexels/Pixabay, CLI in gợi ý điền khóa để lấy video stock thật. Freesound dùng bản preview MP3 được API cung cấp; không yêu cầu OAuth tải bản gốc.
4. Gợi ý tạo: BGM in lệnh `lyria_bgm.py`; ảnh in lệnh `comfy_image.py` khi có `comfyui_url`. Người phụ trách duyệt prompt/chi phí trước khi tự chạy lệnh tạo.

Xếp hạng ưu tiên nhóm nguồn ở trên, tiếp theo hướng ảnh khớp yêu cầu và số từ khóa trong tiêu đề. `max_dur` loại ứng viên có thời lượng biết được vượt ngưỡng; thời lượng chưa rõ vẫn được giữ để xem lại. Đây là tìm nguồn theo metadata, không phải đánh giá nội dung bằng thị giác. `n` là số ứng viên cuối cùng (mặc định 5, tối đa 50). Các API vẫn được hỏi sau thư viện để có lựa chọn so sánh. Một nguồn lỗi không chặn các nguồn khác; lỗi được ghi trong `candidates.json`.

## Ví dụ clip screen-demo StradeVn

Giữ demo màn hình làm bằng chứng chính; B-roll chèn ngắn ở cảnh mở/bối cảnh. Tạo `sources.json` là **một danh sách JSON**:

```json
[
  {"id":"whoosh","scene":"S1","kind":"sfx","query_en":"whoosh","query_vi":"vút chuyển cảnh","max_dur":2,"n":5},
  {"id":"ping","scene":"S3","kind":"sfx","query_en":"ping","query_vi":"ting thông báo","max_dur":3},
  {"id":"typing","scene":"S2","kind":"sfx","query_en":"typing","query_vi":"gõ bàn phím","max_dur":10},
  {"id":"tech_bgm","scene":"all","kind":"bgm","query_en":"upbeat tech instrumental no vocals","query_vi":"nhạc nền công nghệ vui tươi","n":5},
  {"id":"port","scene":"S1","kind":"broll_video","query_en":"container ship port","query_vi":"tàu container ở cảng","orientation":"landscape","n":5},
  {"id":"chicago","scene":"S4","kind":"broll_video","query_en":"Chicago skyline","query_vi":"đường chân trời Chicago","orientation":"landscape"},
  {"id":"pepper","scene":"S5","kind":"broll_image","query_en":"black pepper close up","query_vi":"hạt tiêu đen cận cảnh","orientation":"landscape"}
]
```

`id` duy nhất, chỉ dùng chữ ASCII, số, `_`, `-`; `scene`, `kind`, `query_en`, `query_vi` bắt buộc. `kind`: `sfx`, `bgm`, `broll_video`, `broll_image`, `meme`. `max_dur` tính bằng giây; `orientation` là `portrait` hoặc `landscape` (ưu tiên, không loại ảnh khác hướng).

```powershell
python <kit>/tools/find_sources.py <project>
python <kit>/tools/find_sources.py <project> --fetch whoosh:1 port:2 pepper:1
```

Kết quả: `sources/candidates.json` chứa nhu cầu và ứng viên có `rank` bắt đầu từ 1, nguồn, tiêu đề, URL trang/file/preview, giấy phép, ghi công, thời lượng, kích thước byte, width/height và hướng nếu biết. `sources/contact-sheet.jpg` có nhãn ID/hạng cho từng ứng viên hình, sử dụng font chữ có hỗ trợ đầy đủ ký tự tiếng Việt (Arial, Segoe UI, hoặc fallback sang font kit trong `assets/fonts`); preview của meme được tạo khung hình thực tế và lưu đệm tại `<project>/sources/previews/` (render frame từ webm của noto, trích xuất frame bằng ffmpeg từ URL hoặc thumbnail của web.json). Preview không tải được vẫn có ô nhãn. Video Commons có thể chưa có preview hoặc duration. Ảnh preview chỉ dùng để duyệt; bản gốc chỉ tải khi `--fetch`.

`--fetch` dùng lại danh sách đã lưu, không tìm lại làm thay đổi hạng. File vào `assets/src/<id>.<ext>`; chọn lại cùng ID/đuôi sẽ thay file. Chọn nhiều hạng của cùng ID lần lượt sẽ giữ bản cuối; hãy dùng ID riêng khi cần nhiều file. Mỗi lần chọn thành công nối nguồn, giấy phép, ghi công vào `sources/credits.md`. Nếu nguồn chỉ công bố giấy phép chưa rõ (đặc biệt meme web), cần xem trang nguồn và chốt quyền dùng trước khi xuất bản; công cụ không suy diễn quyền thương mại từ một URL.

Với audio, CLI in danh sách và lệnh `sfx_audition.py`. File local nghe thử ngay; nguồn online cần `--fetch` trước rồi dùng đúng đường dẫn/đuôi file được in khi tải:

```powershell
python <kit>/tools/sfx_audition.py <project>/sources/audio-audition.mp3 <project>/assets/src/whoosh.mp3 <project>/assets/src/ping.wav
```

## Ảnh Qwen-Image qua ComfyUI

Trong config riêng, đặt `comfyui_url` (ví dụ `http://127.0.0.1:8188`) và `comfyui_workflow` (đường dẫn workflow JSON tuyệt đối hoặc tương đối với kit). Xuất workflow Qwen-Image **dạng API** từ ComfyUI, giữ nguyên model/nodes/SaveImage của workflow đã chạy được. Thay đúng các giá trị input bằng chuỗi placeholder toàn phần:

- Input text của encoder prompt dương: `"{{prompt}}"`.
- Input width và height của latent: `"{{width}}"`, `"{{height}}"`.
- Input seed/noise_seed của sampler: `"{{seed}}"`.

Client thay placeholder bằng chuỗi prompt hoặc số tương ứng, yêu cầu đủ bốn placeholder để tránh chạy nhầm prompt/kích thước. Giữ prompt âm và các input khác như bản workflow gốc. Không dùng JSON giao diện có mảng `nodes`.

```powershell
python <kit>/tools/comfy_image.py "black pepper macro photograph" <project>/assets/src/pepper.png --width 1344 --height 768 --seed 42 --wait 600
```

Client POST `/prompt`, thăm `/history/<prompt_id>` mỗi 2 giây rồi tải ảnh output đầu tiên từ `/view`; báo lỗi khi job thất bại hoặc quá thời gian chờ. Quá thời gian chờ không hủy job đang chạy trên máy chủ. Nguồn tạo không tự thêm credits của kho ảnh; lưu workflow/prompt theo quy trình tạo ảnh của dự án.

Tham chiếu API: [Openverse](https://api.openverse.org/v1/), [Pixabay](https://pixabay.com/api/docs/).
