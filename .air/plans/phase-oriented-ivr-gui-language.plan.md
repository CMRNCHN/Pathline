# Goal
Realign IVRSuite’s GUI and product language around the operator workflow — **Suite Planning / Configuration**, **Live Operations / Active Run**, and **Review / Replay / Analysis** — without changing runtime topology, WebSocket protocol, replay semantics, or deterministic hot-path behavior.

# Approach
Use the existing server-rendered shell in `backend/python/src/ivr_assessor/frontend/templates/index.html:12-344`, the current polling/render loop in `backend/python/src/ivr_assessor/frontend/static/js/main.js:78-871`, and the two existing suite surfaces in `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:25-295` and `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:28-316` as the implementation anchors. The first increment stays frontend-only: relabel, reorder, and simplify existing surfaces so live operation centers on call-path supervision instead of subsystem visibility. A second, optional increment adds read-only backend summaries through the existing `/api/runtime-diagnostics` and `/api/runtime-metrics` endpoints in `backend/python/src/ivr_assessor/live_map_gui.py:302-365` and `backend/python/src/ivr_assessor/live_map_gui.py:657-662`, using additive diagnostics helpers in `backend/python/src/ivr_assessor/inspection.py:110-184`.

## Revised Information Architecture
1. **Suite Planning / Configuration**
   - Primary entry: planning modal launched from `backend/python/src/ivr_assessor/frontend/templates/index.html:210-267`.
   - Purpose: choose target, define route checks, seed starting DTMF path, configure reusable inputs, and decide whether the next run is route discovery or suite execution.
   - Supporting evidence: prior saved maps from `/api/maps` already available through `backend/python/src/ivr_assessor/frontend/static/js/common/api.js:21-27` and rendered from `backend/python/src/ivr_assessor/frontend/static/js/main.js:662-670`.
2. **Live Operations / Active Run**
   - Primary surface: the existing main console region in `backend/python/src/ivr_assessor/frontend/templates/index.html:36-207`.
   - Purpose: supervise one bounded run using prompt timeline, IVR state map, traversal logic state, response automation/manual response entry, and exception-first run notices.
   - Secondary details: runtime diagnostics stay collapsed in the drawer and do not compete with live supervision.
3. **Review / Replay / Analysis**
   - Primary entry: review button and drawer region in `backend/python/src/ivr_assessor/frontend/templates/index.html:179-207` with data already rendered from `backend/python/src/ivr_assessor/frontend/static/js/main.js:437-570`.
   - Purpose: reconstruct call path, inspect checkpoint verification outcomes, review artifacts, identify route refinement candidates, and extract reusable suites.
   - Technical diagnostics remain available, but behind review-oriented labels rather than as primary live navigation.

## Terminology Glossary
- **Route discovery** — bounded exploration of unknown IVR branches; aligns with the operational runbook in `backend/python/docs/OPERATIONS.md:24-31`.
- **Call-path mapping** — capturing prompts, actions, and transitions into the persisted IVR map already surfaced in `backend/python/src/ivr_assessor/frontend/templates/index.html:80-103` and `backend/python/src/ivr_assessor/frontend/static/js/main.js:212-283`.
- **Suite execution** — running a prepared route suite against a known flow; matches the run-suite flow in `backend/python/src/ivr_assessor/frontend/templates/index.html:278-344` and `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:158-308`.
- **Traversal logic** — the deterministic automation state currently exposed by the mode toggle in `backend/python/src/ivr_assessor/frontend/templates/index.html:113-121` and `backend/python/src/ivr_assessor/frontend/static/js/main.js:588-600`.
- **Response automation** — the system’s approved automatic response behavior during traversal; preferred over “autopilot” or agentic language.
- **Checkpoint verification** — evaluating each expected suite step/result, matching the run-suite detail model in `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:88-153`.
- **IVR state mapping** — the current graph-oriented live map already rendered in `backend/python/src/ivr_assessor/frontend/static/js/main.js:232-283`.
- **Prompt matching** — matching prompt text during suite planning and review, already represented in legacy planning triggers at `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:154-182`.
- **Response anchoring** — tying a DTMF or speech response to a prompt match or checkpoint expectation.
- **Route refinement** — using review evidence to adjust prompts, paths, or checkpoints for the next run.
- **Reusable suite extraction** — turning an observed route or reviewed outcome into a durable suite definition.
- **Disallowed language** — do not use “training the IVR,” “teaching the IVR,” chatbot framing, autonomous conversation framing, or agentic AI wording anywhere operator-facing.

