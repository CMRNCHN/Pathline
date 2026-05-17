# 1. Goal
Deliver the requested 68% → 82% Operational Cohesion phase as three independently shippable plans: `A+B` replay/operator UX polish, `C+D` demo/runtime hardening, and `E` continuity/documentation finish.

# 2. Approach
The repo already has the right architectural spine, so the plan focuses on finishing existing seams instead of adding new ones. The review workspace already has real replay APIs in [backend/python/src/ivr_assessor/backend/routes/replay_routes.py:11-123], but the frontend still mixes minimal live replay hydration in [backend/python/src/ivr_assessor/frontend/static/js/modules/replay.js:11-160] with mock review UI in [backend/python/src/ivr_assessor/frontend/static/js/main.js:999-1135]; the fastest safe path is to replace those mock surfaces with deterministic data-backed rendering and shared UI primitives already anchored in [backend/python/src/ivr_assessor/frontend/static/css/main.css:1086-1455].

In parallel, runtime/demo hardening should stay inside current topology: startup and diagnostics live in [backend/python/src/ivr_assessor/live_map_gui.py:52-388], replay loading in [backend/python/src/ivr_assessor/events/replay_service.py:50-171], and recovery/cleanup in [backend/python/src/ivr_assessor/runtime/runtime_supervisor.py:74-260], [backend/python/src/ivr_assessor/runtime/recovery_manager.py:11-69], and [backend/python/src/ivr_assessor/runtime/session_cleanup.py:14-77]. Documentation should be finalized last because current continuity artifacts still have drift and duplication: test count mismatch in `.ai/AIR_RULES.md:23-24`, stale priorities in `.ai/NEXT_SESSION.md:9-17`, and casing/path drift in `.ai/HANDOFF.md:37-48` versus the actual `.ai/PLANS`, `.ai/TASKS`, and `.ai/SESSION_LOGS` tree.

# 3. File Changes

