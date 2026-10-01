# 01 · Cài đặt (làm 1 lần, ~30–60 phút)

Đã chạy thật trên: Windows 11, Python 3.14, FFmpeg 8.1, Chrome, Git Bash. Mac/Linux làm tương tự (đổi đường dẫn).

## 1. Phần mềm trên máy
| Phần mềm | Kiểm tra | Cài |
| --- | --- | --- |
| Python ≥ 3.11 | `python --version` | python.org (tick "Add to PATH") |
| FFmpeg (bản *full*, có ffprobe) — **bắt buộc**, không cài qua pip | `ffmpeg -version` | Windows: `winget install Gyan.FFmpeg` · macOS: `brew install ffmpeg` · Ubuntu: `sudo apt install ffmpeg` (cài xong mở lại cửa sổ lệnh) |
| Google Chrome | có biểu tượng Chrome | google.com/chrome — `render.py` tự dò; chỗ cài lạ → biến `VIDEOKIT_CHROME`; không có Chrome → `python -m playwright install chromium` |
| Git (+ Git Bash trên Windows) | `git --version` | git-scm.com — cần cho `tools/fetch_sources.py` |
| Node.js 22+ (tuỳ chọn) | `node -v` | chỉ cần nếu dùng CLI HyperFrames (`npx hyperframes check`) |
| Claude Code (khuyên dùng) | `claude --version` | docs.claude.com |

## 2. Thư viện Python
```bash
pip install -r kit/requirements.txt
```
(Playwright ở đây chỉ điều khiển Chrome có sẵn — **không** cần `playwright install` nếu máy có Chrome.)

Rồi tải phần âm thanh Pixabay/Mixkit (không lưu trong git vì giấy phép cấm phân phối lại file rời) và kiểm cả máy:
```bash
python kit/tools/fetch_sources.py   # clone 3 repo nguồn vào _repos/ → dựng lại kit/audio-library
python kit/tools/check_env.py       # ✅/❌ từng mục: Python, pip, FFmpeg, Chrome, key Google, âm thanh
```

## 3. Key Google Cloud (giọng đọc + nhạc Lyria)
1. Vào console.cloud.google.com → chọn/tạo project → **bật Billing**.
2. Bật API: **Cloud Text-to-Speech API** và **Vertex AI API**.
3. IAM → Service Accounts → tạo tài khoản dịch vụ (vd `marketing-video`), cấp quyền tối thiểu: *Cloud Text-to-Speech User*
   (hoặc Editor nếu chưa rõ) + *Vertex AI User*. → Keys → Add key → JSON → tải file về.
4. Để file key ở chỗ riêng (KHÔNG để trong kit, KHÔNG gửi ai). Rồi:
   ```bash
   cp kit/config.example.json kit/config.json      # sửa "gcp_key_path" trỏ tới file key
   ```
   hoặc đặt biến môi trường `VIDEOKIT_GCP_KEY=<đường dẫn file key>`.
5. Thử: `python kit/tools/tts_script.py kit/templates/video-project/voice.json _thu` → ra `_thu/narration.mp3` là xong.

> Mẹo: dùng service account **riêng cho marketing** để tách chi phí với sản phẩm chính.

## 4. plenxai (ảnh + clip AI) qua MCP
- Có tài khoản plenxai + credit. MCP endpoint: `https://mcp.plenxai.com/mcp` — thêm vào Claude Code
  (`claude mcp add` hoặc cấu hình MCP của máy). Công cụ dùng: `generate_image`, `generate_video_omni`.
- Đặt hạn mức credit cho mỗi dự án (vd 700) và ghi sổ chi (`credits.md`) — endpoint xem số dư của MCP có lúc lỗi.
- Ảnh/clip tạo lâu hơn giới hạn chờ MCP (~4 phút) → MCP báo *timeout* nhưng vẫn tạo xong trên web plenxai → vào web
  copy link về. Đừng gọi lại ngay (tạo trùng, tốn credit).

## 5. Quyền trong Claude Code (nếu dùng auto mode)
Claude Code có thể chặn chạy code tải từ ngoài. Nếu cần HyperFrames CLI: `/permissions` → thêm `Bash(npx hyperframes:*)`.
Các công cụ trong `tools/` là Python cục bộ, không cần quyền đặc biệt.

## 6. Cài skill cho Claude Code
```bash
python kit/tools/install_skill.py                      # dùng mọi nơi (~/.claude/skills/) — tự điền đường dẫn KIT
python kit/tools/install_skill.py --project <thư mục>  # chỉ cho 1 dự án
```
Sau đó mở Claude Code, nói: *"làm video marketing cho …"*. Kéo bản kit mới (`git pull`) thì chạy lại lệnh trên.

## 7. Đóng gói mang sang máy khác
```bash
python kit/tools/make_package.py              # dist/marketing-video-kit-YYYYMMDD.zip (có ví dụ ~110 MB)
python kit/tools/make_package.py --no-example # bản nhẹ
```
Gói tự loại `config.json` (đường dẫn key riêng). Máy mới: giải nén → làm lại mục 1–4.