## Current-Label Replacement Suggestions
- `Planning` in `backend/python/src/ivr_assessor/frontend/templates/index.html:28` → **Suite Planning** or **Plan Run**.
- `Suite Execution` in `backend/python/src/ivr_assessor/frontend/templates/index.html:29` → keep as **Suite Execution**, but pair it with checkpoint-focused supporting copy instead of subsystem wording.
- `Review` in `backend/python/src/ivr_assessor/frontend/templates/index.html:30` → **Review Run**.
- `Transcript Timeline` in `backend/python/src/ivr_assessor/frontend/templates/index.html:49-50` → **Active Run Timeline** or **Prompt Timeline**.
- `Live Caption` in `backend/python/src/ivr_assessor/frontend/templates/index.html:65-67` → **Active Prompt**.
- `Active Call-Path Map` / `IVR State Map` in `backend/python/src/ivr_assessor/frontend/templates/index.html:83-85` → keep `IVR State Map`; use supporting copy that emphasizes current route and route refinement.
- `Response Controls` in `backend/python/src/ivr_assessor/frontend/templates/index.html:108-109` → **Response Automation & Manual Response**.
- `Traversal Automation` in `backend/python/src/ivr_assessor/frontend/templates/index.html:116-119` → **Traversal Logic** with states **Automatic** / **Manual Override**.
- `Response Injection` in `backend/python/src/ivr_assessor/frontend/templates/index.html:123-130` → **Manual Response** or **Anchored Response**.
- `Run Notices` in `backend/python/src/ivr_assessor/frontend/templates/index.html:156-160` → **Run Alerts**.
- `Quick Tools` in `backend/python/src/ivr_assessor/frontend/templates/index.html:163-171` → **Review Shortcuts** or **Run Support**, and demote them visually during live mode.
- `Review & Diagnostics` in `backend/python/src/ivr_assessor/frontend/templates/index.html:181-183` → **Review / Replay / Analysis**.
- Drawer tabs in `backend/python/src/ivr_assessor/frontend/templates/index.html:191-197`:
  - `Diagnostics` → **Run Health**
  - `Run Reconstruction` → **Call-Path Replay**
  - `Stream Lifecycle` → **Technical Trace**
  - `Checkpoint Trace` → **Checkpoint Verification**
  - `Replay Artifacts` → **Evidence & Artifacts**
  - `Readiness` → **Run Readiness**
- `New Route Suite` in `backend/python/src/ivr_assessor/frontend/templates/index.html:220` → **New Planned Suite**.
- `Variable Inputs` in `backend/python/src/ivr_assessor/frontend/templates/index.html:236-248` → **Reusable Inputs**.
- `Data Row Import` in `backend/python/src/ivr_assessor/frontend/templates/index.html:249-256` → **Input Row Import**.
- `Route Checks` in `backend/python/src/ivr_assessor/frontend/templates/index.html:259-263` → keep as **Route Checks**.
- `Route Check Name` in `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:142-144` → **Checkpoint Group Name** or **Route Check Name** depending whether the suite is discovery-heavy or execution-heavy.
- `Prompt Match` / `Response / Variable` in `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:167-169` → **Prompt Match** / **Response Anchor**.
- `Saved Route Suites` in `backend/python/src/ivr_assessor/frontend/templates/index.html:289-299` → **Reusable Suites**.
- `Execution Events` in `backend/python/src/ivr_assessor/frontend/templates/index.html:315-318` → **Execution Timeline**.
- `Checkpoint Detail` in `backend/python/src/ivr_assessor/frontend/templates/index.html:322-326` → **Checkpoint Verification Detail**.
- `Suite Actions` in `backend/python/src/ivr_assessor/frontend/templates/index.html:332-337` → **Suite Management**.

## Phase-by-Phase UI Layout
### Suite Planning / Configuration
- Keep the existing modal shell in `backend/python/src/ivr_assessor/frontend/templates/index.html:210-267`, but reorganize it into four explicit blocks:
  1. **Run Scope** — target IVR, operating intent (route discovery vs suite execution copy only), and optional starting DTMF path.
  2. **Reusable Inputs** — existing variables/data-row import from `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:68-128`.
  3. **Route Checks** — existing case/trigger model from `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:130-217`, relabeled around prompt matching and response anchoring.
  4. **Evidence for Reuse** — optional summary of saved map availability and prior run context using existing maps fetch from `backend/python/src/ivr_assessor/frontend/static/js/main.js:662-670`.
