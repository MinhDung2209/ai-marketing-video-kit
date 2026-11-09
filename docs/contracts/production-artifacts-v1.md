# Production artifacts v1

This contract maps kit tool results to the existing **KWF product-demo v1** stages. The adjacent [JSON contract](production-artifacts-v1.json) is a JSON Schema for a **single stage attempt's artifact receipt**. Its `examples[0]` is one complete synthetic render manifest. It introduces no workflow transitions, queue, approval service or Studio UI. KWF's `D:/Projects/kit-studio/docs/workflows/product-demo.json` and its `backend/workflow/{service,check}.mjs` remain authoritative. KNEW consumes resumable receipts; KDAY owns queued attempts/retries; the Studio backend invokes tools and translates evidence.

The JSON's `x-authoritative-workflow` records the raw source SHA-256, and `x-kwf-stage-mapping` projects the exact stage IDs, required files, checklist keys and evidence filenames. A definition hash mismatch requires mapping review before consumption. Do not deploy that projection as a second workflow definition. No adapter or automatic manifest ingestion is implemented by these two documents.

## Existing stage mapping

All required paths below are relative to the Studio **clip**. Work/build paths are separate. `workflow-evidence/<stage-id>.json` is required by the existing checker for every non-approval stage, even when absent from `requiredFiles`. Approval stages have no evidence sidecar and no required files; their authority is the trusted owner's approval in `workflow.json`.

| Existing ID | KWF required files | Kit output or existing owner responsibility |
| --- | --- | --- |
| `brief` | `brief.md` | Studio producer records scope, destination, rules and safe actions. No kit brief generator is implied. |
| `research` | `research.json` | Existing researcher records actual labels, figures, URLs, observation times, safe route and screenshots. Backend/agent writes the receipt. |
| `script` | `script.md`, `voice.json` | Scriptwriter creates both from verified research; retain manual caption overrides. |
| `script-approval` | none | Trusted KWF owner action records approval in `workflow.json`; agents/tools cannot grant it. |
| `record` | `recording.json` | `screendemo/shoot.py <work> --list`, then approved shot IDs, produces recordings/sheets in `assets/screen/<shot-id>/`. Backend/record owner writes `recording.json` with recording hashes, observations and reviewed sheets. |
| `voice` | `voice.json`, `voice-review.json` | Existing `tools/tts_script.py` emits per-line MP3, `narration.mp3`, `timing.json`; `screendemo/chunks.py` inspects phrase timing. Voice owner preserves `voice.json`, records owner listen approval with who/when/reference in `voice-review.json`, and hashes actual audio/timing. |
| `build` | `build-manifest.json` | `screendemo/produce.py <work> --build --only full` runs `story.py` and produces HTML/cues; snapshots and `--qa --qa-source build --only full` produce visual evidence. Backend/build owner writes `build-manifest.json` with build root, actual paths/hashes and QA. |
| `to-studio` | `index.html`, `studio.json`, `voice.json` | `tools/to_studio.py <build> <clip>` writes initial Studio master/assets/metadata. Backend preserves existing workflow evidence separately; the transfer does not create KWF evidence or grant permission to overwrite edits. |
| `studio-qa` | `index.html`, `voice.json`, `studio.json` | Studio QA owner runs lint/snapshots against the current master, records exact KWF checklist plus `firstSceneEnd`, `inkTimes`, `stickerTimes` and human observations in `workflow-evidence/studio-qa.json`. |
| `owner-review` | none | Trusted KWF owner watches/listens to current Studio preview and approves or sends back through the existing workflow service. |
| `render` | `renders/final.mp4`, `render-review.json` | Existing KWF command is `npx hyperframes render -o renders/final.mp4 -q delivery`. Render owner captures actual MP4 frames, probe/audio evidence and approved master hash in `render-review.json`. |
| `publish-package` | `publish-package.json` | Existing packaging owner prepares local MP4, title, description, CTA, thumbnail, review/probe evidence and credits (including Noto when used). This is not `tools/make_package.py`, which packages the kit distribution. Actual posting requires a separate owner instruction. |

Required KWF receipts (`recording.json`, `voice-review.json`, `build-manifest.json`, `render-review.json`, `publish-package.json`) are **not automatically emitted** by the listed raw kit commands. Their existing backend/stage owners write them; this contract does not invent those tools. The JSON preserves all exact checklist keys for review without proposing replacements.

KWF's command remains recorded as written. Selecting a pinned renderer/optional picture-only adapter is the backend owner's integration decision; this contract does not update installed engines. Kit `produce.py`'s pre-transfer `final/<slug>-<variant>.mp4` does not satisfy the approved Studio render by filename alone. Validate provenance and render the approved master. Picture-only optional rendering must retain the existing external audio mix until parity is established; never mix the same audio twice.

