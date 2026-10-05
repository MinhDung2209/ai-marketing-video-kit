# Bên thứ ba: repo, dịch vụ, giấy phép

Kit **không cần cài repo nào trong số này để chạy**. Toàn bộ code trong `tools/` là code tự viết. Các repo dưới đây
được dùng theo 3 cách: học định dạng, lấy âm thanh sạch giấy phép, hoặc tham khảo ý tưởng hook. Commit ghi ở đây là
bản đã kiểm giấy phép ngày 30/09/2026.

## 1. Phần mềm cài trên máy (bắt buộc)
| Phần mềm | Dùng để | Giấy phép | Cài |
| --- | --- | --- | --- |
| **FFmpeg + ffprobe** | Trộn âm, đo khoảng lặng, ghép khung hình thành MP4 (H.264 + AAC) | LGPL/GPL (bản full có libx264 → GPL) | `winget install Gyan.FFmpeg` / `brew install ffmpeg` / `apt install ffmpeg` |
| **Google Chrome** / Chromium | Render từng khung hình (qua Playwright) | Chrome: điều khoản Google · Chromium: BSD | google.com/chrome hoặc `python -m playwright install chromium` |
| Python 3.11+ & gói pip | Xem `requirements.txt` | PSF / Apache / BSD | `pip install -r requirements.txt` |

Lưu ý: kit **gọi** FFmpeg như chương trình ngoài (không nhúng, không sửa mã) nên không bị GPL "lây" sang code kit.

## 2. Repo mã nguồn mở

Clone tất cả về `_repos/` đúng commit đã đọc (để tra cứu, học tiếp): `bash scripts/clone_repos.sh`.
| Repo | Commit | Giấy phép | Kit dùng gì |
| --- | --- | --- | --- |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | 9a27b9f | Apache-2.0 | **Định dạng trang dựng** (data-start/duration, GSAP timeline `window.__timelines`). `render.py` tự viết lại runtime tối thiểu. 19 SFX Pixabay. CLI `npx hyperframes check` (tuỳ chọn) |
| [Vincentwei1021/video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft) | 5ddbf52 | Apache-2.0 (code) | 148 SFX + 4 nhạc Mixkit — **chỉ file có URL gốc Mixkit** trong ATTRIBUTION.md |
| 899ms/uisfx (repo gốc **đã 404 từ 10/2026**) | 9950fe6 | MIT (code) · **CC0 (âm thanh)** | 936 SFX giao diện, 12 bộ phong cách — lưu thẳng trong git, kèm `LICENSE-AUDIO` gốc |
| [arhamhi/hooksmith](https://github.com/arhamhi/hooksmith) | 1a1c13c | MIT | Nguyên tắc hook (viết lại bằng lời mình trong `library/hooks/`) |
| [sharon-laicc/viral-video-decomposer](https://github.com/sharon-laicc/viral-video-decomposer) | 3409359 | MIT | Cách mổ xẻ video viral (tham khảo) |
| [shixinzhang/tiktok-viral-hooks](https://github.com/shixinzhang/tiktok-viral-hooks) | eaae981 | **CC BY-NC-SA 4.0 — cấm thương mại** | Chỉ đọc tham khảo, **không chép nội dung** vào kit |
| [jakeolschewski/short-form-video-scripts](https://github.com/jakeolschewski/short-form-video-scripts) | f4f83d2 | không ghi giấy phép | Chỉ đọc tham khảo |
| [hypit-ai/hypit](https://github.com/hypit-ai/hypit) | 7f730ab (npm 0.2.17) | Apache-2.0 **có điều kiện** (cấm SaaS nhiều khách / bán lại khi chưa mua giấy phép) | Tuỳ chọn, cài riêng ở `integrations/hypit/` — không chép code |
| [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) | 08e2151 | **AGPL-3.0** | Học kiến trúc; **dùng nội bộ thoải mái** (người phụ trách đã cho phép). AGPL chỉ ràng buộc khi phát hành hoặc cho người ngoài dùng qua mạng (vd bán webapp) → lúc đó phải mở mã phần dùng nó |
| [zhuyansen/awesome-claude-video-skills](https://github.com/zhuyansen/awesome-claude-video-skills) | b116824 | CC0 | Danh sách để tìm repo |
| [wilwaldon/Claude-Code-Video-Toolkit](https://github.com/wilwaldon/Claude-Code-Video-Toolkit) | a6e9e52 | không ghi | Danh sách để tìm repo |
| [kapishdima/soundcn](https://github.com/kapishdima/soundcn) | 7cbfbb3 | MIT (code) | **KHÔNG dùng âm thanh**: lẫn 110 file © Blizzard |

## 3. Âm thanh trong `audio-library/`
| Thư mục | Nguồn | Giấy phép | Trong git? |
| --- | --- | --- | --- |
| `sfx/uisfx/` | uisfx | CC0 1.0 | ✅ có |
| `bgm/lyria/` | Tự tạo bằng Google Lyria | Thuộc người tạo (điều khoản Google Cloud) | ✅ có |
| `sfx/pixabay/` | hyperframes → Pixabay | Pixabay Content License: dùng trong video thương mại OK, **cấm phân phối lại file rời** | ✅ có (dùng nội bộ; xem lại khi thương mại hoá) |
| `sfx/mixkit/`, `bgm/mixkit/` | video-shotcraft → Mixkit | Mixkit Free License: như trên | ✅ có (dùng nội bộ; xem lại khi thương mại hoá) |

Nguồn + giấy phép **từng file**: `audio-library/catalog.json`.

## 4. Dịch vụ trả tiền (cần tài khoản)
| Dịch vụ | Dùng để | Ghi chú |
| --- | --- | --- |
| Google Cloud Text-to-Speech, model `gemini-3.1-flash-tts-preview` | Giọng đọc | Bản *preview*, tên model có thể đổi |
| Vertex AI Lyria `lyria-002` | Nhạc nền ~32s | |
| plenxai (MCP `https://mcp.plenxai.com/mcp`) | Ảnh `gpt-image-2.5-flare`, clip `omni-flash-video` | Kiểm điều khoản thương mại của plenxai trước khi bán lại |