- Keep saved suite schema unchanged; `cases`, `triggers`, `variables`, and `variable_labels` continue flowing through `backend/python/src/ivr_assessor/backend/routes/run_suite_routes.py:43-98`.

### Live Operations / Active Run
- Keep the existing shell in `backend/python/src/ivr_assessor/frontend/templates/index.html:36-207`, but make the live panel order unmistakable:
  1. **Run status / target / elapsed time** from `backend/python/src/ivr_assessor/frontend/static/js/main.js:165-193` and `backend/python/src/ivr_assessor/frontend/static/js/main.js:766-774`.
  2. **Prompt timeline** from `backend/python/src/ivr_assessor/frontend/static/js/main.js:78-210`.
  3. **IVR state map** from `backend/python/src/ivr_assessor/frontend/static/js/main.js:212-283`.
  4. **Traversal logic + manual response** from `backend/python/src/ivr_assessor/frontend/templates/index.html:113-153` and `backend/python/src/ivr_assessor/frontend/static/js/main.js:727-757`.
  5. **Run alerts** from `backend/python/src/ivr_assessor/frontend/static/js/main.js:383-419`.
- The drawer remains secondary and collapsed by default during active runs.

### Review / Replay / Analysis
- Reuse the current drawer in `backend/python/src/ivr_assessor/frontend/templates/index.html:179-207`, but reorder it around analysis first:
  1. **Call-Path Replay** — existing session chronology from `backend/python/src/ivr_assessor/frontend/static/js/main.js:483-499`.
  2. **Checkpoint Verification** — existing queue/checkpoint summary from `backend/python/src/ivr_assessor/frontend/static/js/main.js:518-537` plus suite-run checkpoint detail from `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:118-153`.
  3. **Evidence & Artifacts** — existing artifact summary from `backend/python/src/ivr_assessor/frontend/static/js/main.js:537-550`.
  4. **Route Refinement** — frontend-computed action items in the first increment; optional backend summary in the second increment.
  5. **Technical Trace / Run Health** — existing runtime and WebSocket diagnostics from `backend/python/src/ivr_assessor/frontend/static/js/main.js:461-517`, intentionally secondary.

## Live-Mode Simplification Strategy
- Preserve the exception-first heartbeat already present in `backend/python/src/ivr_assessor/frontend/static/js/main.js:285-381`, but rename cards around run risk and IVR progress rather than backend subsystem state.
- Remove `websocket` and `review` as first-class live timeline filters from `backend/python/src/ivr_assessor/frontend/templates/index.html:55-63` unless the user explicitly opens review/diagnostics; keep `Transcript`, `Responses`, `Traversal`, and `Notices` as the live-default filters.
- Keep `btn-open-runtime`, `btn-open-artifacts`, and `btn-open-smoke` in `backend/python/src/ivr_assessor/frontend/templates/index.html:165-168`, but visually demote them behind a “Review Shortcuts” grouping so they no longer read as primary live actions.
- Keep the drawer closed while `AppState.callRunning` is true unless the operator explicitly opens review or run health from `backend/python/src/ivr_assessor/frontend/static/js/main.js:759-764`.
- Do not surface storage counts, lifecycle counters, or artifact directories in the main live workspace; those stay in review/technical tabs only.

## Review-Mode Analysis Strategy
- Reframe review around three operator questions using data already built in `backend/python/src/ivr_assessor/inspection.py:16-184` and rendered in `backend/python/src/ivr_assessor/frontend/static/js/main.js:437-570`:
  1. **What route did the IVR actually take?**
  2. **Which checkpoints verified, failed, or timed out?**
  3. **What should change before the next run?**
- Frontend-only increment: compute review callouts from existing chronology, queue visibility, artifact counts, and graph node totals.
- Backend-supported increment: add additive review summaries such as prompt-match count, action count, terminal/dead-end markers, and route refinement hints via `backend/python/src/ivr_assessor/inspection.py:110-184`, surfaced through the same `/api/runtime-diagnostics` endpoint in `backend/python/src/ivr_assessor/live_map_gui.py:360-365`.
- Keep replay deterministic: summaries may interpret existing evidence, but they must not alter replay generation, chronology ordering, or stored artifacts.

