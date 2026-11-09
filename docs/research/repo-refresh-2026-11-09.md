# Video kit repository refresh — 2026-11-09

Research only. KITREPO writes this file alone in the kit. Recommendations below are proposed work, not installed upgrades. No Google models, app installs, commits or pushes were used.

## Scope, evidence and key findings

All 12 repositories in `THIRD-PARTY.md` section 2 and `scripts/clone_repos.sh` were attempted, plus OpenFilm and 19 additional candidates: **32 repositories; 30 fetched and checked out; two unavailable public repositories**. The initial snapshot was approximately 09:17–09:29 UTC; all sources were re-fetched and checked against advertised remote HEADs at 09:50:18–09:50:28 UTC on 2026-11-09 after shell access recovered. Latest means the advertised default-branch head fetched in that window, not a promise about the latest package release. HyperFrames HEAD has CLI package **0.9.26**. OpenFilm HEAD exactly matches the local reference.

Reference clones are under `D:/agent-cache/KITREPO/repos/`. Per-repository JSON files in `D:/agent-cache/KITREPO/` retain full head SHAs, head dates, original baseline SHAs, complete commit-subject logs, diff statistics and changed filenames. `verified-heads.txt` contains all 32 results. Original comparisons used `git log OLD..HEAD`, `git diff --stat OLD HEAD` and changed source files. All 11 accessible original baselines, including OpenFilm, resolve locally and are ancestors of their fetched heads. Counts include merges and merged work with older author dates, rather than only commits dated after September. New candidates have no kit baseline: **NEW means newly evaluated for the kit, not necessarily recently created**. They were shallow-cloned; no historical delta is invented for them.

The default Git Schannel backend initially failed with `SEC_E_NO_CREDENTIALS`. Retrying with `git -c http.sslBackend=openssl -c core.longpaths=true clone ...` worked without disabling TLS verification. For the two failed clones, independent requests to `https://api.github.com/repos/{owner}/{repo}` returned 404. That proves public unavailability, not whether the repository was deleted or made private.

Windows names are case-insensitive: wilwaldon's `Claude-Code-Video-Toolkit` and digitalsamba's `claude-code-video-toolkit` collide when cached by basename. The digitalsamba clone is explicitly `repos/digitalsamba-video-toolkit/`. These are different repositories, not a rename.

The most urgent finding is **audio refresh compatibility**: video-shotcraft commit `1266a3e` removes the old `assets/audio/sfx/` collection and switches to per-project Freesound sourcing. The kit's `tools/fetch_sources.py` and `tools/build_library.py` still rebuild from old Mixkit attribution rows. Updating only that source pin can omit old SFX from the rebuilt catalog even if their files remain on disk. Preserve the legacy audio pin until the importer preserves existing entries and understands the new manifest. HyperFrames' old `skills/media-use/audio/assets/sfx/` directory still exists.

Reproduce the original comparisons in PowerShell:

```powershell
git -C D:/agent-cache/KITREPO/repos/hyperframes rev-parse HEAD
git -C D:/agent-cache/KITREPO/repos/hyperframes log --oneline 9a27b9f..HEAD
git -C D:/agent-cache/KITREPO/repos/video-shotcraft diff --name-status 5ddbf52 HEAD -- assets/audio
python D:/agent-cache/KITREPO/verify-heads.py
```

## What this means for the daily Studio flow

Kit-Video-Studio is the human UI for daily production: brief → research → script → script approval → record → voice → build → `to_studio` → Studio QA → owner review → render → publish package. These match the existing IDs/artifacts in `D:/Projects/kit-studio/docs/workflows/product-demo.json`, read during this refresh. Keep that workflow authoritative; the proposed kit tasks supply tools and evidence to its existing KWF/KNEW/KDAY owners.

Prioritize resumable, machine-readable outputs from local tools over another orchestration service. Reuse `tools/to_studio.py`, `tools/doi_loi.py`, `screendemo/shoot.py`, `voice.json`, `studio.json` and the existing libraries. Studio opens work immediately, humans review drafts, and subagents receive small file scopes. A rerun resumes the failed stage; a tool must never rebuild an approved `index.html` over human edits. Publish-package creation prepares files and credits; actual posting remains an explicit Studio action.

