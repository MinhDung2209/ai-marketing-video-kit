# OpenFilm và OpenMontage: nên lấy gì cho kit video marketing?

Ngày kiểm chứng: **09/11/2026**. Số sao là ảnh chụp GitHub API lúc tra cứu; giờ commit/release dưới đây là **UTC**. Đây là nghiên cứu tài liệu và mã nguồn qua HTTP, chưa chạy các app trên máy này. Không clone, cài gói, gọi API tạo media hoặc tải tư liệu khách hàng.

**Đề xuất:** giữ HyperFrames và quy trình hiện tại. OpenFilm đáng học cách kiểm tính tất định và giữ chỉnh sửa của người dùng; OpenMontage đáng học quy trình chọn tư liệu, checkpoint và kiểm đầu ra. **Chưa đáng tích hợp nguyên hệ thống nào.** Subscription coding agent phục vụ viết code; không tự cấp quyền dùng API tạo ảnh, giọng hoặc video. Đường không cần key phải dựa vào media có sẵn, đồ hoạ bằng code hoặc model local đã thiết lập.

## 1. Xác định đúng repo

Đã tìm web và GitHub với `OpenFilm`, `open-film`, `OpenMontage`, `open-montage`, rồi đọc metadata/README và một số file triển khai. Đây là các ứng viên liên quan, không phải toàn bộ kết quả tìm kiếm.

### OpenFilm