## Planning-Mode Configuration Strategy
- Keep the planning entry in `backend/python/src/ivr_assessor/frontend/templates/index.html:210-267`, but change the mental model from “test suite editor” to “plan the next bounded IVR run.”
- Preserve the current save/run flow in `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:221-257`, but rename validations and buttons so the operator is saving a reusable suite and optionally starting suite execution.
- Add lightweight planning aids without schema changes:
  - show prior map availability for the entered target using the existing maps fetch in `backend/python/src/ivr_assessor/frontend/static/js/main.js:662-670`
  - show route-check counts and prompt-match counts per saved suite using data already returned by `/api/suites` in `backend/python/src/ivr_assessor/backend/routes/run_suite_routes.py:43-52`
  - preserve the saved JSON payload and validation path in `backend/python/src/ivr_assessor/backend/routes/run_suite_routes.py:55-65`
- Do not add new planning abstractions, hidden state machines, or new suite-schema dependencies.

## Frontend-Only Opportunities
- Relabel the shell, toolbar, modal, and drawer copy in `backend/python/src/ivr_assessor/frontend/templates/index.html:12-344`.
- Reorder live emphasis and collapse review surfaces through `backend/python/src/ivr_assessor/frontend/static/js/main.js:195-580` without changing poll intervals at `backend/python/src/ivr_assessor/frontend/static/js/main.js:863-870`.
- Rename and regroup suite-planning fields in `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:68-217` while preserving current `cases/triggers` data shape.
- Rename run-suite detail and event language in `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:88-245` to checkpoint verification / reusable suite language.
- Adjust CSS emphasis only in `backend/python/src/ivr_assessor/frontend/static/css/main.css` and `backend/python/src/ivr_assessor/frontend/static/css/run_suites.css` so review/diagnostic affordances stay visually secondary during live mode.
- Align documentation language in `backend/python/docs/OPERATIONS.md:16-109` and `README.md:12-26` so the product narrative matches the GUI.

## Backend-Supported Opportunities
- Add additive review summaries to `backend/python/src/ivr_assessor/inspection.py:110-184`, such as:
  - prompt count vs action count
  - last matched prompt / last anchored response
  - potential dead-end route markers
  - route refinement cues based on missing action after prompt or repeated prompts
- Surface those additive summaries through the existing diagnostics payload builder in `backend/python/src/ivr_assessor/live_map_gui.py:360-365` and keep endpoint paths unchanged in `backend/python/src/ivr_assessor/live_map_gui.py:657-662`.
- Optionally enrich suite-execution list/detail payloads in `backend/python/src/ivr_assessor/backend/routes/run_suite_routes.py:102-155` with additive metadata already derivable from stored suites (for example scenario totals, last-updated timestamps, or suite descriptions), without changing run semantics or requiring new WebSocket events.
- Optionally expose a compact map-summary view through the existing `/api/maps` payload path in `backend/python/src/ivr_assessor/backend/routes/mapper_routes.py:60-66` if the frontend needs explicit counts for planning; keep the endpoint and saved map shape backward-compatible.