## Plan 1: Agent A + Agent B
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/modules/replay.js:12-160`
  - Replace one-shot replay loading with staged loading, explicit empty/error handling, and state handoff into the review workspace.
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/modules/replay_timeline.js:8-155`
  - Add smoother cursoring/scrubbing behavior, focus handling, optimistic cursor updates, and tighter diff/timeline rendering without changing replay semantics.
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/main.js:999-1135`
  - Remove the mock review header/timeline/transcript/template content and render those surfaces from replay state, cursor metadata, and alignment data.
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/common/state.js:1-89`
  - Add narrowly scoped replay UI state for loading phase, selected transcript row, comparison selection, bookmarks, and restore-on-exit behavior.
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/common/api.js:1-44`
  - Add explicit helpers for the already-existing replay subroutes and any missing waveform/alignment endpoints.
- **Modify** `backend/python/src/ivr_assessor/frontend/templates/index.html:391-469`
  - Add stable review-workspace containers for loading, empty, comparison, bookmark, and replay focus surfaces.
- **Modify** `backend/python/src/ivr_assessor/frontend/static/css/main.css:1086-1455`
  - Normalize typography, palette token usage, shared button/badge/loading styles, and panel rhythm.
- **Modify** `backend/python/src/ivr_assessor/frontend/static/css/main.css:395-635`
  - Refine review header, timeline, waveform, transcript, and template-builder layout so replay feels stable rather than mock-like.
- **Modify** `backend/python/src/ivr_assessor/frontend/static/css/main.css:1960-1972`
  - Replace generic empty-state styling with a reusable operator-grade pattern used across review, run, and discover.

## Plan 2: Agent C + Agent D
- **Modify** `backend/python/src/ivr_assessor/backend/routes/replay_routes.py:15-123`
  - Tighten route-level replay validation/error surfaces and expose the missing review data paths consistently.
- **Modify** `backend/python/src/ivr_assessor/events/replay_service.py:21-171`
  - Add explicit replay validation helpers, bounded offset handling, and clearer failure reasons while preserving deterministic reconstruction.
- **Modify** `backend/python/src/ivr_assessor/events/waveform_metadata.py:22-35`
  - Replace placeholder-only behavior with deterministic fallback metadata and missing-media signaling.
- **Modify** `backend/python/src/ivr_assessor/live_map_gui.py:83-131`
  - Harden startup checkpointing and operator-facing recovery/fallback messages around stream server readiness.
- **Modify** `backend/python/src/ivr_assessor/live_map_gui.py:259-343`
  - Improve runtime/replay visibility payloads so demo/reset/status surfaces can rely on stable structured data.
- **Modify** `backend/python/src/ivr_assessor/live_map_gui.py:668-833`
  - Tighten replay GET routing and export response/error behavior without changing endpoint names.
- **Modify** `backend/python/src/ivr_assessor/runtime/runtime_supervisor.py:80-250`
  - Make stale detection, state transitions, and operator-facing failure context more explicit and testable.
- **Modify** `backend/python/src/ivr_assessor/runtime/recovery_manager.py:20-66`
  - Clarify bounded recovery messaging and attempt bookkeeping.
- **Modify** `backend/python/src/ivr_assessor/runtime/session_cleanup.py:20-77`
  - Make cleanup idempotency and final registry removal behavior explicit and verifiable.
- **Modify** `backend/python/tests/test_replay_sync.py:1-114`
  - Extend replay timing coverage for alignment/cursor expectations after frontend-facing replay changes.
- **Modify** `backend/python/tests/test_runtime_supervisor.py:1-101`
  - Add stale-runtime, recovery, and operator-message assertions.
- **Modify** `backend/python/tests/test_recovery_manager.py:1-46`
  - Tighten bounded-recovery and failure-event expectations.
- **Modify** `backend/python/tests/test_session_cleanup.py:1-40`
  - Fix current idempotency expectations to match the desired contract and add repeat-call coverage.
- **Create** `backend/python/tests/test_replay_routes.py`
  - Cover replay 404/400 behavior, cursor bounds, waveform fallback, and alignment route consistency.
- **Create** `backend/python/tests/test_demo_resilience.py`
  - Cover startup/readiness/export fallback behavior at the HTTP payload level.

## Plan 3: Agent E
- **Modify** `README.md:1-108`
  - Collapse the root README into a concise operator-first quick start and link outward to deeper docs.
- **Modify** `backend/python/README.md:1-41`
  - Replace the current minimal backend note with an engineering quick start tied to the actual pytest path and runtime commands from `.ai/PROJECT_STATE.md:12-19` and `AGENTS.md`.
- **Modify** `backend/python/docs/OPERATIONS.md:1-161`
  - Refocus the runbook into an operator quick start plus live/review/demo flows, not just terminology.
- **Create** `backend/python/docs/REPLAY_QUICK_START.md`
  - Provide a concrete review/replay walkthrough for operators using the real review workspace and replay endpoints.
- **Create** `backend/python/docs/DEMO_QUICK_START.md`
  - Provide a deterministic demo/reset path grounded in the current local-first startup flow.
- **Modify** `.ai/PROJECT_STATE.md:9-19`
  - Keep authoritative test count, replay surface summary, and commands aligned with delivered work.
- **Modify** `.ai/NEXT_SESSION.md:9-17`
  - Replace stale priorities after implementation lands.
- **Modify** `.ai/HANDOFF.md:37-48`
  - Fix governance-file references and record changed boundaries/risks for the finished phase.
- **Modify** `.ai/AIR_RULES.md:23-24`
  - Update the outdated `240 passing` floor to match the repo’s current baseline and avoid future planning drift.
- **Modify** `.ai/PLANS/ivr-phase-operations-anchor.md`
  - Only if needed to align wording introduced by the new quick starts; keep it governance-only.
- **Create** `.ai/DECISIONS/2026-05-15-review-workspace-data-backed-replay.md`
  - Record the non-obvious decision to replace mock review content with deterministic replay-backed rendering using existing endpoints.

# 4. Implementation Steps

## Plan 1: Replay UX + Operator Cohesion

### Task 1: Replace mock review rendering with real replay-backed rendering
1. In `backend/python/src/ivr_assessor/frontend/static/js/main.js:1006-1119`, replace the hard-coded review header, timeline markers, and transcript rows with renderers that consume `AppState.replayState`, replay cursor metadata, and alignment data.
2. In `backend/python/src/ivr_assessor/frontend/static/js/modules/replay.js:31-101`, persist the hydrated replay payload into shared state and trigger targeted review re-renders instead of only calling legacy global hooks.
3. In `backend/python/src/ivr_assessor/frontend/templates/index.html:392-463`, add explicit placeholders for review summary chips, transcript empty state, bookmark rail, and comparison state so JS can update stable nodes instead of rewriting unrelated markup.

### Task 2: Tighten replay timeline interaction without changing semantics
1. In `backend/python/src/ivr_assessor/frontend/static/js/modules/replay_timeline.js:14-79`, add optimistic cursor display updates, in-flight seek guarding, bounded scrub throttling, and last-request wins behavior.
2. In `backend/python/src/ivr_assessor/frontend/static/js/modules/replay_timeline.js:81-155`, replace the current button-only controls with a real scrub track, clearer time display, selected-event focus treatment, and bounded diff log updates.
3. In `backend/python/src/ivr_assessor/frontend/static/js/common/api.js:1-44`, add helpers for `/api/replays/<id>/timeline`, `/state/<offset>`, `/cursor/<offset>`, `/diff/<from>/<to>`, waveform metadata, and alignment lookup so replay code stops hand-assembling paths.

### Task 3: Add trustworthy loading, empty, and comparison states
1. In `backend/python/src/ivr_assessor/frontend/static/js/modules/replay.js:12-29` and `110-130`, stage replay loading into list refresh, session selection, timeline hydration, and completion/failure states.
2. In `backend/python/src/ivr_assessor/frontend/static/js/common/state.js:1-89`, add review-local state for `loadingPhase`, `selectedTranscriptEventId`, `bookmarks`, `comparisonSessionId`, and `liveRestoreSnapshot`.
3. In `backend/python/src/ivr_assessor/frontend/templates/index.html:416-466`, add review empty-state containers for no sessions, no waveform, no transcript, and comparison-not-selected.

### Task 4: Standardize shared operator UI primitives
1. In `backend/python/src/ivr_assessor/frontend/static/css/main.css:1086-1126`, switch the global UI font token from Inter to IBM Plex Sans / IBM Plex Mono and preserve the current warm-charcoal palette tokens unless a value must shift for contrast.
2. In `backend/python/src/ivr_assessor/frontend/static/css/main.css:1271-1421`, unify button, badge, panel-header, spacing, and focus-visible rules so status surfaces look consistent across prep/live/review/run.
3. In `backend/python/src/ivr_assessor/frontend/static/css/main.css:1960-1972`, replace the one generic empty-state pattern with a reusable operator-empty style that works in replay, discover, and run surfaces.

### Task 5: Reduce review-workspace jitter and dead UI patterns
1. In `backend/python/src/ivr_assessor/frontend/static/css/main.css:395-635`, stabilize review layout dimensions for waveform, timeline, transcript, and template panes so scrubbing does not shift the page.
2. In `backend/python/src/ivr_assessor/frontend/static/js/main.js:999-1135`, remove stale labels and duplicate review controls that conflict with the actual replay selector in `index.html`.
3. Audit dead listeners in `main.js` and `replay.js` so the review workspace does not render mock content after a real replay session loads.

## Plan 2: Demo Hardening + Runtime Recovery

### Task 1: Tighten replay route and service validation
1. In `backend/python/src/ivr_assessor/backend/routes/replay_routes.py:15-123`, convert replay-not-found, invalid offset, and missing media cases into explicit `FileNotFoundError` or `ValueError` paths that the HTTP layer already maps at `live_map_gui.py:781-784`.
2. In `backend/python/src/ivr_assessor/events/replay_service.py:50-171`, add private validation helpers for session existence, normalized offsets, and route-friendly error messages without changing reconstruction order.
3. In `backend/python/src/ivr_assessor/live_map_gui.py:668-693`, wire any missing replay subroutes consistently and preserve current endpoint names.

### Task 2: Make waveform and replay loading deterministic under missing artifacts
1. In `backend/python/src/ivr_assessor/events/waveform_metadata.py:22-35`, return structured zeroed metadata plus a reason/status field when recordings are absent instead of an uninformative placeholder.
2. In `backend/python/src/ivr_assessor/backend/routes/replay_routes.py:102-123`, expose waveform and alignment data in a way the frontend can treat as present-but-empty rather than failed.
3. Add regression tests in `backend/python/tests/test_replay_routes.py` for missing recording, empty waveform, and alignment lookup responses.

### Task 3: Harden startup, reset, and export behavior for demos
1. In `backend/python/src/ivr_assessor/live_map_gui.py:83-131`, make startup checkpoints and operator messages clearly distinguish `ready`, `timeout`, and `error` states for the stream server.
2. In `backend/python/src/ivr_assessor/live_map_gui.py:303-343`, extend runtime metrics with the minimum extra flags needed for deterministic demo resets and recovery messaging.
3. In `backend/python/src/ivr_assessor/live_map_gui.py:805-833`, tighten export handling so empty graphs, unsupported formats, and missing targets return explicit operator-safe outcomes.
4. Cover these cases in `backend/python/tests/test_demo_resilience.py` and extend `backend/python/tests/test_live_map_gui.py` if route-level assertions are a better fit.

### Task 4: Clarify stale detection, bounded recovery, and cleanup semantics
1. In `backend/python/src/ivr_assessor/runtime/runtime_supervisor.py:80-250`, factor stale-session detection into an explicit helper, include the threshold in operator-facing payloads, and keep the watchdog bounded.
2. In `backend/python/src/ivr_assessor/runtime/recovery_manager.py:20-56`, include attempt count and operator action text in recovery failure/attempt events.
3. In `backend/python/src/ivr_assessor/runtime/session_cleanup.py:20-77`, make repeated cleanup calls idempotent after registry removal and emit exactly one cleaned-success lineage event per session.
4. Update `backend/python/tests/test_runtime_supervisor.py`, `test_recovery_manager.py`, and `test_session_cleanup.py` to lock those semantics.

### Task 5: Verify replay performance and frontend load behavior
1. Add a focused seek-latency test in `backend/python/tests/test_replay_routes.py` or a new replay-service test that loads a representative event stream and asserts bounded seek reconstruction time.
2. Use existing replay reconstruction tests such as `backend/python/tests/test_snapshot_replay_equivalence.py` and `backend/python/tests/test_temporal_reconstruction.py` as the baseline for preserving semantics.
3. Document any measured threshold used in tests so future replay polish does not hide a regression behind smoother UI.

## Plan 3: Operational Finish

### Task 1: Consolidate operator-facing entry points
1. Rewrite `README.md:1-108` into a short operator-first entry with purpose, three startup commands, and links to deeper docs.
2. Rewrite `backend/python/README.md:1-41` into an engineering quick start with exact install, test, and run commands already documented in `.ai/PROJECT_STATE.md:169-183` and `AGENTS.md`.
3. Expand `backend/python/docs/OPERATIONS.md:22-161` into a task-oriented runbook with operator quick start, review quick start, and live/review boundaries.

### Task 2: Add replay and demo quick starts
1. Create `backend/python/docs/REPLAY_QUICK_START.md` covering replay selection, timeline scrubbing, transcript alignment, export, and comparison flow against the real review workspace.
2. Create `backend/python/docs/DEMO_QUICK_START.md` covering deterministic startup, known-good review path, reset path, and fallback messaging for demo operators.
3. Cross-link both from `README.md` and `backend/python/docs/OPERATIONS.md`.

### Task 3: Repair continuity drift in `.ai`
1. Update `.ai/HANDOFF.md:37-48` so governance-file references match the actual `.ai/PLANS`, `.ai/TASKS`, and `.ai/SESSION_LOGS` tree.
2. Update `.ai/AIR_RULES.md:23-24` so the documented test floor matches the current 296-pass baseline in `.ai/PROJECT_STATE.md:12-19`.
3. Replace `.ai/NEXT_SESSION.md:9-17` with the next highest-value post-phase priorities after this work lands.
4. Add one decision record under `.ai/DECISIONS/` for the replay-review rendering seam if the implementation introduces non-obvious conventions.

# 5. Acceptance Criteria

## Plan 1
- Loading a replay from the review workspace updates header, timeline, transcript, graph, and metrics from real replay data rather than mock rows.
- Scrubbing or stepping changes the visible cursor immediately and never renders an out-of-range cursor.
- The review workspace shows explicit empty states for no sessions, no waveform, and no transcript, with no broken layout.
- Review-workspace button, badge, and panel styles match the shared spacing/type system and use IBM Plex consistently.
- Review loading or scrubbing does not visibly reflow adjacent panels on desktop widths >= 1280px.

## Plan 2
- Replay routes return `404` for missing sessions and `400` for invalid replay requests with actionable error text.
- Waveform metadata requests return a structured payload even when the recording is missing.
- Runtime metrics expose enough state to tell whether startup, replay loading, or recovery is waiting, degraded, or failed.
- A repeated cleanup call after a successful cleanup remains safe and does not emit duplicate lineage events.
- Recovery attempts stop at the configured bound and surface the attempt count/operator message.
- The full backend test command from `.ai/PROJECT_STATE.md` remains green, with the known `webrtcvad` caveat only if the active environment lacks it.

## Plan 3
- Root README is a short project entry point, not a mixed operator/CLI dump.
- Backend README gets a real engineering quick start tied to the actual repo commands.
- Operator docs cover start, review/replay, and demo-reset flows without contradicting runtime constraints.
- `.ai` continuity docs no longer disagree on test baseline, active priorities, or governance-file locations.

# 6. Verification Steps
- Run `pytest backend/python/tests/ -q` from repo root, or the documented pyenv command in `.ai/PROJECT_STATE.md:12-19` if that is the validated local path.
- Run targeted replay tests: `pytest backend/python/tests/test_replay_sync.py backend/python/tests/test_replay_timeline.py backend/python/tests/test_snapshot_replay_equivalence.py -q`.
- Run targeted runtime tests: `pytest backend/python/tests/test_runtime_supervisor.py backend/python/tests/test_recovery_manager.py backend/python/tests/test_session_cleanup.py -q`.
- Run the GUI locally with `./run_ivr_assessor.sh live-map-gui` and manually verify:
  1. Review workspace loads with no replay selected.
  2. Selecting a replay hydrates real summary/timeline/transcript data.
  3. Rapid stepping and scrubbing keep the cursor readable and the layout stable.
  4. Missing-media or missing-session cases show operator-safe fallback states.
  5. Export routes still return JSON, Mermaid, and Markdown when a graph exists.
- Verify doc consistency with `rg -n "296 passing|Quick Start|Replay Quick Start|Demo Quick Start|PLANS|TASKS|SESSION_LOGS" README.md backend/python/README.md backend/python/docs .ai`.

# 7. Risks & Mitigations
- **Risk:** `main.js` review renderers are currently mock-only and may overlap with new replay module ownership.
  - **Mitigation:** Make `replay.js` the loader/state owner and keep `main.js` as pure renderer for review DOM regions.
- **Risk:** Replay endpoints exist, but waveform/alignment paths are not currently wired through the GET dispatcher.
  - **Mitigation:** Add those paths in `live_map_gui.py` without renaming any existing replay routes.
- **Risk:** The user asked for IBM Plex consistency, but the stylesheet currently imports Inter in `main.css:1` and sets the global font in `main.css:1124-1125`.
  - **Mitigation:** Change typography tokens centrally instead of per-component overrides.
- **Risk:** Cleanup semantics are currently inconsistent with the desired idempotency contract; `test_session_cleanup.py` still expects `False` on the second call.
  - **Mitigation:** Decide the contract explicitly, update runtime code first, then update tests to lock it.
- **Risk:** `.ai` docs already contain stale counts and path references, so doc work can accidentally restate drift.
  - **Mitigation:** Treat `.ai/PROJECT_STATE.md` as the authority for baseline facts, then update all other continuity docs to match it.
