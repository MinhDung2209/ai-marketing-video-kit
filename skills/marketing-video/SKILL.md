---
name: marketing-video
description: Làm video quảng cáo ngắn (Reels/TikTok/Ads, 9:16, 30–60s) bằng AI từ đầu tới MP4 — kịch bản có hook, giọng Gemini-TTS có đạo diễn, ảnh/clip AI plenxai giữ đúng nhân vật, nhạc Lyria, hiệu ứng âm thanh khớp hoạt ảnh, phụ đề, render 1080p. Dùng khi người dùng nói "làm video marketing/quảng cáo", "video Reels/TikTok cho sản phẩm", "video AI cho dự án …".
---

# Làm video marketing AI (marketing-video-kit)

KIT = <ĐƯỜNG DẪN TỚI THƯ MỤC kit>   ← cài bằng `python tools/install_skill.py` (tự điền). Tài liệu đầy đủ: `KIT/docs/00..10`. Ví dụ thật: `KIT/examples/stradevn-ad-v2/`.

## Luật bắt buộc
1. **Không tạo ảnh/clip AI khi chưa được duyệt**: gửi request (model, tỉ lệ, độ phân giải, ảnh tham chiếu, prompt) → chờ OK.
   Hạn mức credit do người dùng đặt; ghi sổ `credits.md` mỗi lần gọi (kể cả timeout).
2. **Không bịa** số liệu, kết quả, thời gian, lời chứng thực. KOL AI = người dẫn chuyện, không đóng vai khách hàng.
3. **Logo chính xác = chèn file thật** khi dựng. Không lộ dữ liệu cá nhân (làm mờ).
4. **Bạn không nghe được âm thanh** → mọi giọng/nhạc/hiệu ứng phải để người dùng nghe duyệt; SFX nghi ngờ → `sfx_audition.py`.
5. **Kiểm bằng mắt trước khi báo xong**: `render.py --snap` rồi Read ảnh; sau render cắt khung từ MP4 + đo âm lượng.
6. Người dùng chưa duyệt kịch bản thì chỉ chạy thử công cụ, không dựng bản chính.

## Quy trình
0. **Máy mới:** `python KIT/tools/check_env.py` — có ❌ thì sửa theo dòng → (thiếu âm thanh: `fetch_sources.py`).
1. **Dự án:** `python KIT/tools/new_project.py <thư mục>`.
2. **Kịch bản `BRIEF.md`** (KIT/docs/03 + `KIT/library/hooks/THU-VIEN-HOOK.md`): ý tưởng lớn · 3–4 hook (đánh vào cảm xúc,
   không bám số liệu) · 5 nhịp Hook → Nỗi đau → Lời giải/rehook → Bằng chứng → Kêu gọi · từng cảnh: lời + hình + chữ + âm
   thanh · bảng prompt ảnh/clip. → **người dùng duyệt**.
3. **Giọng** (KIT/docs/04): `voice.json` = model `gemini-3.1-flash-tts-preview`, giọng Kore, `profile` + `direction` từng câu
   + thẻ `[short pause]`… (không SSML). `python KIT/tools/tts_script.py voice.json audio` (`--only V3` đọc lại 1 câu).
   → **người dùng nghe duyệt**.
4. **Ảnh/clip AI** (KIT/docs/05): ảnh gốc KOL trước; `generate_image` model `gpt-image-2.5-flare`, `resolution: "2k"`,
   `references_urls` = [ảnh gốc, logo] + câu "The SAME woman as the reference…". Clip: `generate_video_omni`
   model `omni-flash-video`, `video_mode: "i2v"`, `resolution: "1080p"`, `duration: 6`, **1 động tác / clip**.
   Gọi tuần tự; timeout = vẫn đang tạo → xin người dùng link từ web plenxai; ảnh đổi đuôi `format=png,quality=100`.
5. **Nhạc** (KIT/docs/06): `python KIT/tools/lyria_bgm.py "<prompt>" bgm/a.wav --seed N` (2 đoạn seed khác → acrossfade)
   hoặc `sfx_search.py --kind bgm`. → **người dùng nghe**.
6. **Dựng** (KIT/docs/07): nhanh = `scenes.json` + `python build.py`; tuỳ biến = sửa `index.src.html` + `build.py` như ví dụ.
   Mốc hoạt ảnh bám lời bằng `speech_segments.py` (không ước lượng ký tự). Clip lỗi đoạn cuối: `data-offset/data-end/data-rate`.
7. **Trộn:** `python KIT/tools/mix_audio.py cues.json assets/final_audio.mp3` (SFX tự chuẩn hoá đỉnh; nhạc duck).
8. **Xem thử:** `python KIT/tools/render.py . --snap 1,5,12,…` → Read `_snap_*.png` → sửa.
8b. **Chạy gộp:** `python KIT/tools/make_video.py <dự án> [--from mix|--only snap]` (không đọc lại giọng đã có).
9. **Render:** `python KIT/tools/render.py . --fps 30 --audio assets/final_audio.mp3 --out <tên>.mp4`
10. **Kiểm** (KIT/docs/08): ffprobe, volumedetect, cắt khung từ MP4, checklist → báo người dùng đường dẫn + điều cần nghe/xem.

## Khi người dùng góp ý
Sửa đúng chỗ, chạy lại từ bước bị ảnh hưởng (bảng ở KIT/docs/02 bước 8). Ghi góp ý + ngày vào đầu BRIEF.md.
Lỗi đã gặp và cách xử lý: KIT/docs/09.
