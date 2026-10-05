# Hypit — tích hợp tuỳ chọn

[Hypit](https://github.com/hypit-ai/hypit) (`@hypit/hypit`) là hệ thống làm video cho agent: nhân bản video mẫu, mốc theo
từng chữ (WhisperX), linh kiện dựng sẵn (bảng xếp hạng, phụ đề karaoke…), ra nhiều biến thể. Render cũng bằng
HyperFrames như kit. **Kit chạy đủ mà không cần Hypit** — thư mục này chỉ để cài nhanh khi muốn thử/dùng.

## Cài (trong thư mục này, không cài toàn máy)
Cần: Node.js ≥ 22.15, [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv` / `brew install uv`), FFmpeg.
```bash
cd integrations/hypit
npm install                 # cài @hypit/hypit 0.2.17 vào node_modules/
npx hypit runtime use hypit.runtime.json
npm run up                  # lần đầu: cài môi trường Python WhisperX + model tiếng Việt + Chrome Headless Shell (vài phút)
npx hypit doctor            # kiểm
npm run down                # tắt dịch vụ cho nhẹ máy
```
`hypit.runtime.json` chỉ dùng công cụ chạy trên máy (media, WhisperX `vi`, HyperFrames) — **không gắn dịch vụ trả phí**.
Muốn dùng model của Hypit (HypiHub) hoặc API key riêng: xem `docs/guide/providers.md` trong repo Hypit.

## Dùng
```bash
npx hypit transcribe <audio|video> --to words.json --language vi   # mốc từng chữ (xem cảnh báo dưới)
npx hypit media frames <video> ...                                 # cắt khung video mẫu
npx skills add hypit-ai/hypit -g                                   # skill /hypit cho Claude Code (nhân bản video mẫu)
```

## Đã đo (05/10/2026, Windows 11, CPU)
| | Kết quả |
| --- | --- |
| Cài + `runtime up` | ✅ chạy |
| WhisperX nghe tiếng Việt | Khá; sai tên riêng ("stray VN" = StradeVn) |
| WhisperX **mốc từng chữ tiếng Việt** | ❌ hỏng: điểm tin cậy ~0,01; bài 54s bị dồn vào 36s |

→ Với tiếng Việt, kit vẫn dùng `tools/speech_segments.py` (đo khoảng lặng, khớp theo cụm). Hướng thử tiếp: model ASR lớn
(`large-v3`, cần GPU), Google Speech-to-Text (có mốc từng chữ), hoặc căn theo kịch bản đã biết.

## Giấy phép
Apache-2.0 có điều kiện: dùng nội bộ / làm video cho khách OK; **SaaS nhiều khách hoặc bán lại cần giấy phép thương mại
của Hypit.AI**. Video làm ra thuộc về mình. Không chép code Hypit vào kit — chỉ cài như phần phụ thuộc.