## Receipt fields and paths

One manifest represents one completed stage attempt. Required top-level fields and nested types are defined in the JSON Schema. Store receipts append-only at a caller-owned location such as `production-artifacts/<stage-id>/<attempt-id>.json` in the clip, without adding that suggested location to KWF's required files. The caller allocates and persists unique `manifest_id`, `attempt.id`, positive `attempt.number` and named `attempt.owner` before running tools. Reattempts have a new ID/number and retain the prior failure receipt; parallel results inside an attempt have unique tool result IDs. KDAY remains responsible for deduplication, ownership, timeouts, cancellation and retry policy. A worker name in JSON is attribution, not authenticated owner authority.

- `workflow`: exact definition ID/version/hash and observed workflow revision. KWF still checks the current revision on mutation; these fields cannot authorize a stale write.
- `roots.clip`, `roots.work`: absolute caller-approved project/build roots outside the read-only kit. Never use the kit source tree as a build target. Resolve real paths before reading or accepting outputs.
- `input_hashes`: all consumed files, including relevant profile/rules, tool scripts/pins, rendered assets, captions, voice/timing, QA evidence and dependency manifests. Copy external consumed config/scripts into a bounded work snapshot when needed; record the originals' provenance there. A path or timestamp alone is insufficient. Include the definition hash and selected engine/version/options as provenance; save options/pins in a hashed work file if they influence output. A changed engine/config invalidates reuse even if a source filename stays the same.
- `artifacts`: accepted output files, each with `root`, normalized forward-slash relative `path`, raw-byte lowercase `sha256` and positive `bytes`. Hash exactly the disk bytes, without newline/Unicode/JSON normalization. Use `root:path` (for example `clip:renders/final.mp4`) for `tool_results[].artifact_paths`; every reference must match one artifact. Directory outputs such as `assets/` are enumerated file by file; include a hashed inventory snapshot in the inputs so additions/removals are detected. Reject duplicate root/path pairs, absolute/traversal/drive/backslash paths, symlink/junction escapes, missing/empty files and mismatched sizes/hashes. Do not hash a directory name as a file.
- `tool_results`: terminal results from individual invocations, with stable tool identity/version or source pin, status, exit code, message, accepted artifact references and structured error/remediation. A legacy stdout-only tool is wrapped by the existing backend; preserve actual exit status, validate promised files, and optionally hash retained logs. Printed success alone is insufficient.
- `review_evidence`: separate automated observations and human watch/listen evidence, with reviewer/time/decision, actual evidence file hashes, subject hashes and checklist booleans. `passed` means this review passed; it grants no owner approval. Automated measurement must never impersonate a human. A send-back or changed subject invalidates review reuse.
- `approval_refs`: snapshots of actual KWF owner approvals (`stage_id`, `state_file`, revision, who/when, digest and gate input hashes). Re-read current trusted workflow state and recompute before use. Do not put a hash of the mutable whole `workflow.json` into an approval digest or hash the manifest into itself; it would become stale on every state write.

The JSON Schema validates shape/status conditions; filesystem containment, referential integrity, completeness, identity, timestamp ordering, current workflow state, hash verification and review freshness require consumer checks. `attempt.finished_at >= started_at`; review times must describe the relevant output/review. Non-file inputs (owner instructions, engine options, selected source URLs) belong in a captured hashed receipt, not an invented file hash.

## Tool result statuses and unavailable engines

| Status | Exit code | Consumer behavior |
| --- | --- | --- |
| `succeeded` | `0` | Accept only verified promised artifacts. Stage completion still needs KWF evidence/checks/gates. A read-only probe may succeed with no artifact output. |
| `failed` | nonzero or `null` for wrapper/validation failure | Preserve structured cause/diagnostics; no artifact references from this invocation. Exclude partial files from accepted artifacts. |
| `unavailable` | `null` | Selected optional engine/module/model/platform or paused service cannot run. No invocation, no artifact paths; report what was missing and an actionable selection/install remedy. |
| `cancelled` | nonzero or `null` | No artifact references. Stop owned processes, release resources, preserve diagnostics. Retry only under scheduler/owner policy. |
| `timed_out` | nonzero or `null` | No artifact references. Deadline expired; stop owned processes and release resources. Never adopt incomplete output. |

For CLI adapters, envelope `exit_code` is the child process exit code. An unavailable adapter may itself exit nonzero while its absent child's `exit_code` remains `null`. An invocation that exits zero but produces invalid/missing outputs is `failed` with `exit_code: null` and a validation error retaining the raw exit in diagnostic evidence.

