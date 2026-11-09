# Filmed screen: chọn → xuất → xem lại

One editable 8-second, 1280 × 720, picture-only example. Open `index.html` in a browser; use `?t=4.8` to inspect the export click or the arrow keys to step by 0.1 seconds. Playback is paused by design. The illustrated interface is original sample content, not a recording or evidence of a working product.

The monitor has a mild perspective tilt, glass shading and scanlines. A camera and a cursor share one position table; clicks create a ring and update the illustrated interface. The cursor compensates for camera zoom. Captions sit outside the camera so they stay readable during moves.

## Replace the screen

Copy this folder into your own project before editing. In `CONFIG` near the bottom of `index.html`, set `screenAsset` to a relative local image, for example `assets/product-screen.png`. Supply a 1056 × 440 image, or crop it to that ratio first: the image fills those exact coordinates. Nothing is fetched remotely; the default uses an inline SVG and system fonts, with no extra assets or JavaScript packages.

Update `CONFIG.stops` to put the cursor on real controls in your image. Coordinates are pixels in the unscaled screenshot, measured from its upper-left corner. The camera clamps its pan to keep the viewport covered. `at` is absolute composition time; adjacent identical positions create holds. `CONFIG.clicks` contains absolute click times. Update `CONFIG.cues` for the narration; these captions are authored text, not generated word alignment. Change the heading and the accessible image description to match your product.

A replacement image is a single still throughout the shot. The sample SVG's selection/export changes do not modify that image; use the SVG fixture when demonstrating those illustrative state changes. This recipe does not capture a browser, click a real control or move the OS pointer.

`window.filmedScreen.asset.status` reports `fixture`, `loading`, `ready` or `unavailable`. A missing image or rejected remote/absolute/parent path returns `unavailable` with a reason, leaves the original illustration visible, and shows a status above the monitor. Wait for `ready` before accepting a render with your replacement image. No capture, speech or optional renderer engine is required or installed.

## Editing contract

| Stable ID / API | Purpose |
| --- | --- |
| `root`, `scene-screen` | `main` composition, duration 8 seconds, one scene |
| `monitor`, `viewport`, `camera` | Screen shell, clip boundary, camera transform |
| `screen-placeholder`, `screen-asset` | Original SVG fixture / replaceable image |
| `cursor`, `click-ring` | Pointer tip and deterministic click pulse |
| `selection-card`, `selection-status`, `export-status` | Sample UI proof at 2.0 and 4.8 seconds |
| `title`, `caption`, `caption-text`, `asset-status` | Fixed text overlays and asset result |
| `window.__timelines.main.seek(t)` | Absolute-time sampling for the existing kit renderer |
| `window.filmedScreen` | Same sampler, editable configuration, asset status |

The small timeline adapter implements the kit's `seek` contract without GSAP. It is not a full GSAP or HyperFrames runtime. Every sampled visual state comes from absolute time, with no timers, autoplay, randomness or accumulated animation state. Keep the IDs when changing artwork. The duration, stop table and cue endpoints must be updated together if you change the length.

The 16:9 title-safe rectangle is x=64…1216, y=36…684 (5% inset). The caption box is x=128…1152, y=645…684 and the supplied Vietnamese captions fit on one line. Keep edited captions within two lines and recheck their actual rendered bounds; long text can exceed the safe area. Portrait output needs a new layout, not just changed metadata. Audio remains with the kit's external mix path.

## Snapshots and a real render

Run from the repository root in PowerShell. Work in a cache copy because `--snap` writes PNGs into the project directory:

```powershell
$python = 'D:/Projects/ai-marketing-video-kit/.venv/Scripts/python.exe'
$scene = 'D:/agent-cache/K-STYLE-DEMO/manual-preview'
New-Item -ItemType Directory -Force $scene | Out-Null
Copy-Item examples/filmed-screen-kit/index.html $scene
# If using a replacement, also copy its assets folder into $scene.
$env:TEMP = $scene
$env:TMP = $scene
$env:PYTHONDONTWRITEBYTECODE = '1'
& $python tools/render.py $scene --snap 0,1.5,2,2.2,2.4,3.4,4.8,5,5.2,6.2,6.4,7,7.9 --no-audio
& $python tools/render.py $scene --fps 30 --crf 18 --no-audio --out filmed-screen.mp4
ffprobe -v error -count_frames -show_entries stream=codec_name,width,height,r_frame_rate,nb_read_frames -of json "$scene/filmed-screen.mp4"
```

Use the existing kit Playwright/Chrome and FFmpeg setup. Inspect the selection click at 2.0 seconds, export at 4.8, caption boundaries at 3.4 and 6.4, and the final hold at 7.9. Compare decoded MP4 frames with PNGs at the same frame index (`time × 30`); H.264 is lossy, so PNG hashes are not a video-parity metric. Check both forward and reverse/random seeks. Chrome can also introduce small rasterization differences between PNG seeks through perspective transforms; measure differences instead of claiming byte identity.

Acceptance evidence for this task is retained under `D:/agent-cache/K-STYLE-DEMO/evidence/`; the report at `D:/Projects/kit-studio/orchestration/reports/K-STYLE-DEMO-report.md` contains actual commands and numeric results. Recheck after replacing assets or changing captions, fonts or timing.

## Recipe references

Concepts adapted into original HTML/CSS/JavaScript from the local research snapshots:

- [cursor-flyover, hyperFrames-video-shotcraft, 1df77f1](https://github.com/louiseliu/hyperFrames-video-shotcraft/blob/1df77f1ab080323558f70a5fb880fad0f88f87fc/references/shots/camera/cursor-flyover.md): a shared camera/cursor table, easing, holds, inverse-scale cursor and click rings.
- [filmed-screen, HyperFrames, c38ac5438](https://github.com/heygen-com/hyperframes/blob/c38ac5438c751094a720c55c68bd15fc6450ec37/registry/components/filmed-screen/README.md): framing the screen as a filmed subject. This example uses ordinary DOM/CSS; it does not include that component's WebGL/HTML-in-Canvas lens or its depth-of-field effects.

No upstream code, assets, template collection or runtime was vendored.
