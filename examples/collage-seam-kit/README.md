# Collage seam fixture

An editable, silent, six-second 1280 × 720 HTML composition at 30 fps. Two original paper collages explain how small ideas become a story. All artwork is inline SVG; the fixture uses system Arial, needs no downloads, and makes no network requests. No speech, capture or provider engine is required.

Open `index.html` locally. It stays paused; append `?t=2.9666666667`, `?t=3` or `?t=3.0333333333` to inspect the frame before, at, and after the cut. In the browser console, `window.__timelines.main.seek(seconds)` samples another time.

## Timing and editing

| Layer / stable ID | Start | End | Track |
| --- | ---: | ---: | ---: |
| Outgoing `el-idea` | 0 | 3.2 | 0 |
| Incoming `el-story` | 2.8 | 6 | 1 |
| Master caption `caption` / `caption-text` | 0 | 6 | 2 |

The cut is centered at 3 seconds. The overlap is **[2.8, 3.2)**, not two clips competing on one track. The outgoing artwork holds its final pose throughout that overlap. The incoming wrapper translates from 48px to 0 and fades from 0 to 1 over the opaque outgoing scene. Both `body` and `root` also paint an opaque dark background. At 3.2 the outgoing wrapper hides only after the incoming one reaches full opacity.

The cue from 2.6 to 3.4 seconds deliberately spans the seam: “Nối các mảnh nhỏ thành một câu chuyện.” Captions sit above both wrappers and never inherit their opacity or movement. Adjacent cues use half-open time ranges; the terminal preview at 6 seconds holds the final caption. The renderer samples frames 0–179, ending at 5.966667 seconds.

Edit the Vietnamese copy, `CUES`, or the inline shapes. Keep IDs and layer timing attributes stable. If retiming, change `SEAM`, scene `data-start` / `data-duration`, and caption ranges together. `seek()` assigns every animated property from absolute time, so direct, reverse and repeated seeks match. The small master adapter implements the existing kit renderer's `seek(t, false)` and `duration()` contract without GSAP, timers or autoplay. It is not a pilot of the optional HyperFrames CLI.

## Local verification

Run from the kit root in PowerShell. Render a **cache copy** so renderer outputs never land in the source example:

```powershell
$cache = 'D:/agent-cache/K-STYLE-COLLAGE'
New-Item -ItemType Directory -Force "$cache/fixture", "$cache/tmp" | Out-Null
Copy-Item examples/collage-seam-kit/index.html "$cache/fixture/index.html"
$env:TEMP = "$cache/tmp"
$env:TMP = "$cache/tmp"
& ./.venv/Scripts/python.exe -B tools/render.py "$cache/fixture" --fps 30 --no-audio --out "$cache/seam.mp4"
```

The renderer uses installed Chrome/Playwright and FFmpeg. If those prerequisites are unavailable, rendering is unavailable; the HTML still opens locally. This example does not install engines or supply a provider fallback.

The task's retained acceptance harness uses the existing renderer's `SEEK_JS`, Playwright and Pillow:

```powershell
& ./.venv/Scripts/python.exe -B D:/agent-cache/K-STYLE-COLLAGE/acceptance.py
```

It checks opaque coverage and exact expected captions on all 180 frames, caption safe bounds, distinct overlap tracks, unique IDs, reverse/random/repeated and fresh-load seek parity, unchanged holds, cue boundaries, and zero remote requests. It renders a real silent MP4, probes its frame count, checks every decoded frame for a white flash, and compares rendered frames 89/90/91 with snapshots, including caption pixels. Snapshot/render RGB RMSE must be below 12/255 to allow H.264 compression. Retained evidence is `cut-089.png`, `cut-090.png`, `cut-091.png`, `seam.mp4`, and `acceptance.txt` in that cache. The fixture copy and browser temporary directories are removed after the task; the harness recreates those directories when rerun.

## Concept provenance

Seam mechanics were adapted conceptually from the locally cached community `vox-explainer` references at research pin `ba7a0bb6d3567d124c51f6074625043bfe0b32eb`:

- `D:/agent-cache/KITREPO/repos/hyperframes-community-skills/skills/vox-explainer/references/render-safe-seams.md`: opaque stage, extended outgoing wrapper, early incoming start, separate tracks, master-time transition.
- `D:/agent-cache/KITREPO/repos/hyperframes-community-skills/skills/vox-explainer/references/seam-gate.md`: stable wrapper IDs and verification around cut ± one frame, including random seeks.

This is an original minimal HTML implementation and original local artwork, with no upstream code or media copied. It intentionally uses a composited crossfade; the upstream vector gate's zero-overlap rule belongs to its motion-cut family and is not claimed as a check for this blend. No community skills were installed; no provider or browser history was accessed.
