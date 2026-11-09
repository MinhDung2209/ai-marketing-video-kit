# Hypit 0.3.2 isolated pilot — 2026-11-09

HYPIT-PILOT, rank 21 of [the refresh handoff](../../docs/research/repo-refresh-2026-11-09.md).
**Decision: retain the existing optional 0.2.17 integration.** Exact 0.3.2 source passes the structural frame/caption experiment below; the requested published distribution is unavailable. This evidence supports another isolated pilot, not production migration.

## Actual compatibility result

| Check | Observed result |
| --- | --- |
| Existing integration | Manifest/lockfile pin `@hypit/hypit` 0.2.17; no installed engine at its local `node_modules/@hypit/hypit/package.json` |
| Published 0.3.2 | Explicit public-registry install exits 1 with `ETARGET`; version metadata returns HTTP 404. Public metadata had `latest: 0.3.1` at inspection. No version substitution. |
| Exact source | Cached commit `2d31e88765e297f0795348b460c77a6067f12261`, clean tracked checkout; copied manifest and `bin/hypit.mjs --version` report 0.3.2 |
| Windows / Node | Node v22.23.4; source runs through tsx 4.21.0. Only tsx 4.21.0 and TypeScript 5.9.3 were installed as isolated test helpers. |
| Source regressions | 31 upstream tests pass, zero failed/skipped: Timeline author surfaces, Caption identity and Fine Caption scheduling/render structures |
| Original Vietnamese fixture | Five tests pass, zero failed/skipped; details below |
| Missing optional engine | Explicit `unavailable` result tested with a missing manifest; probe performs no download, startup or fallback |
| Production preservation | All five existing integration files remain byte-identical: manifest, lockfile, runtime profile, README and `.gitignore` |
| Delivery renderer / 0.2 projects | Not validated: no browser pixels, encoded video, speech alignment, audio, full CLI `check`/`plan`, or actual 0.2 production was executed |

Repository version and published release availability are separate evidence. The fixture invokes source APIs through local package junctions; it is not a built or installed Hypit distribution. The kit remains usable without Hypit.

## Experiment and acceptance

The original fixture authors a two-second, 60-frame Timeline at 30/1 fps and a 1080×1920 caption frame. Manually supplied text is `Xin chào || thế giới!`; four unit timings are `[0,15)`, `[15,30)`, `[30,45)` and `[45,60)`. These are synthetic authored times, not ASR output or evidence of Vietnamese alignment quality.

The five tests call the real source APIs:

1. Timeline surface preflight accepts `60f` and rejects `250ms` at 30 fps (7.5 frames).
2. A rational 30000/1001 clock accepts `1001ms`, exactly 30 frames, without rounding fps.
3. Script parsing preserves accents and punctuation. Fine Caption preserves two authored cues and produces spans `[0,30)` and `[30,60)` without changing unit timing.
4. Caption timing rejects missing/duplicate units, fractional frames and a different document identity. Rendering rejects a different Timeline identity.
5. A later Hidden Use over `[15,45)` leaves visibility `[0,15)` and `[45,60)`. Frames 14, 45 and 59 remain visible; 15, 29, 30, 44 and 60 do not. Original unit times remain intact.

**Integration detail:** rendered Presents carry the mask in `visibility`; the outer `span` still covers the original cue envelope. Consumers must honor both. This checks render structures, not pixels. The font is a synthetic resource identity, so this proves neither glyph availability nor browser layout.

Reproduce from PowerShell:

```powershell
& D:/Projects/ai-marketing-video-kit/.venv/Scripts/python.exe `
  D:/agent-cache/K-HYPIT-PILOT/run_acceptance.py --prepare --cleanup