WhisperX, VieNeu, Cap/OpenScreen, Streamlink, HyperFrames adapters and other new engines stay optional. Missing installation is not stage success and never triggers Google/hosted/provider fallback. A selected required capability that is unavailable blocks that stage; an optional QA supplement can be omitted only through the existing owner's explicit evidence/policy while required KWF checks still pass. Google narration remains paused under the current KWF instructions until the owner restores service or authorizes another existing tool. This contract does not authorize alternative TTS. Installation/configuration, when explicitly chosen, stays on `D:/`; no keys are added.

Example **tool result** for an absent optional engine (not a second manifest):

```json
{
  "id": "align-probe-1",
  "tool": "WhisperX",
  "version_or_pin": "not-installed",
  "status": "unavailable",
  "exit_code": null,
  "message": "Optional WhisperX alignment is unavailable; no alignment ran.",
  "artifact_paths": [],
  "error": {
    "code": "ENGINE_UNAVAILABLE",
    "message": "Selected WhisperX module/model was not found.",
    "remediation": "Choose an authorized existing path, or configure an isolated engine under D:/ and rerun explicitly."
  }
}
```

## Existing approval digest and invalidation

Use the **existing KWF** `approvalDigest(clip, stage)` implementation. It hashes the UTF-8 relative filename followed immediately by that file's raw bytes, for each file in the exact order below, into a single SHA-256. Do not substitute a sorted JSON hash, concatenate individual hex hashes, add delimiters, or include the artifact manifest. `approval_refs[].input_hashes` exposes the separate raw file hashes for auditing; `approval_digest` is the distinct existing KWF aggregate.

| KWF gate | Exact existing digest inputs, in order |
| --- | --- |
| `script-approval` | `script.md`, `voice.json`, `research.json` |
| `owner-review` | `index.html`, `voice.json`, `studio.json`, `workflow-evidence/studio-qa.json` |

`brief.md`, asset bytes, narration/timing/captions and tool/config/pin inventories are additionally captured by artifact input/review hashes. **Current KWF gate digests do not cover all transitive inputs.** On any transitive change, missing file, different checksum/size, definition drift, stale attempt revision or send-back, the consumer rejects reuse of affected receipts/reviews, and asks the existing workflow service/owner to send back the relevant stage and invalidate dependent steps/approvals. The contract does not implement this extra automatic detection or claim the current KWF service already watches those inputs. Use the service's current revision and trusted owner identity; never patch workflow state directly.

For example, changing `voice.json` after script approval makes the existing script gate stale, including a timing/metadata-only change. Keep generated timing in `timing.json` and preserve approved voice bytes where possible. If voice or human caption text changes, reconcile the intended script/voice metadata and obtain new script approval through existing send-back. After `to-studio`, `index.html` is the master. Do not rerun story/build/import over human edits; even `produce.py --snap` rebuilds. Use Studio snapshots for Studio QA. `doi_loi.py` currently changes HTML/audio without persisting replacement text into `voice.json`; the existing owner must reconcile those representations before hashes, QA and renewed approval can be trusted. No tool is changed here.

Resume a failed stage only when its current inputs, approvals and ownership still match. Keep upstream accepted artifacts and reviews intact; rerun the affected attempt rather than the whole pipeline. A render interrupted by the system is not automatically restarted. Send-back and reapproval remain existing KWF/KNEW/KDAY responsibilities.

## One complete example and acceptance

The JSON's `examples[0]` contains every required manifest field: render attempt 2, named owner, definition/revision, inputs, six output/evidence files, tool result, automated and human review records, and both referenced approval gates with input hashes and reproducible KWF digests. `x-example-file-contents-utf8` gives **all exact example file bytes** as UTF-8 strings. The `.mp4`/`.jpg` example payloads are explicit text placeholders, not decodable media; reviewer names, measurements and approvals are fictional. Materialize them only in the task cache for contract/hash tests. No actual render, audio measurement, owner approval or production completion is claimed by this example.

Acceptance must validate the schema and example; compare all 12 stage projections against the live KWF definition; verify every example artifact/input/review/gate hash and size; compare gate digests with the real KWF implementation; reject changed script, master and transitive asset input; reject invalid/unavailable-success results, missing evidence and unsafe paths; and exercise actual absent-engine discovery without invoking a provider. Tests use the kit venv and fixtures only under `D:/agent-cache/K-DAILY-CONTRACT/`.

This is a documentation/contract handoff. The required KWF/KNEW/KDAY mapping review and exact acceptance output are recorded in `D:/Projects/kit-studio/orchestration/reports/K-DAILY-CONTRACT-report.md`. Schema acceptance does not establish renderer parity, real recording quality, TTS/ASR quality, or downstream ingestion. Owners must wire consumers in their existing scoped modules.