# File Changes
- **Modify** `backend/python/src/ivr_assessor/frontend/templates/index.html:12-344` — relabel phase entry points, reorder live/review emphasis, and restructure modal/drawer copy around operator phases while keeping the same DOM topology and script includes.
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/main.js:78-871` — rename live/review labels, simplify live filters, keep review secondary during active runs, and render review-first analysis sections from the same polled payloads.
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:25-295` — convert the legacy suite editor’s operator-facing language from “test suite / trigger” framing to planning, route-check, prompt-match, and response-anchor framing without changing persisted schema.
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:28-316` — relabel run-suite surfaces around suite execution, checkpoint verification, reusable suites, and execution evidence.
- **Modify** `backend/python/src/ivr_assessor/frontend/static/css/main.css` — visually demote diagnostics in live mode and reinforce the three-phase IA without introducing new layout frameworks.
- **Modify** `backend/python/src/ivr_assessor/frontend/static/css/run_suites.css` — align the suite execution modal’s visual hierarchy with checkpoint verification and review language.
- **Modify** `backend/python/src/ivr_assessor/inspection.py:110-184` — optional additive review summaries for route refinement and reusable suite extraction; no replay semantic changes.
- **Modify** `backend/python/src/ivr_assessor/live_map_gui.py:302-365` and `backend/python/src/ivr_assessor/live_map_gui.py:657-662` — optional additive diagnostics payload fields only; no new routes, no poll cadence changes, no protocol changes.
- **Modify** `backend/python/src/ivr_assessor/backend/routes/run_suite_routes.py:102-155` — optional additive suite metadata for planning/review support while keeping current import/export/run behavior intact.
- **Modify** `backend/python/src/ivr_assessor/backend/routes/mapper_routes.py:60-66` — optional additive map summaries if planning needs explicit saved-map counts; keep current API contracts backward-compatible.
- **Modify** `backend/python/docs/OPERATIONS.md:16-109` — keep operator runbook aligned with the new phase-first IA and glossary.
- **Modify** `README.md:12-26` — keep top-level product language aligned with the GUI phase model.

# Implementation Steps
## Task 1: Establish the phase-first shell and language baseline
1. Update `backend/python/src/ivr_assessor/frontend/templates/index.html:12-33` so the header buttons and status copy clearly represent planning, live operations, and review rather than generic subsystem entry points.
2. Update `backend/python/src/ivr_assessor/frontend/templates/index.html:179-207` so the drawer title and tab labels use review-first IVR language.
3. Update `backend/python/docs/OPERATIONS.md:16-109` and `README.md:12-26` to match the GUI terminology and explicitly ban training/chatbot wording in operator-facing guidance.

## Task 2: Reframe planning as bounded IVR configuration
4. Update `backend/python/src/ivr_assessor/frontend/templates/index.html:210-267` to group the planning modal into run scope, reusable inputs, route checks, and prior-evidence support.
5. Update `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:68-217` so labels, placeholders, and validation messages speak in terms of route discovery, prompt matching, response anchoring, starting DTMF path, and reusable inputs while preserving the current suite JSON schema.
6. Optionally use existing `/api/maps` data from `backend/python/src/ivr_assessor/frontend/static/js/main.js:662-670` to show whether the entered target already has saved IVR state mapping, without adding a new endpoint.

## Task 3: Simplify live mode around one active run
7. Update `backend/python/src/ivr_assessor/frontend/templates/index.html:45-177` so the default visual order is prompt timeline → IVR state map → traversal logic/manual response → run alerts.
8. Update `backend/python/src/ivr_assessor/frontend/static/js/main.js:78-283` to rename timeline badges, empty states, graph meta, and action text with IVR-native terminology.
9. Update `backend/python/src/ivr_assessor/frontend/static/js/main.js:285-419` so heartbeat and control-status cards emphasize run health, prompt flow, queue/intervention state, and checkpoint visibility instead of raw subsystem language.
10. Update `backend/python/src/ivr_assessor/frontend/static/js/main.js:759-865` so the review drawer remains closed by default during active runs and technical tabs only surface when explicitly requested.
11. Adjust `backend/python/src/ivr_assessor/frontend/static/css/main.css` to visually subordinate review shortcuts and technical diagnostics during live mode.

## Task 4: Reframe review as route refinement and reusable-suite extraction
12. Update `backend/python/src/ivr_assessor/frontend/static/js/main.js:437-570` to render review tabs in this order: call-path replay, checkpoint verification, evidence/artifacts, route refinement, and technical trace.
13. Update `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:88-245` so suite execution language centers on checkpoint verification, execution evidence, and reusable suite management.
14. Update `backend/python/src/ivr_assessor/frontend/static/css/run_suites.css` so suite-execution detail, verification outcomes, and review evidence have clear hierarchy without introducing a new layout system.

## Task 5: Optional additive backend summaries for richer review
15. Extend `backend/python/src/ivr_assessor/inspection.py:110-184` with additive route-analysis summaries derived from existing chronology and session snapshot data.
16. Surface those summaries through `backend/python/src/ivr_assessor/live_map_gui.py:360-365` and preserve the same GET routes in `backend/python/src/ivr_assessor/live_map_gui.py:657-662`.
17. If the planning or review surfaces need richer suite/map metadata, add backward-compatible summary fields in `backend/python/src/ivr_assessor/backend/routes/run_suite_routes.py:102-155` and `backend/python/src/ivr_assessor/backend/routes/mapper_routes.py:60-66` rather than creating new topology or protocol paths.

# Acceptance Criteria
- The primary operator entry points in `backend/python/src/ivr_assessor/frontend/templates/index.html:26-33` are clearly organized as **Suite Planning / Configuration**, **Live Operations / Active Run**, and **Review / Replay / Analysis**.
- No operator-facing copy in the touched GUI or docs uses “training the IVR,” “teaching the IVR,” chatbot framing, or autonomous AI conversation framing.
- The planning surface in `backend/python/src/ivr_assessor/frontend/templates/index.html:210-267` and `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:68-257` uses IVR-native terms such as route discovery, route checks, prompt matching, response anchoring, checkpoint verification, reusable inputs, and starting DTMF path.
- The live workspace in `backend/python/src/ivr_assessor/frontend/templates/index.html:45-177` and `backend/python/src/ivr_assessor/frontend/static/js/main.js:195-419` prioritizes prompt timeline, IVR state map, traversal logic, manual response, and run alerts; raw stream lifecycle and artifact counts are not primary live controls.
- The review surface in `backend/python/src/ivr_assessor/frontend/static/js/main.js:437-570` supports run reconstruction, checkpoint verification, evidence/artifacts, and route refinement using the existing diagnostics payloads; if backend summaries are added, they are additive fields only.
- Persisted suite schemas saved through `backend/python/src/ivr_assessor/backend/routes/run_suite_routes.py:55-65` and imported/exported through `backend/python/src/ivr_assessor/backend/routes/run_suite_routes.py:116-166` remain backward-compatible.
- Existing runtime endpoints in `backend/python/src/ivr_assessor/live_map_gui.py:657-662`, poll cadence in `backend/python/src/ivr_assessor/frontend/static/js/main.js:863-870`, and deterministic runtime behavior described in `backend/python/docs/OPERATIONS.md:39-84` remain unchanged.
- The implementation does not change WebSocket protocol, replay semantics, or hot-path routing/audio behavior.

# Verification Steps
- Run syntax checks for the touched frontend files:
  - `node --check backend/python/src/ivr_assessor/frontend/static/js/main.js`
  - `node --check backend/python/src/ivr_assessor/frontend/static/js/run_suites.js`
  - `node --check backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js`
- Run targeted backend tests for unchanged contracts and additive diagnostics behavior:
  - `/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/test_live_map_gui.py backend/python/tests/test_inspection.py -q`
  - If backend-supported review summaries are added, also run `/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/test_replay_mode.py backend/python/tests/test_cli_smoke.py -q`
- Manual verification in the GUI:
  1. Open the live GUI and confirm the three phase entry points read as planning, live operations, and review.
  2. Start a bounded run and verify the drawer stays secondary while prompt timeline, IVR state map, traversal logic, and manual response remain primary.
  3. Open planning and confirm route-check / prompt-match / response-anchor language appears without schema changes.
  4. Open review after a run and confirm call-path replay, checkpoint verification, and route refinement are easier to find than technical diagnostics.
- Regression check terminology:
  - Search touched frontend/docs files for banned language (`training`, `teaching`, `chatbot`, `agent`, `conversation`) and confirm operator-facing copies no longer use them inappropriately.

# Risks & Mitigations
- **Risk: legacy and new suite surfaces drift apart.** `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:25-295` and `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:28-316` currently express adjacent workflows differently. **Mitigation:** update both surfaces in the same increment and use the same glossary for checkpoint, prompt match, response anchor, and reusable suite wording.
- **Risk: live-mode simplification accidentally hides needed operational safety signals.** The current live console combines heartbeat, control status, and diagnostics from `backend/python/src/ivr_assessor/frontend/static/js/main.js:285-570`. **Mitigation:** keep exception-first alerts, queue visibility, and manual override prominent; only demote storage/lifecycle detail.
- **Risk: copy changes imply new schema or run behavior.** The planning editor in `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:188-257` persists the current suite payload. **Mitigation:** treat the first increment as relabeling/reordering only and keep validation/schema paths unchanged.
- **Risk: backend-supported review summaries are mistaken for runtime control logic.** Diagnostics are built in `backend/python/src/ivr_assessor/inspection.py:110-184`. **Mitigation:** keep all new backend work read-only, additive, and under the existing diagnostics endpoints.
- **Risk: scope crosses frontend and backend and exceeds the repo’s refactor guardrails.** This work touches more than three files and potentially crosses domains. **Mitigation:** implement in two approved slices: (1) frontend/docs-only IA and terminology pass, then (2) optional backend-supported additive summaries after explicit confirmation.
- **Risk: technical tabs retain subsystem-first wording through overlooked strings.** Labels currently live in both template and render functions across `backend/python/src/ivr_assessor/frontend/templates/index.html:45-344` and `backend/python/src/ivr_assessor/frontend/static/js/main.js:87-570`. **Mitigation:** perform a final terminology sweep after implementation, not just a visual pass.