```

`--prepare` verifies the existing cached upstream SHA, copies source into this task's cache, installs only pinned helpers there and maps copied packages locally. It requires `D:/agent-cache/KITREPO/repos/hypit` and Node/npm at `D:/Apps/nodejs/`. It does not install the Hypit engine or start Runtime. A separate isolated install probe records release availability. npm/temp/browser-cache settings all point under this task's D: cache; no keys or speech models are required.

`--cleanup` removes copied source, dependencies, junctions, the release-probe project and temporary caches. Retained acceptance evidence under `D:/agent-cache/K-HYPIT-PILOT/` includes the harness, `pilot.test.mjs`, `fixture-result.json`, `acceptance.log`, both TAP logs, install logs, source/original-file hashes, registry observations and the helper manifest/lockfile. The harness passed again after rebuilding from a cleaned cache.

Actual final acceptance output (2026-11-09 10:32:27 UTC):

```text
Source: 2d31e88765e297f0795348b460c77a6067f12261 (package.json 0.3.2; exact source, not published distribution)
node: v22.23.4
source version: 0.3.2
Published 0.3.2: {"status": "unavailable", "http": 404, "reason": "The requested published version is absent from the public npm registry"}
Published install exit=1; npm error notarget No matching version found for @hypit/hypit@0.3.2.
PASS missing optional engine: {"status": "unavailable", "reason": "Optional Hypit engine is not installed at the selected manifest; use an isolated explicitly pinned installation. No fallback or runtime startup attempted."}
> node --import tsx --test --test-reporter=tap source/packages/timeline-author/test/surface.test.ts source/packages/caption/test/caption.test.ts source/packages/caption-fine/test/caption-fine.test.ts
1..31
# tests 31
# suites 0
# pass 31
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 1074.7892
exit=0
> node --import tsx --test --test-reporter=tap pilot.test.mjs
1..5
# tests 5
# suites 0
# pass 5
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 473.2805
exit=0
Original Hypit integration preservation: 5/5 byte-identical
RESULT: PASS structural exact-source experiment; published 0.3.2 unavailable; no production migration or browser/render parity claimed.
CLEANUP: removed copied source, dependencies, npm/temp caches and release probe; evidence and rerun scripts retained.
```

The release install failure is expected availability evidence, not a successful render:

```text
npm error code ETARGET
npm error notarget No matching version found for @hypit/hypit@0.3.2.
npm error notarget In most cases you or one of your dependencies are requesting
npm error notarget a package version that doesn't exist.
exit=1
```

Full output and test names are retained in `acceptance.log`, `published-install.log`, `upstream.tap` and `pilot.tap`.

## Manual migration sequence for a future production

1. **Keep 0.2 recoverable.** Inventory the executable, manifest/lockfile, Sources, Recipes, Runs, project packages, profile, assets and Results. Preserve a separate working copy before editing. Keep accepted `index.html`, stable IDs and every `voice.json` caption override. This task did not edit or upgrade the current integration.
2. **Select an available exact target in a separate D: cache.** Verify published metadata first. While 0.3.2 is absent, return `unavailable` and stop that release migration. Exact-source investigations must name this SHA and remain separate from the published-release path. Do not substitute `latest`, alter the existing lockfile, or call `runtime up` inside a 0.2 production. Full source-distribution packaging was outside this experiment.
3. **Repair language entries deliberately.** Keep Author reader `@hypit/markup@1`; old Run reader `@hypit/run-markup@1` becomes `@hypit/markup/run@1`. Ordinary Recipe sheets move from `@hypit/svs@1` to `@hypit/recipe@1`; Text-template sheets retain `@hypit/text/svs@1`. Preserve the actual Author path, output targets, Candidates and reuse declarations. Logical `@1` addresses are language interfaces, not npm package versions.
4. **Re-express relationships.** Declare Clock, finite Timeline and Canvas. Keep exact frame counts/rational rates. Replace implicit semantic timing with explicit Projections and named absolute Windows/Instants. Place picture/sound in Visual/Audio Clips and select their outputs in Film. Feed the Composition into `@hypit/html-video@1`. The kit mixes externally: begin with picture-only output and prove sound ownership before selecting AudioTracks, avoiding duplicated narration/music.
5. **Preserve authored captions.** Supply CaptionDocument plus complete CaptionTiming keyed by unit ID, rather than only Script and Timeline. Script-derived timing uses `@hypit/narrative-caption@1` with its binding and Projection. Preserve `||` grouping, display/pronunciation relationships, accents, sidecar tags/settings and corrected `voice.json` text. Use a validated import adapter; never regenerate over manual corrections. Styles and timed Uses change presentation without retiming words. Fine Caption is a separate family (`@hypit/caption-fine`). Missing units/identity mismatches require explicit repair. A kit-to-Hypit caption adapter was not implemented here.
6. **Update affected SDK dependencies.** The 0.3.1 migration moves domain imports such as `@hypit/hypit/caption`, `/composition`, `/media`, `/temporal` and `/timeline` into corresponding independent `@hypit/*` packages. Generic host imports such as `@hypit/hypit/author`, `/producer` and `/protocol` remain. Rebuild each component's own source and declare its actual dependencies. Do not patch `node_modules` or assume packages share the host version. Review the full mapping and package peers; do not bypass errors with `--force`.
7. **Review Runtime separately.** The old profile's `@hypit/provider-hyperframes-local`, `@hypit/provider-media-local` and platform credential store are historical selections. Current docs select Runtime Local, `@hypit/provider-html-local`, `@hypit/media-local`, and a local/environment credential store. Use the chosen release's schema/provider README; do not blindly rename profile strings. Keep WhisperX and other engines optional. Missing engines return actionable status without provider substitution. Later engine/browser/model installs require explicit D: destinations. None ran here.
8. **Preserve Results and verify the copied production.** Reuse compatible accepted Outputs through explicit Run Candidates. Never relabel old structured Results as new types. Retain raw media where normalization must be repeated. With an actual installed target, identify it using `hypit version`/`hypit paths`, rebuild changed packages, run `hypit check` on the real Source and Run, and inspect `hypit plan <run> --runtime <profile>` before execution. These full CLI migration checks remain pending; the source API fixture does not replace them.
9. **Require rendered evidence before adoption.** Inspect the 29/30-frame handoff, final exclusive bounds, forward/reverse seeks, holds, late fonts/images, looping video and 16:9/9:16 captions using actual Vietnamese-capable fonts. Compare snapshots and encoded full/range renders, original-program-time sampling, multiple workers where supported, audio ownership and measured duration. Keep editable kit HTML and `tools/to_studio.py` authoritative. Production cutover is a separate owner action after reviewing that evidence.

If a required component, provider or release is unavailable, retain the production's known-working exact version, lockfile and Results. Rollback selects the preserved 0.2 working copy; accepted assets must not be deleted to make migration appear successful.

## Pinned upstream references

- [Source snapshot](https://github.com/hypit-ai/hypit/tree/2d31e88765e297f0795348b460c77a6067f12261)
- [0.3 migration](https://github.com/hypit-ai/hypit/blob/2d31e88765e297f0795348b460c77a6067f12261/migrations/0.3.md)
- [0.3.1 SDK mapping](https://github.com/hypit-ai/hypit/blob/2d31e88765e297f0795348b460c77a6067f12261/migrations/0.3.1.md)
- [Package ownership](https://github.com/hypit-ai/hypit/blob/2d31e88765e297f0795348b460c77a6067f12261/docs/guide/packages.md)
- [Frame preflight tests](https://github.com/hypit-ai/hypit/blob/2d31e88765e297f0795348b460c77a6067f12261/packages/timeline-author/test/surface.test.ts)
- [Caption timing validation](https://github.com/hypit-ai/hypit/blob/2d31e88765e297f0795348b460c77a6067f12261/packages/caption/src/temporalize.ts)
- [Fine Caption scheduling](https://github.com/hypit-ai/hypit/blob/2d31e88765e297f0795348b460c77a6067f12261/packages/caption-fine/src/schedule.ts)