| Repo / owner | Sao | Nó là gì và vì sao chọn/bỏ |
| --- | ---: | --- |
| **[openfilm/openfilm](https://github.com/openfilm/openfilm)** — `openfilm` | **5.375** | **Chọn chính:** coding agent viết phim bằng HTML; có Studio sửa hình/timeline và render local. Sát nhất với video ngắn dựng bằng code của kit. |
| [bynanci/open-film](https://github.com/bynanci/open-film) — `bynanci` | 2 | Editor local để tổ chức media, lên câu chuyện, dựng thô và xuất NLE; phân tích bổ sung bên dưới. |
| [newopenapi/openfilm](https://github.com/newopenapi/openfilm) — `newopenapi` | 30 | Canvas node tạo ảnh/video: React/TypeScript/Vite, backend proxy, key Gemini/Kling/Hailuo/OpenAI/fal/Volcengine. README nêu Electron/local diffusion nhưng chưa xác minh các nhánh đó. **Là repo khác**, không có bằng chứng là tên cũ của `openfilm/openfilm`. [README](https://github.com/newopenapi/openfilm/blob/main/README.md) |
| [Pbihao/OpenFilm](https://github.com/Pbihao/OpenFilm) — `Pbihao` | 4 | React, agent tạo storyboard/keyframe/video và timeline. Yêu cầu **OpenRouter + fal.ai key**, gọi trực tiếp browser→API; không hợp điều kiện hiện tại. [README](https://github.com/Pbihao/OpenFilm/blob/main/README.md) |
| [skolmuirgheasa/openfilmai](https://github.com/skolmuirgheasa/openfilmai) — `skolmuirgheasa` | 4 | Điều phối shot sinh AI bằng trạng thái cảnh/nhân vật kế thừa; Python + React/Electron theo README. Thiên về phim có nhân vật liên tục; chưa chứng minh lợi ích cho demo B2B. [README](https://github.com/skolmuirgheasa/openfilmai/blob/main/README.md) |

Metadata bổ sung: `newopenapi` commit `8f9679f3e1` ngày 12/04/2026; README gắn nhãn Apache-2.0 nhưng API trả license `null`, cây repo không thấy LICENSE/COPYING: **chưa xác nhận quyền tái sử dụng**. `Pbihao` commit `25d3631b69` ngày 31/03/2026; API nhận diện `Other`, nhưng [LICENSE](https://github.com/Pbihao/OpenFilm/blob/main/LICENSE) chứa Apache 2.0, copyright Aixio. `skolmuirgheasa` commit `18d112c376` ngày 21/01/2026, MIT. Mức sao/nhãn README không chứng minh chất lượng thực tế.

### OpenMontage

| Repo / owner | Sao | Nó là gì và vì sao chọn/bỏ |
| --- | ---: | --- |
| **[OpenMontageInc/OpenMontage](https://github.com/OpenMontageInc/OpenMontage)** — `OpenMontageInc` | **78.724** | **Chọn chính:** hệ thống sản xuất do coding agent điều phối, có HyperFrames/FFmpeg, screen demo và montage footage thật. URL cũ [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) chuyển hướng tới đây; kit đã tham chiếu URL cũ. |
| [47thtechcorner/RayCodes_OpenMontage](https://github.com/47thtechcorner/RayCodes_OpenMontage) — `47thtechcorner` | 63 | Quảng bá Ollama + HyperFrames + FFmpeg local. Nhưng [pipeline.py](https://github.com/47thtechcorner/RayCodes_OpenMontage/blob/main/pipeline.py) chỉ liệt kê/chọn model, dựng manifest cố định từ `reference_video.mp4`, chép template và render. Trong hàm chạy không thấy suy luận Ollama, `prompt` chưa được sử dụng; chưa thể gọi là tự dựng hoàn chỉnh theo prompt. |
| [charliewwdev/OpenMontage](https://github.com/charliewwdev/OpenMontage) — `charliewwdev` | 28 | Drama Studio tự host: ý tưởng→kịch bản→nhân vật→storyboard→video/giọng/dựng. README yêu cầu LLM key và Seedream/Seedance trả phí, dùng edge-tts + FFmpeg. Liên quan quảng cáo ngắn nhưng không hợp subscription-only. [README](https://github.com/charliewwdev/OpenMontage/blob/main/README.md) |
| [digimads-lab/OpenMontage](https://github.com/digimads-lab/OpenMontage) — `digimads-lab` | 7 | Ý tưởng cộng tác làm phim qua Discord, chọn shot và chia doanh thu; README ghi pre-alpha/planning. Không phải bộ auto-edit local cần cho kit. [README](https://github.com/digimads-lab/OpenMontage/blob/main/README.md) |

Metadata bổ sung: RayCodes commit `5900928cdf` ngày 22/06/2026; API không có license cấp repo, nhưng `openmontage_engine/` có [AGPL-3.0](https://github.com/47thtechcorner/RayCodes_OpenMontage/blob/main/openmontage_engine/LICENSE), không được coi toàn bộ repo là MIT. Drama Studio commit `481aeca474` ngày 08/11/2026, AGPL-3.0. `digimads-lab` commit `0bc572483e` ngày 03/03/2026, Apache-2.0.

**Kết quả dễ nhầm:** web search trả `Open-Montage-app/OpenMontage` quảng bá bộ cài Windows/macOS/Linux. GitHub API trực tiếp trả repo đó **404**, trong khi repo chính có danh sách release rỗng. Không xác nhận hoặc khuyên tải các bộ cài này. API xác nhận `vorale/openmontage` là fork có parent `OpenMontageInc/OpenMontage`; không phải dự án độc lập.

## 2. Hai dự án chính thực sự làm gì?

### OpenFilm: agent viết phim bằng web, người sửa bằng editor

| Mục | Đã xác minh |
| --- | --- |
| Repo / owner / license | [openfilm/openfilm](https://github.com/openfilm/openfilm), tổ chức `openfilm`; [MIT](https://github.com/openfilm/openfilm/blob/a85a80a9742981f0f77f61df88a2780984f8f3fb/LICENSE). |
| Hoạt động gần nhất | **5.375 sao**; main [`a85a80a974`](https://github.com/openfilm/openfilm/commit/a85a80a9742981f0f77f61df88a2780984f8f3fb), **08/11/2026 20:25:53 UTC**. Release [v0.3.1](https://github.com/openfilm/openfilm/releases/tag/v0.3.1), **08/11/2026 21:21:21 UTC**. `pushed_at` không dùng thay ngày commit. |
| Bản chất | Công cụ cho coding agent dựng phim và editor local. Không phải một model text-to-video; sinh pixel bằng AI là việc của provider riêng. |
| Stack | CLI Node.js/JavaScript ESM; `playwright-core` + Chromium + FFmpeg. Studio React/TypeScript/Vite; desktop **Electron**, không phải Tauri. [Package CLI/Studio](https://github.com/openfilm/openfilm/blob/a85a80a9742981f0f77f61df88a2780984f8f3fb/packages/openfilm/package.json), [package desktop](https://github.com/openfilm/openfilm/blob/a85a80a9742981f0f77f61df88a2780984f8f3fb/apps/desktop/package.json). |
| Đầu vào / project | Media local và các trang cảnh; `film.html` mô tả track/clip, vị trí, gain, tốc độ. Cảnh công bố `window.film.frame(t)`: cùng t phải cho cùng hình bất kể thứ tự tua. **Format riêng**, không phải HyperFrames. [Protocol](https://github.com/openfilm/openfilm/blob/a85a80a9742981f0f77f61df88a2780984f8f3fb/packages/openfilm/SPEC.md) |
| Đầu ra | README nêu MP4, GIF, âm thanh/stems, phụ đề, stills, slide, video trong suốt và timeline cho Final Cut/Premiere/Resolve. Chưa thử độ trung thực khi chuyển NLE; không mặc định mọi effect còn sửa được. [README](https://github.com/openfilm/openfilm/blob/a85a80a9742981f0f77f61df88a2780984f8f3fb/README.md) |
| Windows | CLI công bố Windows/macOS/Linux, **Node ≥22.2 + FFmpeg**, Git cho saved versions; lần đầu tải Chromium khoảng 100 MB. Release có `OpenFilm-Setup-x64.exe`. Checkout phát triển yêu cầu Node ≥22.18, khác mức CLI. Chưa chạy thử trên máy chủ. [Release](https://github.com/openfilm/openfilm/releases/tag/v0.3.1), [package gốc](https://github.com/openfilm/openfilm/blob/a85a80a9742981f0f77f61df88a2780984f8f3fb/package.json) |
| Phần cứng | Chưa thấy mức RAM/VRAM tối thiểu chính thức cho toàn app. Dựng DOM/GSAP/media không bắt buộc diffusion/CUDA local; WebGL/3D phụ thuộc cảnh và GPU trình duyệt. Không có cơ sở hứa “8 GB đủ cho mọi phim”. |

**Model và tiền:** dùng coding agent đã đăng nhập bằng subscription để tạo/sửa code được. Dựng/chỉnh/render media sẵn có không cần tài khoản OpenFilm. Tạo media mới chọn key riêng hoặc **mua credit OpenFilm**; credit là chi phí riêng. [Services](https://openfilm.dev/docs/services/) phân biệt các đường thanh toán này.

Adapter đã đọc: Google cloud qua `GEMINI_API_KEY`, khai báo `gemini-3.8-flash-tts`, `gemini-3.1-flash-image`, `gemini-omni-1.2-flash`; OpenAI có `gpt-4o-mini-tts`, `whisper-1`; local provider có **Whisper Small/Large v3 Turbo** cho transcript và **BiRefNet** tách nền. Đây là ID/chức năng **được khai báo trong source**, chưa gọi live kiểm quyền hay chất lượng. Không có bằng chứng OpenFilm kèm local diffusion cho mọi ảnh/video. [Google adapter](https://github.com/openfilm/openfilm/blob/a85a80a9742981f0f77f61df88a2780984f8f3fb/packages/openfilm/studio/server/providers/google.mjs), [OpenAI adapter](https://github.com/openfilm/openfilm/blob/a85a80a9742981f0f77f61df88a2780984f8f3fb/packages/openfilm/studio/server/providers/openai.mjs), [local adapter](https://github.com/openfilm/openfilm/blob/a85a80a9742981f0f77f61df88a2780984f8f3fb/packages/openfilm/studio/server/providers/local.mjs).

Hai chi tiết sát kit: `look` thực sự render cùng các mốc hai lần với hai thứ tự xáo trộn để phát hiện hình không nhất quán; `overrides` lưu chỉnh sửa phần tử bên trong trang cảnh, agent được hướng dẫn giữ chúng. Không có bằng chứng cơ chế này tự giữ mọi sửa tay khi tái sinh project HyperFrames. [look.mjs](https://github.com/openfilm/openfilm/blob/a85a80a9742981f0f77f61df88a2780984f8f3fb/packages/openfilm/src/look.mjs), [hướng dẫn edit](https://github.com/openfilm/openfilm/blob/a85a80a9742981f0f77f61df88a2780984f8f3fb/packages/openfilm/manual/edit/SKILL.md).

### OpenMontage: dây chuyền do coding agent điều phối

| Mục | Đã xác minh |
| --- | --- |
| Repo / owner / license | [OpenMontageInc/OpenMontage](https://github.com/OpenMontageInc/OpenMontage), `OpenMontageInc`; [AGPL-3.0](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/LICENSE). `calesthio` là URL cũ. |
| Hoạt động gần nhất | **78.724 sao**; main [`356b5fa924`](https://github.com/OpenMontageInc/OpenMontage/commit/356b5fa92474998c9f9a0782fd5547d05837d284), **08/11/2026 00:41:51 UTC**. `/releases?per_page=3` trả `[]`: chưa có GitHub Release công khai lúc kiểm. |
| Bản chất | Agent đọc YAML/Markdown, gọi Python tools, ghi JSON checkpoint, duyệt từng bước. Không có Python orchestrator tự thay agent. Auto-montage là một pipeline trong hệ thống rộng hơn. Backlot là board/storyboard local theo dõi sản xuất; không nên gọi là NLE tương đương Studio. |
| Stack | Python, Pydantic/JSON Schema, YAML; FFmpeg; renderer HyperFrames hoặc React/Remotion, cả đường FFmpeg. Backlot dùng FastAPI/SSE. Runtime chọn ở proposal, lưu trong `edit_decisions.render_runtime`. [Kiến trúc](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/docs/ARCHITECTURE.md) |
| Đầu vào / đầu ra | Ý tưởng/brief, media người dùng hoặc video tham chiếu theo pipeline. Script→scene plan→asset manifest→edit decisions→render; lưu JSON/checkpoint, MP4 cuối, ví dụ `projects/<name>/renders/final.mp4`. [Screen-demo manifest](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/pipeline_defs/screen-demo.yaml) |
| Montage footage thật | `documentary-montage` tìm/cắt footage, có CLIP retrieval và provenance/license. Manifest ghi **beta**, **`reference_input.supported: false`** dù README nói hệ thống nói chung nhận video tham chiếu. Có fast path tìm trực tiếp, không buộc mọi lần lập corpus CLIP. [Manifest](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/pipeline_defs/documentary-montage.yaml) |
| Windows | README có hướng dẫn PowerShell: Python ≥3.10, Node bản upstream chỉ định, FFmpeg, coding agent. Node hiện pin 22.23.4; không phải Node bất kỳ. Recorder có Windows **gdigrab + dshow**. Không có cơ sở nói bắt buộc WSL; chưa thử native E2E. [README](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/README.md), [recorder](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/tools/capture/screen_recorder.py) |
| Máy khi không sinh AI local | HTML/FFmpeg/Piper không bắt buộc GPU CUDA. CLIP mặc định CPU, tự chọn CUDA nếu có, tải `openai/clip-vit-base-patch32`; cần torch/transformers và dung lượng model riêng. Chưa thấy RAM tối thiểu toàn hệ thống được kiểm chứng. [clip_embedder.py](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/lib/clip_embedder.py) |

**Local/cloud và tiền:** điều phối tận dụng coding assistant hiện có; không cần LLM API key riêng chỉ cho điều phối. README vẫn ghi Ollama/LM Studio native orchestration là *coming soon*, nên chưa kết luận hệ thống chính chạy toàn bộ LLM offline. Media tools cần credential riêng; tên provider trong `config.yaml` không chứng minh có quyền truy cập. [Kiến trúc](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/docs/ARCHITECTURE.md), [config](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/config.yaml).

Upstream tài liệu hoá cloud Kling/fal, Veo, GPT Image, ElevenLabs/Google TTS; local **Piper**, WAN 2.1/2.2, Hunyuan, CogVideo, LTX, Stable Diffusion/ComfyUI. Đây là adapter/tuyến tích hợp, không phải weights đóng gói sẵn. Piper cần binary + voice model; mặc định tool là `en_US-lessac-medium`, **chưa xác nhận giọng Việt phù hợp**. [Provider guide](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/docs/PROVIDERS.md), [Piper tool](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/tools/audio/piper_tts.py).

Theo upstream, local video NVIDIA/CUDA có mốc VRAM tham khảo: WAN 2.1 1.3B **6 GB**, WAN 2.2 TI2V 5B **12 GB**, WAN 2.1 14B **24 GB**, LTX-2 **8 GB**, Hunyuan 1.5 **12 GB**, CogVideo 5B **10 GB**. Đây không phải benchmark trên máy chủ; resolution/frame count/quantization/offload/workflow thay đổi nhu cầu. ComfyUI cần server, workflow, weights đã cài; core requirements không đủ. [Provider guide — local generation](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/docs/PROVIDERS.md#local-video-generation-gpu-required).

### Ứng viên phụ bynanci/open-film

Main [`08e38b6a63`](https://github.com/bynanci/open-film/commit/08e38b6a63a0b0fbcfd3a073c8bfa5dcc8c08224), **08/11/2026 17:34:32 UTC**; release [v0.4.0](https://github.com/bynanci/open-film/releases/tag/v0.4.0), **20/10/2026 21:37 UTC**, gồm source và tài liệu kiểm thử, **không có bộ cài native đã phân phối**. License [Apache-2.0](https://github.com/bynanci/open-film/blob/main/LICENSE).

Editor local: ảnh/video/audio→catalog SQLite→Story Graph/Storyboard→rough cut→timeline→MP4 hoặc JSON/OTIO/FCPXML/EDL theo hỗ trợ. Stack TypeScript + Vue, Node service, Tauri shell; cần Node **≥24.14**, pnpm **11.11.0**, FFmpeg/ffprobe. Browser workspace không cần Rust; native shell thêm toolchain Tauri. Không cần cloud/key để dựng cơ bản. [README trực tiếp](https://github.com/bynanci/open-film/blob/08e38b6a63a0b0fbcfd3a073c8bfa5dcc8c08224/README.md), [desktop guide](https://github.com/bynanci/open-film/blob/08e38b6a63a0b0fbcfd3a073c8bfa5dcc8c08224/apps/desktop/README.md).

ASR tùy chọn dùng faster-whisper, model cung cấp riêng; tài liệu mô tả CPU int8/CUDA float16 có fallback. Không bắt buộc GPU để dựng cơ bản; chưa thấy RAM tối thiểu/benchmark Windows được xác nhận. Không có bằng chứng nhận thẳng HyperFrames project; handoff NLE có thể phải bake/dựng lại effect. Kit đã có Studio nên lợi ích trước mắt nhỏ hơn chi phí chuyển format. [Transcription](https://github.com/bynanci/open-film/blob/08e38b6a63a0b0fbcfd3a073c8bfa5dcc8c08224/docs/transcription.md), [NLE compatibility](https://github.com/bynanci/open-film/blob/08e38b6a63a0b0fbcfd3a073c8bfa5dcc8c08224/docs/nle-compatibility.md).

## 3. Đối chiếu với kit

Đã đọc [README kit](../../README.md), [docs/07](../07-dung-canh-va-render.md), [docs/12](../12-video-demo-san-pham.md), [awesome-opus5-5.md](awesome-opus5-5.md), [AGENTS của video-studio](../../../video-studio/AGENTS.md). Ghi chú awesome dùng để hiểu hướng thiết kế; không dùng các khẳng định giá/model trong đó làm chứng cứ cho hai repo.

Kit đã có: Gemini TTS/lời làm đồng hồ, `speech_segments.py`, quay thật theo `shots.json`, chặn `never_click`/`needs_var`, HTML/GSAP, FFmpeg/mix âm, `to_studio.py`, sửa câu bằng `doi_loi.py`. Docs hiện có `flow_diagram`, `kinetic_rehook`, **`produce.py --qa`**, nên không đề xuất contact sheet như thể chưa có.

Sau handoff, **`index.html` trong Studio là bản chính**. OpenFilm dùng `frame(t)`/`film.html`; kit dùng GSAP `window.__timelines` và thuộc tính thời gian. Chuyển qua lại cần adapter, không chỉ đổi tên file. Không dựng lại từ kit ghi đè sửa tay.

Trong bảng: **none** = không thêm tiền API, vẫn tốn máy/hạn mức subscription; công sức là **ước lượng của người nghiên cứu**, chưa triển khai.

| Tính năng / nguồn | Hữu ích cho ta? | Gắn vào file / bước | Chi phí | Công sức |
| --- | --- | --- | --- | --- |
| Render cùng mốc theo thứ tự xáo trộn — OpenFilm `look` | **yes** | QA: `tools/render.py` hoặc `screendemo/qa.py`, kiểm GSAP/video seek | none; CPU/Chrome | 0,5–1 ngày |
| Giữ chỉnh sửa theo phần tử — OpenFilm `overrides` | **maybe** | Sau handoff: `studio.json`, `tools/to_studio.py`; cần ID ổn định/preview diff | none | 2–4 ngày nếu làm merge/adapter |
| Thay editor/renderer bằng OpenFilm | **no** | Phải đổi `index.html`, `to_studio.py`, `doi_loi.py`, `docs/12` | Chuyển format; render không cần API | Cao; chưa có PoC |
| Thư viện âm/thành phần OpenFilm | **maybe** | `audio-library/`, `meme-library/`, `screendemo/blocks.py`; chọn từng asset | none nếu license phù hợp | 0,5–1 ngày/lô nhỏ |
| Cloud sinh ảnh/video/giọng — cả hai | **no** hiện tại | Assets/voice, `docs/04–06` | **API $ / credit**; subscription không thay key | Không đưa vào kế hoạch hiện tại |
| Whisper local — OpenFilm/bynanci; phân tích media — OpenMontage | **maybe** | Media ngoài vào `assets/`; hỗ trợ `tools/tts_qa.py`, không thay mốc lời đã đo | none API; model/CPU, GPU tùy chọn | 1–2 ngày + thử tiếng Việt |
| Checkpoint/schema, kiểm đầu ra — OpenMontage | **yes** | `screendemo/produce.py`, `tools/make_video.py`; lưu stage/input/QA | none nếu phép kiểm local | 1–2 ngày cho lớp mỏng |
| Duyệt phương án/sample trước tạo tài sản — OpenMontage | **yes** | `BRIEF.md`, `clip.json`, bước lời/scene plan | none với media sẵn có | 0,5–1 ngày |
| B-roll thật và provenance — OpenMontage | **maybe** | Trước dựng: `assets/broll/`, manifest, `story.py` | Download/model/CPU; không key với nguồn phù hợp | 1–3 ngày PoC |
| CLIP tìm footage — OpenMontage | **maybe** | Chỉ khi kho media lớn, tìm tay chậm | none API; torch/weights/CPU hoặc GPU | 2–3 ngày |
| Piper offline — OpenMontage | **maybe** cho nháp | Provider tùy chọn `tools/tts_script.py`; thử giọng Việt/license | none API; binary/model | 1–2 ngày thử |
| Recorder OpenMontage thay quay hiện tại | **no** | Giữ `screendemo/shoot.py`, `profiles/.../profile.json` | none | Recorder chung không thay logic thao tác/mốc an toàn của kit |
| Local WAN/Hunyuan/ComfyUI — OpenMontage | **no** lúc này | Chỉ cân nhắc B-roll ngoài demo thật | **GPU**, weights, điện | Cao; chưa biết cấu hình/benchmark |
| Backlot board — OpenMontage | **maybe** ý tưởng; **no** cài thêm lúc này | `_team`/board hiện có nếu cần stage/assets | none API; thêm service nếu dùng nguyên | 2–3 ngày adapter; dễ trùng board |
| Remotion/NLE hoặc catalog mới — OpenMontage/bynanci | **no** để thay dây chuyền | Không đổi chuẩn project chỉ để thêm editor | Chuyển format; license dependency cần xét riêng | Cao so với lợi ích hiện tại |

## 4. Ba ý tưởng cụ thể nên ưu tiên

### 1. Kiểm tính tất định trong QA hiện có

Học OpenFilm, tự viết phép kiểm HyperFrames: chọn mốc đầu/cuối cảnh, focus/ink, chụp mỗi mốc ở **hai thứ tự khác nhau**, cùng viewport/font/asset. So ảnh để tìm timer, random, tween có trạng thái hoặc seek video chưa hoàn tất; ghi mốc sai và hai ảnh vào QA. Không chạy thẳng `openfilm look` lên HTML HyperFrames vì khác hợp đồng runtime.

Gắn vào `screendemo/qa.py` hoặc `tools/render.py`, tái dùng `produce.py --qa`. Nghiệm thu: cảnh cố ý phụ thuộc thứ tự tua bị phát hiện; GSAP tất định và video tua/giữ khung ổn định. Dùng ngưỡng khác biệt nhỏ cho nhiễu decoder, không hứa hash giống tuyệt đối trên mọi máy. **Ưu tiên cao; không thêm key/GPU.**

### 2. Duyệt phần thay đổi, giữ bản chính khi sửa clip

Học tinh thần `overrides` và checkpoint/review: trước sửa nhiều phần tử, lưu `.hf-versions/`, ghi ID/câu sẽ đổi, preview đúng đoạn rồi áp dụng chỉnh sửa được giao. Sửa lời phải kiểm cả phụ đề và độ dài; sửa hình kiểm snapshot. Giữ `index.html` hiện hành là nguồn chuẩn như AGENTS yêu cầu.

Gắn vào quy trình Studio quanh `tools/doi_loi.py`, `studio.json → rules`; chỉ sau đó mới cân nhắc patch theo ID. **Không tự merge mọi sửa tay sau `to_studio.py`**: thay ID, DOM hay giờ GSAP dễ xung đột. Nghiệm thu: đổi một câu không mất font/màu/vị trí phần khác; xung đột hiện rõ, không ghi đè âm thầm. **Ưu tiên vừa; bắt đầu quy trình nửa ngày, chưa xây adapter lớn.**

### 3. Thử B-roll được phép dùng, có ghi nguồn

Học montage nhưng PoC hẹp: một clip 30–45 giây, thêm 2–3 shot phụ từ footage chủ sở hữu hoặc nguồn có điều khoản phù hợp. Asset ghi URL/tác giả/license/yêu cầu credit/timecode. Duyệt thumbnail trước; chưa cần CLIP. Đưa shot vào `<video>` HyperFrames hoặc scene media hiện có.

Gắn vào `assets/broll/` + manifest, `story.py`/`scenes.json`, kiểm cuối ở `docs/08`. Dùng audio đã có/tự thu; không phát sinh API. Footage chỉ minh họa bối cảnh; bằng chứng màn hình/số thật vẫn quay bằng `shoot.py`. Nghiệm thu: đủ quyền, không số/nhãn gây hiểu nhầm, không key hay upload media riêng. **Ưu tiên sau QA, chỉ triển khai khi nội dung cần B-roll.**

Chưa đáng thay toàn bộ kit: OpenFilm thêm chuẩn project phải đồng bộ; OpenMontage đã dùng HyperFrames/FFmpeg ta có, đồng thời thêm nhiều provider/tool và AGPL. Chưa có bằng chứng làm tốt hơn các phần đặc thù: tiếng Việt, lời làm đồng hồ, focus/ink, thao tác web có chặn nút. Chỉ lấy phần giải quyết vấn đề đo được.

## 5. Chi phí, license, dữ liệu và Windows

### Chủ chỉ có subscription, không có API key

| Đường làm việc | Khả thi về nguyên tắc? | Giới hạn |
| --- | --- | --- |
| Agent subscription + media có sẵn + HTML/FFmpeg | **Có**, cả hai dự án chính | Cần runtime; tốn hạn mức agent. Chưa cài/chạy ở nghiên cứu này. |
| OpenFilm credit tạo media | **Không nằm trong subscription hiện có** | Không mang key riêng nhưng vẫn mua credit và gửi nội dung tới dịch vụ. |
| Adapter Google/OpenAI/fal/ElevenLabs… | **Không** khi chưa có credential/quyền/billing phù hợp | Không suy ra quyền API từ việc trả phí giao diện chat/video. |
| Piper/Whisper/video model local | **Sau khi thiết lập riêng** | Cần model/runtime; giọng Việt, license, RAM/VRAM/tốc độ chưa thử. |
| Pexels/Pixabay/Unsplash qua adapter | **Không tính là zero key** | Free key vẫn là key; chọn media local/nguồn không cần key để thay. |
| Gemini TTS của kit | **Không phải offline** | README kit nêu Google Cloud credential. Chưa xác nhận key sẵn có; dưới ràng buộc hiện tại chỉ tái dùng file tiếng/tự thu, không hứa sinh TTS mới bằng subscription. |

**License:** MIT của OpenFilm cho phép tái sử dụng có giữ notice; asset/font/model/dependencies có điều khoản riêng. Hướng dẫn media mô tả thư viện OpenFilm là CC0, nhưng lấy tài sản vẫn cần kiểm file/metadata và [third-party notices](https://github.com/openfilm/openfilm/blob/a85a80a9742981f0f77f61df88a2780984f8f3fb/packages/openfilm/THIRD_PARTY_NOTICES.md). Logo/video ví dụ bất kỳ không tự thành tài sản quảng cáo được phép dùng vì code MIT.

OpenMontage là AGPL-3.0; [THIRD-PARTY.md kit](../../THIRD-PARTY.md) đã ghi chủ cho phép học kiến trúc/dùng nội bộ tại commit cũ `08e2151`; nghiên cứu không mở thêm bước xin phép để đọc. Nếu đưa code/skill/schema AGPL vào bản phân phối hoặc cung cấp phiên bản sửa đổi qua mạng, phải xét nghĩa vụ tương ứng, không đổi nhãn thành Apache-2.0. Tự viết ý tưởng chung là hướng nhẹ hơn. Xuất MP4 không tự khiến mọi nội dung video thuộc AGPL; quyền media xét riêng. Căn cứ [LICENSE, mục 2 và 13](https://github.com/OpenMontageInc/OpenMontage/blob/356b5fa92474998c9f9a0782fd5547d05837d284/LICENSE).

**Cloud:** render/preview local không có nghĩa mọi tool local. ASR cloud, sinh image/video, search có thể gửi audio/ảnh/video tham chiếu hoặc truy vấn ra ngoài. OpenFilm Google adapter có Files API upload và cleanup; đó vẫn là upload. Agent subscription cũng xử lý prompt/ngữ cảnh qua dịch vụ agent. Không có key hoặc key lưu trên máy không đồng nghĩa không gửi dữ liệu.

Với dữ liệu riêng, dùng assets local và provider chọn rõ; không tự bật phân tích cloud. Giữ [AGENTS](../../../video-studio/AGENTS.md): chỉ chạy `hyperframes publish/cloud` khi chủ yêu cầu. Nghiên cứu chỉ GET tài liệu/source công khai, không gửi media.

**Windows:** OpenFilm chính có installer x64/CLI; OpenMontage chính có PowerShell/recorder Windows nhưng chưa có release công khai; bynanci chưa có installer phân phối. Trước triển khai cần thử đường dẫn Unicode, FFmpeg/ffprobe, font Việt, browser, antivirus/signing và playback thật. Đây là các mục cần thử, không phải lỗi đã quan sát. Không có benchmark máy này để hứa tốc độ/RAM.

## 6. Phương pháp và kiểm tra báo cáo

Nguồn sơ cấp: GitHub repo/README, package manifests, adapters, YAML, LICENSE, API. Web search tìm ứng viên; khi cache web khác raw/main, ưu tiên raw/API vừa đọc. Ví dụ bynanci: cache còn mô tả bản cũ; README trực tiếp hiện phân biệt source release với main và nêu rõ chưa có installer.

Với ba repo phân tích sâu, đã đọc `/repos/{owner}/{repo}`, `/commits?per_page=1`, `/releases?per_page=3`, `/git/trees/main?recursive=1`. Tìm thêm `/search/repositories` với biến thể tên rồi đọc raw từng file. Source chính được pin commit trong các link để kiểm lại.

Đã thử `Invoke-RestMethod` và `curl.exe` theo brief. TLS của hai client Windows thất bại; không vô hiệu xác minh TLS hoặc kết luận GitHub mất mạng. Python stdlib `urllib.request` lấy JSON/raw qua HTTPS thành công. Output lỗi thực tế và các trường JSON trích lược:

```text
curl: (35) schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS (0x8009030e) - No credentials are available in the security package
Invoke-RestMethod : The underlying connection was closed: An unexpected error occurred on a receive.

openfilm/openfilm: stars=5375; commit=a85a80a9742981f0f77f61df88a2780984f8f3fb
release=v0.3.1; published_at=2026-11-08T21:21:21Z
OpenMontageInc/OpenMontage: stars=78724; commit=356b5fa92474998c9f9a0782fd5547d05837d284
releases=[]
bynanci/open-film: stars=2; commit=08e38b6a63a0b0fbcfd3a073c8bfa5dcc8c08224
release=v0.4.0; published_at=2026-10-20T21:37:00Z
```

Metadata trên là trích lược JSON, không phải output thử chạy app. Brief không nêu test/lint riêng cho tài liệu; không chạy render/TTS/test upstream vì cần môi trường ngoài phạm vi. Kiểm phù hợp ở đây: UTF-8, link nội bộ, khoảng trắng và `git diff --check`. Output thực tế:

```text
PASS UTF-8, code fences, trailing whitespace, final newline
PASS local Markdown links: 7 references, 6 unique targets
git diff --check: exit 0; output=''
git -c core.autocrlf=false diff --no-index --check NUL report: exit 1; output=''
?? openfilm-openmontage.md
```

File đang untracked nên `git diff --check` thông thường không đủ để kiểm nội dung mới. Đã kiểm thêm trực tiếp với `--no-index` và bằng Python; exit 1 của no-index biểu thị file khác file rỗng, không có cảnh báo whitespace. Tắt chuyển đổi CRLF riêng cho lệnh kiểm để tránh cảnh báo định dạng xuống dòng của Git trên Windows. Chỉ sửa báo cáo này; không commit/push. Lệnh `say.py R03 --done` ở bước kết thúc chỉ cập nhật trạng thái công việc theo brief.