The HyperFrames source snapshot and its release are distinct. [`docs/changelog.mdx`](https://github.com/heygen-com/hyperframes/blob/c38ac5438c751094a720c55c68bd15fc6450ec37/docs/changelog.mdx) records 0.9.26; HEAD still declares 0.9.26 in `packages/cli/package.json`, but the latest motion-blur commit is **after** that release. Installing `hyperframes@0.9.26` does not establish that it contains `c38ac5438`. Pilot the published release first; assess that fix using an exact-source build or a later verified release. Do not install an unqualified `latest` in the production path.

On resume, cached repos initially failed Git's ownership check because the previous run used `CodexSandboxOnline` and the resumed shell uses the owner account. Per-command `-c safe.directory=<specific cached repo>` fixed this without changing global Git configuration. All 30 accessible repos then fetched successfully. No new error 1909 occurred in the resumed verification.

## Recorded repositories and OpenFilm

Y means useful for scoped implementation or continued reference. N means no new implementation work recommended. File paths below are relative to the corresponding cached clone; comparison links are immutable evidence for the original repositories. The full SHA ledger appears in the proposed section 2 table below.

| Repo | Old commit → fetched commit | What changed | Use for kit Y/N | How / concrete source files |
| --- | --- | --- | --- | --- |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes/compare/9a27b9f...c38ac5438c751094a720c55c68bd15fc6450ec37) | `9a27b9f → c38ac5438c75` | **1,967 commits.** Seven knowledge skills replace workflow skills (`688229314`); transcription/SRT/VTT/API, audio analysis/master bus, filmed-screen, render ranges/ProRes/resolution options. Recent virtual film-time timers (`59c2065d6`, `fed14b016`), seeded randomness (`eb16510a1`), GSAP seek fixes, cached/budgeted check reports, Windows fixes. Latest `c38ac5438` propagates page motion blur into distributed/range renders. | Y | `skills/hyperframes/SKILL.md`, `skills/hyperframes/references/captions.md`, `packages/cli/src/commands/{check,transcribe,render,audio}.ts`, `packages/producer/src/services/fileServer.ts`, `packages/producer/src/services/distributed/{plan,renderChunk}.ts`. Refresh kit skill contracts; pilot a pinned optional renderer before changing `tools/render.py`. |
| [Vincentwei1021/video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft/compare/5ddbf52...1266a3ec4831289c4d893d42dd5102723658039a) | `5ddbf52 → 1266a3ec4831` | **10 commits.** Windows workbench/export fixes (`55359eb`, `c81ec74`), distinct real frames for short clips (`bd02e26`), optional Upload-Post publishing, per-project Freesound sourcing replacing old SFX (`1266a3e`). | Y | `shot-polish/{sheet,test_sheet}.py`, `assets/scripts/{sfx-source,test_sfx_source}.py`, `references/sfx-sourcing.md`, `assets/audio/ATTRIBUTION.md`. Port short-clip QA and additive manifest ingestion. Do not blindly bump the audio-rebuild pin. |
| [899ms/uisfx](https://github.com/899ms/uisfx) | `9950fe6 → unavailable (404)` | No public head or delta can be established. Anonymous clone fails; API returns 404. | N refresh | Keep the kit-local 936-file snapshot, `audio-library/sfx/uisfx/` and existing metadata. `tools/build_library.py` already falls back to the kit copy. Never report a failed clone as success. |
| [arhamhi/hooksmith](https://github.com/arhamhi/hooksmith/commit/1a1c13c313fe7c314233fccb2aa6bd2e8564373e) | `1a1c13c → 1a1c13c313fe` | **0 commits.** Head equals the recorded pin. | Y existing | `skills/hooksmith/references/{anti-patterns,command-audit,hook-families}.md`: add a compact original hook-review guide. These are existing capabilities, not new upstream features. |
| [sharon-laicc/viral-video-decomposer](https://github.com/sharon-laicc/viral-video-decomposer/commit/34093598d48bda6492f687c5eae3472b782d0637) | `3409359 → 34093598d48b` | **0 commits.** | Y existing | `skill/references/output-contract.md`, `skill/references/validate_report.py`: structured video-reference observations and validation; no new runtime dependency. |
| [shixinzhang/tiktok-viral-hooks](https://github.com/shixinzhang/tiktok-viral-hooks/compare/eaae981...c730c55d6d4a1fe01f91964a4651311910004042) | `eaae981 → c730c55d6d4a` | **35 commits.** Daily analyses through November 7, new October/November breakdowns, README and `_data/all-videos.json`. No renderer/caption/TTS implementation change. | N runtime | Optional editorial reference from `_data/all-videos.json`, `breakdowns/en/2026-10/`, `breakdowns/en/2026-11/`. Preserve the kit's existing no-copy policy; do not import the corpus into hooks. |
| [jakeolschewski/short-form-video-scripts](https://github.com/jakeolschewski/short-form-video-scripts) | `f4f83d2 → unavailable (404)` | API 404 and anonymous clone unavailable; no verified latest commit. | N | Retain the old pin as historical provenance. No current file pointer or changelog can honestly be supplied. Exclude from mandatory successful clone counts. |
| [hypit-ai/hypit](https://github.com/hypit-ai/hypit/compare/7f730ab...2d31e88765e297f0795348b460c77a6067f12261) | `7f730ab → 2d31e88765e2` | **77 commits; 0.2.17 → 0.3.2.** Breaking composition/temporal author model; independently owned packages, authored caption cues and exact-frame preflight; embeddable HTML, local video-frame reuse, Bach/HypiHub provider. | Y isolated | `docs/guide/packages.md`, `packages/caption/src/temporalize.ts`, `packages/caption-fine/src/schedule.ts`, `skills/hypit/references/playbooks/craft/{screen-demonstrations,sound-mix}.md`. Keep optional; evaluate one 0.3 fixture before migrating a 0.2 project. |
| [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage/compare/08e2151...fecb9a1e3cc23ef84de30b272059457a427f16f8) | `08e2151 → fecb9a1e3cc2` | **275 commits.** Caption layout/tail padding, forwarded captionProps and complete cache identity; RTL/Thai fixes; isolated render workspaces; delayed stereo audio and duck timing; local fonts; MiniCut music-fit/SFX/TTS/upscale; backlot series. | Y selective | `tools/audio/audio_mixer.py`, `lib/asset_cache.py`, `tools/video/{hyperframes_compose,remotion_caption_burn}.py`, `remotion-composer/src/components/CaptionOverlay.tsx`, `lib/verify_scene_pacing.py`. Port demonstrated reliability fixes; MiniCut remains opt-in. |
| [zhuyansen/awesome-claude-video-skills](https://github.com/zhuyansen/awesome-claude-video-skills/compare/b116824...6dbd11c4609a8bf2c536fd924d8bdb143d90f14d) | `b116824 → 6dbd11c4609a` | **41 commits.** Daily catalog growth, renamed/dead repo cleanup, end-to-end comparison guidance, new motion/screen-demo/video-agent entries. | Y discovery | `README.md`, `README.zh-CN.md`: discover candidates, then inspect their actual code. A catalog entry does not prove Windows compatibility. |
| [wilwaldon/Claude-Code-Video-Toolkit](https://github.com/wilwaldon/Claude-Code-Video-Toolkit/commit/a6e9e5225d85585472666598297f47d9584f9a97) | `a6e9e52 → a6e9e5225d85` | **0 commits.** Still February 2026 index. | N refresh | `README.md` remains an index. Prefer maintained source repos below; this is not the digitalsamba workspace. |
| [kapishdima/soundcn](https://github.com/kapishdima/soundcn/commit/7cbfbb3f56e8548b81fb26410bdcea657447d087) | `7cbfbb3 → 7cbfbb3f56e8` | **0 commits.** | N | `README.md`; no new implementation benefit. Preserve the existing kit exclusion of its audio. |
| [openfilm/openfilm](https://github.com/openfilm/openfilm/commit/a85a80a9742981f0f77f61df88a2780984f8f3fb) | `a85a80a97429 → a85a80a97429` | **0 commits** since `D:/Projects/craft-anything/refs/openfilm` HEAD. Useful features below already existed. | Y existing | `packages/openfilm/src/{captions.mjs,captions.test.mjs}`, `packages/openfilm/studio/server/caption-tracks.mjs`: WebVTT round-trip, timed text and editable caption tracks. Adapt sidecar support without replacing `voice.json` or manually corrected captions. Studio ports remain with studio owners. |

## Additional repositories evaluated

Searches covered agent video skills, HyperFrames components/editors, local captioning, Vietnamese TTS, agent screen recording and independent download backends. Selection came from current upstream pages and refreshed catalogs, followed by actual clone/source inspection. Repository age is distinguished from novelty to this kit. File pointers are relative to each clone; exact pins appear below.

| Repo | Old → fetched commit | What is new to the kit / finding | Use for kit Y/N | How / concrete source files |
| --- | --- | --- | --- | --- |
| [louiseliu/hyperFrames-video-shotcraft](https://github.com/louiseliu/hyperFrames-video-shotcraft/commit/1df77f1ab080323558f70a5fb880fad0f88f87fc) | `NEW → 1df77f1ab080` | HyperFrames-native shot cards, HTML/GSAP compositions, editable template, camera moves/themes, JianYing export. HEAD dates to September 24, not a November release. | Y | `template/index.html`, `references/shots/camera/cursor-flyover.md`, `references/shots/data/before-after-slider-scrub.md`, `references/jianying-export.md`. Adopt one usable HTML recipe instead of translating React demos. |
| [kurbaitaev/ghost-editor](https://github.com/kurbaitaev/ghost-editor/commit/ce172726c36293722b08eb57b5b307d4f06389e8) | `NEW → ce172726c362` | Talking-head reels, take selection, meme/SFX ranking, face-aware overlays, seek-order/render-vs-snapshot/flicker QA. README targets Mac; Windows pipeline unverified. | Y selective | `scripts/{meme_find,framecheck}.py`, `references/{sound-and-memes,take-selection}.md`. Strongest new meme/QA reference. Adapt English `[a-z]` tokenization to Vietnamese Unicode; do not import its shell pipeline wholesale. |
| [remotion-dev/skills](https://github.com/remotion-dev/skills/commit/1af7e69a2a613437d46095924057970a6a7df40d) | `NEW → 1af7e69a2a61` | Official caption/layout agent knowledge; package snapshot 4.0.542. `package.json` identifies canonical source in the remotion monorepo. | Y reference | `skills/remotion-best-practices/remotion-captions/{import-srt-captions,display-captions,transcribe-captions}.md`. Borrow data/layout concepts; retain HTML authoring. |
| [m-bain/whisperX](https://github.com/m-bain/whisperX/commit/5d3678b8535698a2826a5db9eb3e4105aef85dd9) | `NEW → 5d3678b85356` | Local word alignment and optional diarization; explicit Vietnamese alignment model, optional torchaudio fallback and accelerated alignment. Head identifies 3.8.7rc1, not a validated kit dependency. | Y optional | `whisperx/{alignment,asr,transcribe}.py`; Vietnamese model `nguyenvulebinh/wav2vec2-base-vi-vlsp2020` is in `alignment.py`. Separate Torch/model environment, benchmark actual Vietnamese. |
| [jianfch/stable-ts](https://github.com/jianfch/stable-ts/commit/e312072cc024ae9fceb25b057d7d18524873a02b) | `NEW → e312072cc024` | Timestamp refinement/grouping/silence suppression, but README explicitly says development is indefinitely paused. | N default | `README.md`: experimental comparison only if WhisperX cannot meet quality; do not describe it as actively maintained. |
| [pnnbao97/VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS/commit/6cdb62e03e6a9fd6ebff70e77aff8570c50949c3) | `NEW → 6cdb62e03e6a` | Local Vietnamese v3 Turbo, 48kHz, presets, batched conversation and streaming. Open v3 Turbo differs from proprietary hosted v4. | Y | `src/vieneu/{factory,v3turbo}.py`, `examples/main_v3turbo.py`, `docs/streaming.md`. Optional narration backend emitting the existing timing schema from measured WAV durations. Upstream speed claims were not benchmarked here. |
| [CapSoftware/Cap](https://github.com/CapSoftware/Cap/commit/a42f8f44f61c02b50302d755c41a7b739947a3e7) | `NEW → a42f8f44f61c` | JSON agent CLI, local MCP, explicit recording lifecycle, source discovery, detached capture and export; cap-demo skill. | Y optional | `apps/cli/README.md`, `apps/cli/src/{record,mcp}.rs`, `apps/cli/skill/cap-demo/SKILL.md`. Native desktop capture adapter; verify installed Windows executable rather than assuming source availability proves packaged support. |
| [getopenscreen/openscreen](https://github.com/getopenscreen/openscreen/commit/565ac5dc31c6bc56694eecb0502bad0cfcef4690) | `NEW → 565ac5dc31c6` | Cross-platform native capture, cursor/zoom editing, MCP/CLI, caption/export runners, demo skill. Package source is 2.2.2. | Y pilot | `electron/mcp/{openscreen-mcp-server,project-tools}.ts`, `src/cli/CliCaptionsRunner.tsx`, `plugin/skills/openscreen-demo/SKILL.md`. Export scripted pointer tracks when Playwright does not move the OS cursor; check released binary exposes MCP. |
| [imputnet/cobalt](https://github.com/imputnet/cobalt/commit/a636575b09de1fc55d9b8cd98cac88f5f2f16b42) | `NEW → a636575b09de` | Independent media-download API/extractors, not a yt-dlp wrapper. Default branch head dates to April despite later issue activity. | N default; Y spike | `api/src/core/api.js`, `api/src/processing/services/{tiktok,youtube}.js`. Self-hosted fallback only for demonstrated failures; public API and current YouTube compatibility not established. |
| [streamlink/streamlink](https://github.com/streamlink/streamlink/commit/ae15e79ea7e650bf2e715190d14b941f157e7112) | `NEW → ae15e79ea7e6` | Independent live extraction, HLS/DASH; changelog includes 8.6.2 on October 7. Complements VOD download tools. | Y live | `CHANGELOG.md`, `src/streamlink_cli/main.py`, `src/streamlink/stream/hls/hls.py`. Explicit live mode with duration cap/cancellation; not a general yt-dlp metadata/subtitle replacement. |
| [iankiku/anytranscript](https://github.com/iankiku/anytranscript/commit/934d30fa52c7efadeed04a66db0858680c3f9876) | `NEW → 934d30fa52c7` | 1.0.2 caption-first URL transcription, rolling VTT deduplication, local Whisper fallback and clean stdout/stderr separation. Uses yt-dlp underneath. | Y patterns | `src/{vtt,transcribe,ytdlp}.ts`. Add caption-first processing before ASR. It is **not an independent yt-dlp replacement**, and a second Node runtime need not be mandatory. |
| [clonn/awesome-agent-video-skills](https://github.com/clonn/awesome-agent-video-skills/commit/5747288335fffc2f599cde0d41f0dd54d700f51d) | `NEW → 5747288335ff` | Categorized catalog, individual skill cards and machine-readable source data. | Y discovery; N runtime | `README.md`, `sources/upstream/skills.json`. Secondary discovery, not another dependency or proof of compatibility. |
| [digitalsamba/claude-code-video-toolkit](https://github.com/digitalsamba/claude-code-video-toolkit/commit/f3d83c664554569c7e3411b614e5dda9eba350f9) | `NEW → f3d83c664554` | Active full workspace with brand/voice profiles, actual Playwright recording, synthetic UI demos and Remotion guidance. Different from wilwaldon's index. | Y selective | `.claude/skills/{playwright-recording,synthetic-ui-demo}/SKILL.md`, `brands/default/brand.json`, `docs/creating-brands.md`. Borrow profile separation and planning; use real capture for evidence of real product behavior. |
| [heygen-com/hyperframes-community-skills](https://github.com/heygen-com/hyperframes-community-skills/commit/ba7a0bb6d3567d124c51f6074625043bfe0b32eb) | `NEW → ba7a0bb6d356` | Eight independent community workflows: 3D captions, collage explainers, split-screen/duo and deterministic p5 art. September 24 HEAD; new to this audit, not newly released. | Y selective | `skills/camera-3d-captions/references/recipes.md`, `skills/vox-explainer/references/{render-safe-seams,seam-gate}.md`, `skills/duo/references/sourcing-real-ui.md`. Borrow caption/cut mechanics; review each skill separately. No need to install all eight. |
| [kmilo93sd/agent-video-editor](https://github.com/kmilo93sd/agent-video-editor/commit/8e32c0aff64c445ef1e2b87bc04408a34d68c973) | `NEW → 8e32c0aff64c` | v2.0 editing judgment, narrated-screen tutorial recipes, measurable preflight, 113 SFX + 15 music files and 26 graphics claimed CC0 with source inventories. Stronger asset provenance than another uncurated meme dump. | Y | `skills/editing-videos/{review-checklist.md,recipes/narrated-screen-tutorial.md}`, `skills/editing-videos/library/{catalog.json,LICENSES.md,verify.mjs}`, `skills/editing-videos/graphics/LICENSES.md`. Add measured review guidance and a separate additive asset importer. Quick verification matched all 128 audio records/files; decoding/loudness were not checked. |
| [kyutai-labs/pocket-tts](https://github.com/kyutai-labs/pocket-tts/commit/28770c06f7deb1b65617834e60a6add7a4ff5b6d) | `NEW → 28770c06f7de` | October small English CPU models (18.2M/6.9M/1.9M), Rust CLI and seven upstream languages. The registered language list does not include Vietnamese; community model count does not prove VI support. | N Vietnamese; Y English pilot | `README.md`, `pocket_tts/main.py`, `pocket_tts/models/tts_model.py`. Consider CPU English variants only after the Vietnamese path works. Preserve separate model/voice metadata; published speed claims were not measured here. |
| [latent-spaces/brag](https://github.com/latent-spaces/brag/commit/669ab9286aa28b6c3ee30e75f181ee74319d012a) | `NEW → 669ab9286aa2` | 0.5.0 launch-video skill: project inspection, product-flow plan, tone/brand/audio direction and delivery copy. Includes a slim workflow that does not use HyperFrames; avoid assuming every variant emits kit-compatible HTML. | Y reference | `skills/brag/references/{step-1-inspect,step-2-plan,step-3-compose,step-4-deliver}.md`, `skills/brag-slim/SKILL.md`. Reuse the one-page brief and real-product-flow checklist inside the current workflow; no second UI or automatic posting. Do not treat its bundled music as covered by the code license. |
| [lonthq/overtone-captions](https://github.com/lonthq/overtone-captions/commit/9fad13e25d59869ebed41f5979120f09b95abea0) | `NEW → 9fad13e25d59` | One word timeline with separate 16:9/9:16 caption cuts, explicit reading-speed/line/hold rules, SRT/VTT export, offline recut and optional local ASR. Language packs list en/nl/de/fr/es/it/pt, not vi. | Y layout reference | `packages/format/overtone.schema.json`, `packages/format/src/export/{vtt,srt}.ts`, `packages/cli/src/segment/{rules,splitter}.ts`, `packages/cli/src/lang/index.ts`. Adapt format-aware line cuts; use Unicode/neutral rules or add reviewed VI rules. Default transcription uses paid providers; use existing aligned words/offline recut instead. |
| [langchain-ai/design-agent](https://github.com/langchain-ai/design-agent/commit/a6e15774409094adaa22654255bdcd8165cfb4ef) | `NEW → a6e157744090` | Content Studio combines brand packs, briefs, storyboard/animatic/production gates, isolated frame packets, artifact contracts and review evidence. Its hosted Slack/MDA deployment differs from the owner's local Studio/CLI design. | Y patterns; N deployment | `skills/launch-film/orchestration.md`, `skills/general-video/scripts/{frame-packets,frame-packets.test}.mjs`, `skills/brand-design/references/artifact-contract.example.json`, `examples/brands/example-studio/brand.toml`. Reuse bounded handoffs and proof of stage completion; let existing Studio owners consume the kit artifact contract. Four offline packet tests passed; no agent/service was launched. |

## Adoption boundaries

1. **Source pins and asset pins are different.** Preserve old catalog IDs, paths and metadata. Ingest new per-project SFX manifests additively. This audit deliberately did not run `tools/fetch_sources.py`, which would mutate the owner's library.
2. **Preserve kit contracts.** HTML stays editable source; `voice.json` retains caption overrides; `tools/to_studio.py` remains the studio bridge. VTT sidecars must preserve cue settings, tags and manually corrected text, not regenerate over human edits.
3. **Local speech can avoid Google at runtime.** No speech models were invoked here. For Vietnamese, explicitly choose a multilingual Whisper model and `vi`; HyperFrames' whisper default `small.en` is unsuitable. Distinguish real word alignment from the current character-weighted estimates in `tools/captions.py`.
4. **Prove audio ownership.** The kit already mixes/ducks externally with FFmpeg. Start a HyperFrames adapter with picture-only rendering. Verify audible `<video>`, separate `<audio>`, explicit IDs, `data-has-audio` and master automation before enabling upstream mixing, so audio is never duplicated.
5. **Prove render parity before changing defaults.** Test cut boundaries, worker counts, forward/reverse seeks, holds, late fonts/images and looping sticker videos. A pinned optional CLI adapter is easier to maintain than copying another full runtime into `tools/render.py`. Useful references: HyperFrames `packages/producer/src/services/{fileServer,renderOrchestrator}.ts` and `packages/core/src/adapters/gsap.ts`; ghost-editor `scripts/framecheck.py`.
6. **Native capture is a separate option.** Cap/OpenScreen source does not establish released Windows binary behavior. Require explicit start/stop ownership and cancellation cleanup. Export pointer tracks for scripted Playwright actions; DOM actions alone do not move the OS cursor.
7. **Meme/hooks improvements can stay small.** Preserve Noto/current collections. Adapt relevance/trend/repetition scoring; do not replace the collection. Hooksmith has no upstream delta, but its existing audit references remain useful for original Vietnamese hooks.

## Ranked handoff tasks

Each of the 30 rows has one owner and bounded writable paths. Before Wave A, the lead freezes shared result/asset schemas from DAILY-CONTRACT and agrees SRC-FETCH/SRC-CATALOG/AUDIO-CC0 interfaces; owners then work independently. Each implementation owner may add focused tests only within a separately assigned matching test path, never a shared test file. New paths are proposals, not files created here. Wave A tasks can run in parallel without overlapping writable files; Wave B integrates completed modules. Shared root docs/config belong to the final integration owner. No subagents were started for this research.

| Rank / wave | Single owner | Files touched in kit | Bounded task and acceptance |
| --- | --- | --- | --- |
| 1 / A | SRC-FETCH | `tools/fetch_sources.py` | Separate research HEADs from asset pins. Retain legacy `5ddbf52` for SFX until importer migration; report resolved SHA and fail on fetch/checkout failure. Failure must not replace audio/catalog. Agree manifest interface with SRC-CATALOG before B. |
| 2 / A | SRC-CATALOG | `tools/build_library.py` | Add additive per-project Freesound manifest import from video-shotcraft format; retain old Mixkit IDs and uisfx fallback. Fixture refresh must retain old entries, add valid new entries and be idempotent. Consume AUDIO-CC0 staging manifests only after the shared manifest shape is agreed; that integration is Wave B. |
| 3 / A | DAILY-CONTRACT | new `docs/contracts/production-artifacts-v1.json`, new `docs/contracts/production-artifacts-v1.md` | Map the existing KWF product-demo stage IDs and required files to kit outputs; specify tool result status, artifact path/hash, attempt/owner, review evidence and input hashes for approval invalidation. Include one complete example manifest. KWF/KNEW/KDAY review the mapping; do not create another workflow schema or edit their files. |
| 4 / A | QA-SHEET | new `tools/contact_sheet.py` | Adapt `shot-polish/sheet.py` unique real-frame sampling. 1, 2, 8-frame sources requesting 8 must yield min(frame_count, 8) unique in-range frames with no blank tiles, including paths with spaces. |
| 5 / A | CAP-ALIGN | new `tools/caption_align.py` | Optional WhisperX adapter with explicit Vietnamese/model and separate environment command. Emit `{text,start,end}`. Real Vietnamese sample must have ordered in-duration times; missing engine gives an actionable error, never Google fallback. |
| 6 / A | CAP-VTT | new `tools/caption_vtt.py` | VTT/SRT import/export using OpenFilm concepts. Preserve cue IDs/settings, emphasis and Unicode. Vietnamese + adjacent-cue round-trip must preserve manual text. |
| 7 / A | CAP-LAYOUT | new `tools/caption_layout.py` | Aspect-specific caption segmentation from aligned or explicitly estimated words, using Overtone rules as reference. Verify 16:9/9:16 width, max two lines, pauses, no word loss/duplication, Vietnamese accents and manual overrides. Output data only; CAP-WIRE integrates it. |
| 8 / A | RENDER-HF | new `tools/render_hyperframes.py` | Optional pinned HyperFrames 0.9.26 CLI adapter: picture-only, JSON status, caller cache/config, timeout/cleanup. Render copied kit scene without source mutation or duplicated audio; existing renderer remains available. Treat post-release motion-blur fix `c38ac5438` as a separate exact-source/later-release parity experiment. |
| 9 / A | QA-FRAMES | new `tools/framecheck.py` | Adapt seek-order, render/snapshot and transient-flicker metrics. Held frames pass; injected one-frame blank and seek-dependent layer fail with numeric diagnostics; tolerate H.264 error. |
| 10 / A | AUDIO-PROBE | new `tools/audio_mix_qa.py` | Measured channel/delay, loudness and short-tail checks informed by OpenMontage. Validate both channels of delayed stereo, short cue fade bounds and measured loudness from real FFmpeg output. |
| 11 / A | TTS-VI | new `tools/tts_vieneu.py` | Optional local v3 Turbo preset-voice adapter. Write WAV per line and existing timing schema from probed duration. Test Vietnamese numbers/acronyms and unavailable-engine behavior; no hosted v4/Google fallback. |
| 12 / A | AUDIO-CC0 | new `tools/import_editor_assets.py` | Produce an additive staging manifest for the agent-video-editor audio/graphics subset with source URL, original ID, license evidence and checksum. Dry-run validates catalog/files and rejects missing evidence; no default download or library mutation. SRC-CATALOG consumes this manifest after interface agreement. |
| 13 / A | DEMO-CAP | new `screendemo/cap_capture.py` | Wrap Cap JSON start/status/stop, caller output and finally cleanup. Installed Windows binary pilot or explicit unsupported result; ffprobe-readable recording; no recorder process after failure/cancel. |
| 14 / A | DEMO-POINTER | new `screendemo/pointer_track.py` | Normalized timestamp/x/y/click export for native capture/OpenScreen. Known viewport/DPI fixture maps positions correctly; offsets refer to recording start. Existing shooter not changed yet. |
| 15 / A | MEME-RANK | new `tools/meme_rank.py` | Adapt relevance/trend/per-clip repetition ranking with Vietnamese Unicode and existing asset IDs. Verify accents retained, used meme penalized, stable shortlist and no network/download side effects. |
| 16 / A | SOURCE-CAPTIONS | new `tools/source_captions.py` | Caption-first acquisition plus rolling-VTT dedup from anytranscript patterns. Preserve provenance/times; overlapping rolling cues collapse once, intentional repeated dialogue stays repeated, missing captions explicitly requests ASR. |
| 17 / A | SOURCE-LIVE | new `tools/live_capture.py` | Optional Streamlink wrapper with duration budget, path and cancellation. Local HLS fixture stops at budget and ffprobe reads output. Do not advertise general VOD/yt-dlp replacement. |
| 18 / A | STYLE-DEMO | new `examples/filmed-screen-kit/index.html`, `examples/filmed-screen-kit/README.md` | Adapt one filmed-screen/cursor HTML recipe using replaceable assets and stable IDs. No remote assets, title-safe captions; compare snapshots and renders. Avoid another giant template collection. |
| 19 / A | HOOK-REVIEW | new `skills/marketing-video/references/hook-review.md` | Short first-three-second promise/proof/payoff and anti-pattern review guide using original Vietnamese examples. No hook corpus import. |
| 20 / A | EDIT-REVIEW | new `skills/marketing-video/references/editing-review.md` | Adapt a short original VI review checklist from agent-video-editor: hook proof, caption readability, real measured loudness, cut/head/tail checks, sparse memes and prepared credits. Distinguish automated evidence from human listen/watch approval. Match existing KIT job rules instead of importing generic thresholds as mandatory policy. |
| 21 / A | HYPIT-PILOT | new `integrations/hypit/refresh-0.3.md` | Isolated 0.3.2 exact-frame/caption experiment and migration steps. Record actual compatibility result; do not update existing 0.2 projects automatically. |
| 22 / A | STYLE-COLLAGE | new `examples/collage-seam-kit/index.html`, new `examples/collage-seam-kit/README.md` | One minimal locally sourced two-scene fixture from community vox-explainer seam concepts: opaque stage, deterministic master timeline, stable IDs and correct overlap. Snapshot both sides of the cut; no white flash or lost captions. Use existing tools, no provider or browser-history access. |
| 23 / B after QA-SHEET, QA-FRAMES | DEMO-QA | `screendemo/qa.py` | Optional contact-sheet/framecheck stages with structured errors and report paths. Existing QA works; tiny loop and injected blank produce useful output. |
| 24 / B after CAP-ALIGN, CAP-VTT, CAP-LAYOUT | CAP-WIRE | `tools/captions.py`, `tools/clip_transcribe.py` | Explicit local engine + aligned-word input, estimated fallback and manual caption overrides. Missing local engine never silently calls Google; tests cover corrected caption text surviving alignment. |
| 25 / B after AUDIO-PROBE | AUDIO-WIRE | `tools/mix_audio.py` | Apply demonstrated delay/channel/short-fade fixes; expose measured QA without silently changing established levels. Validate delayed stereo and short BGM using AUDIO-PROBE. |
| 26 / B after DEMO-CAP, DEMO-POINTER | DEMO-WIRE | `screendemo/shoot.py` | Export pointer tracks from scripted actions; optional native backend after Cap pilot. Existing shots stay deterministic; correct pointer timing and cleanup on failure. |
| 27 / B after MEME-RANK | MEME-WIRE | `tools/meme_search.py` | Optional ranked shortlist + used-ID input through the new module. Existing CLI and asset IDs remain compatible. |
| 28 / B after SRC-FETCH, SRC-CATALOG | PIN-SCRIPT | `scripts/clone_repos.sh` | Explicit cache path argument, owner-qualified names, full immutable pins, fetch existing clones, visible failed status and historical unavailable entries. Remove masked failures and unconditional success logging. Second run must be idempotent; summarize failures and return nonzero; never clone into kit `_repos/`. |
| 29 / B after HOOK-REVIEW, EDIT-REVIEW and implemented modules | SKILL-WIRE | `skills/marketing-video/SKILL.md`, `skills/product-demo-video/SKILL.md` | Document aligned vs estimated timing, HTML/track contract, pinned tools, real capture/QA loop and HOOK-REVIEW. Verify instructions on copied scene; do not force vendor workflows. Link the new editing-review reference and DAILY-CONTRACT artifact mapping. |
| 30 / B after PIN-SCRIPT, SKILL-WIRE; last | REF-DOCS | `THIRD-PARTY.md`, `README.md`, `docs/07-dung-canh-va-render.md` | Apply proposed table after PIN-SCRIPT; document optional modules and verified fixtures. Keep asset/research pins separate. Advertise only implemented commands. |

Defer Cobalt deployment, wholesale Remotion migration, automatic posting and full Hypit migration until current source/caption/render/audio gaps are fixed. Kit-studio consumption stays with existing owners: KWF maps tool evidence/checks to its workflow, KNEW uses resumable per-stage artifacts and approval gates, KDAY queues/retries jobs, and the backend owner invokes kit tools. They own all Studio UI, brief/approval/tweak/publish surfaces and file watching; these kit research tasks must not duplicate them. OpenFilm studio work stays with kit-studio owners. Each implementation owner uses its own cache and stops its own processes.

## Proposed replacement for THIRD-PARTY.md section 2

Proposal only: the current section says `_repos/`, and the script still uses old pins and masks failures. Apply the introductory text and table together with PIN-SCRIPT. The text must not claim the new cache interface exists before implementation.

> Các repo dưới đây là nguồn tham khảo; kit không cần clone để chạy. Mốc nghiên cứu cập nhật 09/11/2026. Script dùng thư mục cache chỉ định (khuyến nghị `D:/agent-cache/KITREPO/repos/`), fetch và checkout đúng SHA; repo không còn công khai phải báo rõ. Pin nghiên cứu không tự động thay pin tài sản âm thanh trong `tools/fetch_sources.py`: giữ snapshot cũ đến khi importer tương thích.

Retain the four existing columns. Entries are research snapshots, not claims that suggested integrations have shipped. The metadata column preserves existing distinctions; declined candidates remain in this report rather than the replacement table.

| Repo | Commit nghiên cứu 09/11/2026 | Giấy phép / metadata nguồn | Kit dùng gì / đề xuất |
| --- | --- | --- | --- |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | `c38ac5438c751094a720c55c68bd15fc6450ec37` | Apache-2.0 | HTML/GSAP; CLI 0.9.26 check/render/transcribe/audio; SFX Pixabay có metadata riêng. |
| [Vincentwei1021/video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft) | `1266a3ec4831289c4d893d42dd5102723658039a` | Apache-2.0 (code) | QA/Windows/Freesound manifests; giữ pin tài sản Mixkit `5ddbf52` đến khi importer cập nhật. |
| 899ms/uisfx — public 404 | `9950fe6` (historical) | MIT (code), CC0 (audio), theo snapshot lưu | 936 SFX trong kit; không có HEAD mới xác minh. |
| [arhamhi/hooksmith](https://github.com/arhamhi/hooksmith) | `1a1c13c313fe7c314233fccb2aa6bd2e8564373e` | MIT | Hook audit/anti-patterns, HEAD không đổi. |
| [sharon-laicc/viral-video-decomposer](https://github.com/sharon-laicc/viral-video-decomposer) | `34093598d48bda6492f687c5eae3472b782d0637` | MIT | Hợp đồng báo cáo phân tích; HEAD không đổi. |
| [shixinzhang/tiktok-viral-hooks](https://github.com/shixinzhang/tiktok-viral-hooks) | `c730c55d6d4a1fe01f91964a4651311910004042` | CC BY-NC-SA 4.0; giữ chính sách hiện có | Tham khảo biên tập; không chép corpus vào kit. |
| jakeolschewski/short-form-video-scripts — public 404 | `f4f83d2` (historical) | Không ghi ở mốc cũ | Không có bản cập nhật công khai xác minh. |
| [hypit-ai/hypit](https://github.com/hypit-ai/hypit) | `2d31e88765e297f0795348b460c77a6067f12261` | Modified Apache-2.0, xem LICENSE | 0.3.2 exact-frame/caption/HTML; optional, cần migration từ 0.2. |
| [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) | `fecb9a1e3cc23ef84de30b272059457a427f16f8` | AGPL-3.0 | Port có chọn lọc: audio delay/duck, captions, cache identity, isolated workspaces. |
| [zhuyansen/awesome-claude-video-skills](https://github.com/zhuyansen/awesome-claude-video-skills) | `6dbd11c4609a8bf2c536fd924d8bdb143d90f14d` | CC0 | Danh mục tìm nguồn đã cập nhật. |
| [wilwaldon/Claude-Code-Video-Toolkit](https://github.com/wilwaldon/Claude-Code-Video-Toolkit) | `a6e9e5225d85585472666598297f47d9584f9a97` | Không ghi ở mốc đã kiểm | Danh mục không đổi; khác repo digitalsamba. |
| [kapishdima/soundcn](https://github.com/kapishdima/soundcn) | `7cbfbb3f56e8548b81fb26410bdcea657447d087` | MIT (code), giữ metadata audio hiện có | Không lấy thêm audio; giữ exclusion hiện có. |
| [openfilm/openfilm](https://github.com/openfilm/openfilm) | `a85a80a9742981f0f77f61df88a2780984f8f3fb` | MIT | WebVTT/editable caption track; bằng local reference, không có delta. |
| [louiseliu/hyperFrames-video-shotcraft](https://github.com/louiseliu/hyperFrames-video-shotcraft) | `1df77f1ab080323558f70a5fb880fad0f88f87fc` | Apache-2.0 (code) | HTML/GSAP recipes, camera/cursor, tham khảo export. |
| [kurbaitaev/ghost-editor](https://github.com/kurbaitaev/ghost-editor) | `ce172726c36293722b08eb57b5b307d4f06389e8` | MIT (code) | Meme ranking/take-selection/frame QA; thích nghi Windows/tiếng Việt. |
| [remotion-dev/skills](https://github.com/remotion-dev/skills) | `1af7e69a2a613437d46095924057970a6a7df40d` | Không có LICENSE root trong snapshot; package trỏ source monorepo | Caption/layout references; không đổi renderer chính. |
| [m-bain/whisperX](https://github.com/m-bain/whisperX) | `5d3678b8535698a2826a5db9eb3e4105aef85dd9` | BSD-2-Clause (code), model metadata riêng | Optional local ASR/word alignment, model VI trong source. |
| [pnnbao97/VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS) | `6cdb62e03e6a9fd6ebff70e77aff8570c50949c3` | Apache-2.0 (code), model metadata riêng | Optional giọng Việt v3 Turbo local; v4 là hosted. |
| [CapSoftware/Cap](https://github.com/CapSoftware/Cap) | `a42f8f44f61c02b50302d755c41a7b739947a3e7` | AGPL-3.0 chính; một số crate MIT theo LICENSE | CLI/MCP native capture pilot; kiểm Windows binary. |
| [getopenscreen/openscreen](https://github.com/getopenscreen/openscreen) | `565ac5dc31c6bc56694eecb0502bad0cfcef4690` | MIT | Native capture, pointer track, zoom pilot. |
| [streamlink/streamlink](https://github.com/streamlink/streamlink) | `ae15e79ea7e650bf2e715190d14b941f157e7112` | BSD-2-Clause | Optional livestream HLS/DASH, không thay toàn bộ yt-dlp. |
| [iankiku/anytranscript](https://github.com/iankiku/anytranscript) | `934d30fa52c7efadeed04a66db0858680c3f9876` | MIT | Caption-first/VTT dedup patterns; vẫn dùng yt-dlp. |
| [digitalsamba/claude-code-video-toolkit](https://github.com/digitalsamba/claude-code-video-toolkit) | `f3d83c664554569c7e3411b614e5dda9eba350f9` | MIT | Brand/voice/Playwright skill; cache tên riêng digitalsamba-video-toolkit. |
| [heygen-com/hyperframes-community-skills](https://github.com/heygen-com/hyperframes-community-skills) | `ba7a0bb6d3567d124c51f6074625043bfe0b32eb` | Apache-2.0 (code); asset metadata riêng | 3D captions/collage/seam QA; chọn từng workflow, không cài cả bộ. |
| [kmilo93sd/agent-video-editor](https://github.com/kmilo93sd/agent-video-editor) | `8e32c0aff64c445ef1e2b87bc04408a34d68c973` | MIT (code); CC0 audio/graphics theo manifests | Editing checklist + 128 audio/26 graphics để nhập có chọn lọc, giữ nguồn/ID. |
| [kyutai-labs/pocket-tts](https://github.com/kyutai-labs/pocket-tts) | `28770c06f7deb1b65617834e60a6add7a4ff5b6d` | MIT (code); model/voice metadata riêng | Tuỳ chọn English CPU; không quảng cáo hỗ trợ tiếng Việt. |
| [latent-spaces/brag](https://github.com/latent-spaces/brag) | `669ab9286aa28b6c3ee30e75f181ee74319d012a` | MIT (code); âm thanh kiểm riêng | Brief/hook/product-flow/tone checklist; không thay pipeline KIT. |
| [lonthq/overtone-captions](https://github.com/lonthq/overtone-captions) | `9fad13e25d59869ebed41f5979120f09b95abea0` | MIT | Word timeline → layout theo tỷ lệ khung; cần kiểm VI; không gọi provider mặc định. |
| [langchain-ai/design-agent](https://github.com/langchain-ai/design-agent) | `a6e15774409094adaa22654255bdcd8165cfb4ef` | Apache-2.0; vendored/font metadata riêng | Artifact contract, storyboard/animatic gates, frame handoffs; giữ Studio/local CLI hiện có. |

## Actual verification and limits

Resumed checks passed against the final cached sources: **27 upstream regression tests, zero failed/skipped**, plus a 128-entry asset metadata/disk audit. These cover short-clip real-frame sampling, SFX source manifests, WebVTT timing, plugin launch behavior and bounded frame packets. They do not establish kit integration, native Windows capture quality, local TTS/ASR quality or complete renderer parity. No weights, paid providers, publish calls or Studio UI code were used. UI typecheck and Studio application tests do not apply to this research-only change.

Exact output excerpts from the resumed run (full logs and command metadata: `D:/agent-cache/KITREPO/test-results.json` and `*-test.txt`):

```text
# cwd: D:/agent-cache/KITREPO/repos/video-shotcraft
> D:\Apps\Python313\python.exe -m unittest discover -s shot-polish -p test_sheet.py -v

----------------------------------------------------------------------
Ran 1 test in 5.168s

OK
exit=0

# cwd: D:/agent-cache/KITREPO/repos/video-shotcraft
> D:\Apps\Python313\python.exe -m unittest discover -s assets/scripts -p test_sfx_source.py -v

----------------------------------------------------------------------
Ran 12 tests in 3.806s

OK
exit=0

# cwd: D:/agent-cache/KITREPO/repos/openfilm
> node --test packages/openfilm/src/captions.test.mjs
1..1
# tests 1
# suites 0
# pass 1
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 112.8337
exit=0

# cwd: D:/agent-cache/KITREPO/repos/hyperframes
> node --test skills/hyperframes/scripts/plugin-cli.test.mjs
1..9
# tests 9
# suites 0
# pass 9
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 290.0305
exit=0

# cwd: D:/agent-cache/KITREPO/repos/agent-video-editor
> node skills/editing-videos/library/verify.mjs --quick
128 catalog entries, 128 files on disk, 51.4 MiB of audio
OK: catalog, disk and LICENSES.md agree; no empty, silent, clipped or corrupt file.
exit=0

# cwd: D:/agent-cache/KITREPO/repos/design-agent
> node --test skills/general-video/scripts/frame-packets.test.mjs
1..4
# tests 4
# suites 0
# pass 4
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 135.53
exit=0
```

The asset checker was run with `--quick`: despite its generic final message mentioning silence/clipping/corruption, that mode checks catalog fields, disk presence and license evidence only. Audio decoding, loudness and true-peak checks were skipped by design and are not claimed as passed.

Final read-only validation passed for every audited HEAD, original-pin ancestry, recorded-repo coverage, immutable SHA ledger, all 104 upstream source pointers and 30 unique-owner tasks with disjoint Wave A paths. All 1,391 tracked/untracked kit files in the resumed fingerprint remain byte-identical; the only new git-status entry is this document. Cached reference clones, JSON evidence, scripts and short test logs are retained as requested research outputs. No servers, browsers or detached jobs were started.

Cleanup limitation: automatic approval review rejected recursive deletion of the two verified task-specific temporary directories, `D:/agent-cache/KITREPO/tmp/` and `D:/agent-cache/KITREPO/pycache/`, with `blocked by policy`. A simpler command naming only those two literal paths was also rejected. These temporary directories remain; no cleanup success is claimed. No alternative deletion method was attempted after that rejection.

The previous run's Windows error 1909 is historical; shell access recovered for this run. The requested report can now be delivered directly to `D:/Projects/kit-studio/orchestration/reports/KITREPO-report.md` under the explicit brief authorization. Final delivery/cleanup/scope-validation results and the required `say.py --done` result are recorded there.
