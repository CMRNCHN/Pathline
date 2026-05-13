## 1. Goal

Align IVRSuite’s product language and GUI workflow with its actual purpose: deterministic IVR route discovery, call-path mapping, suite execution, checkpoint verification, and post-run route refinement—not adaptive conversational AI or agentic IVR behavior.

## 2. Approach

Keep the current local-first operator console and vanilla frontend intact, then refine information architecture, labels, and visibility rules inside the existing HTML/JS/CSS surfaces. This avoids frontend rewrites, protocol changes, replay semantic changes, and hot-path changes while making the operator workflow clearer. The main design decision is to express the product as three operational phases—Planning, Live Operations, Review—while preserving existing endpoints such as `/api/status`, `/api/runtime-metrics`, `/api/runtime-diagnostics`, `/api/run-suites`, `/api/inject-dtmf`, and `/api/inject-voice`.

## 3. Revised Product Language Glossary

Preferred terms to standardize across UI/docs:

- **Route discovery**: Automated or assisted traversal of unknown IVR branches to identify reachable prompts and choices.
- **Call-path mapping**: Turning prompts, selections, transfers, loops, and terminal states into an IVR map.
- **Suite execution**: Running repeatable scripted checks against known IVR routes.
- **Traversal logic**: Deterministic rules for selecting the next DTMF or speech response.
- **Response automation**: Preconfigured DTMF/speech actions triggered by prompt matches or call-path conditions.
- **Checkpoint verification**: Confirming expected prompts, events, transfers, outcomes, or terminal states during a run.
- **IVR state mapping**: Converting transcript events into stable nodes and branches.
- **Prompt matching**: Matching recognized IVR speech to known prompts, expected text, or route conditions.
- **Response anchoring**: Attaching an operator-approved response to a known prompt/state so it can be reused.
- **Route refinement**: Post-run cleanup of nodes, prompt labels, branches, timing, retries, and terminal outcomes.
- **Reusable suite extraction**: Converting a successful traversal path into a repeatable suite or scenario.

Terms to avoid or replace:

- “Auto-pilot” → “Traversal Automation” or “Automated Traversal”. Observed in `backend/python/src/ivr_assessor/frontend/templates/index.html:115-118` and `backend/python/src/ivr_assessor/frontend/static/js/main.js:558-570`.
- “Voice Action” where it implies conversational behavior → “Speech Response” or “Speech Injection”. Observed in `backend/python/src/ivr_assessor/frontend/static/js/main.js:100-103`.
- “Reply” → “Response” or “Response Value”. Observed in `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:166-168`.
- “Trigger” → “Prompt Match” or “Response Rule”. Observed in `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:153-181`.
- “Test Cases” → “Call-Path Checks” or “Route Checks”. Observed in `backend/python/src/ivr_assessor/frontend/templates/index.html:258-260`.
- “Initial Path” → “Starting DTMF Path”. Observed in `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:146-150`.
- “Runtime Drawer” → “Diagnostics Drawer” or “Operational Diagnostics”. Observed in `backend/python/src/ivr_assessor/frontend/templates/index.html:162-168`.
- “Smoke Check” → “Readiness Check”. Observed in `backend/python/src/ivr_assessor/frontend/templates/index.html:162-168` and diagnostics rendering in `backend/python/src/ivr_assessor/frontend/static/js/main.js:521-536`.
- “AI Voice Generation” → “TTS Response Audio”. Observed in `README.md:14` and `README.md:80-83`.

## 4. Proposed Phase-Oriented UI Structure

### Phase 1: Suite Planning / Configuration

Primary operator question: “What reusable traversal actions and route checks should be available before a run?”

Recommended surfaces:

- Rename **Suite Editor** to **Planning** or **Suite Planning** in `backend/python/src/ivr_assessor/frontend/templates/index.html:28-30`.
- Rename the current test suite modal from **Test Suites** to **Suite Planning** in `backend/python/src/ivr_assessor/frontend/templates/index.html:209-263`.
- Group editor fields into visible blocks: **Suite Target**, **Variable Inputs**, **Response Action Library**, **Route Checks**, and **Data Row Import**.
- Change variable examples from card-specific defaults toward reusable IVR inputs such as `account_number`, `phone_number`, `zip_code`, and `case_id`; current defaults are card-oriented in `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:8-17`.
- Rename trigger editing copy: **Title** → **Action Name**, **IVR says…** → **Prompt Match**, **Reply (or $variable)** → **Response / Variable**, **+ Add Trigger** → **+ Add Prompt Match** in `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:160-179`.

### Phase 2: Live Operations / Active Run

Primary operator question: “What is happening in the call path right now, and what action can I take?”

Recommended surfaces:

- Keep the transcript/timeline as the source-of-truth center, currently rendered in `backend/python/src/ivr_assessor/frontend/templates/index.html:45-76` and `backend/python/src/ivr_assessor/frontend/static/js/main.js:78-209`.
- Rename **Active Session / Session Timeline** to **Live Operations / Transcript Timeline** in `backend/python/src/ivr_assessor/frontend/templates/index.html:46-51`.
- Rename **Contextual Map / IVR Graph** to **Active Call-Path Map / IVR State Map** in `backend/python/src/ivr_assessor/frontend/templates/index.html:79-101`.
- Rename **Control Bench** to **Response Controls** or **Operator Actions** in `backend/python/src/ivr_assessor/frontend/templates/index.html:104-171`.
- Replace **Mode: Auto-pilot** with **Traversal Automation: On/Off** in `backend/python/src/ivr_assessor/frontend/templates/index.html:113-119` and `backend/python/src/ivr_assessor/frontend/static/js/main.js:558-570`.
- Keep manual DTMF/speech injection via existing `/api/inject-dtmf` and `/api/inject-voice` calls in `backend/python/src/ivr_assessor/frontend/static/js/common/api.js:29-33`; change labels only.
- Convert the always-visible heartbeat strip in `backend/python/src/ivr_assessor/frontend/templates/index.html:36-43` and `backend/python/src/ivr_assessor/frontend/static/js/main.js:285-350` into exception-first cards: show **Warnings**, **Failures**, **Degraded**, and **Intervention Needed** when relevant; otherwise collapse to a compact “Operational status: nominal” summary.

### Phase 3: Review / Replay / Analysis

Primary operator question: “How do I turn this raw run into a clean IVR map and reusable suites?”

Recommended surfaces:

- Rename **Inspect** to **Review** in `backend/python/src/ivr_assessor/frontend/templates/index.html:28-31`.
- Rename **Inspection Drawer** to **Review & Diagnostics** or split copy into **Run Review** plus expandable **Diagnostics** in `backend/python/src/ivr_assessor/frontend/templates/index.html:178-206`.
- Rename drawer tabs: **Session** → **Run Reconstruction**, **Artifacts** → **Replay Artifacts**, **Queue / Checkpoints** → **Checkpoint Trace**, **Smoke** → **Readiness**, while keeping the same tab mechanics in `backend/python/src/ivr_assessor/frontend/static/js/main.js:407-540`.
- Use existing replay/runtime diagnostics payloads from `backend/python/src/ivr_assessor/frontend/static/js/common/api.js:24-26` to describe review concepts without changing semantics.
- Present analysis tasks as future visible actions: relabel prompts, merge duplicate prompts, classify routes, identify failed traversal paths, refine timing/retry rules, convert constants to variables, and extract reusable suites from successful paths.

## 5. Recommended Navigation Model

Use a simple three-tab top-level model inside the existing header—no router, no build step, no SPA rewrite:

- **Planning**: Opens the existing suite editor modal with revised labels and configuration grouping.
- **Live Run**: Default console view with transcript, active IVR state map, response controls, and exception-based status.
- **Review**: Opens the existing drawer/modal area focused on run reconstruction, replay artifacts, route refinement, and diagnostics.

Implementation guardrails:

- Keep DOM-driven vanilla JS event handlers already present in `backend/python/src/ivr_assessor/frontend/static/js/main.js:746-841` and `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:304-315`.
- Do not add routing, client-side state libraries, frontend frameworks, or generated assets.
- Do not change backend routes listed in `backend/python/src/ivr_assessor/frontend/static/js/common/api.js:19-49`.
- Diagnostics remain expandable and read-only; they should not compete with transcript and map during live operation.

## 6. Feature Grouping by Operational Phase

### Planning / Configuration

- Response action library: DTMF, speech response, wait, transfer request, escalation phrase, hang-up condition.
- Prompt matching: prompt text contains, expected event, expected node, expected transfer, prompt confidence.
- Variable inputs: `{{account_number}}`, `{{phone_number}}`, `{{zip_code}}`, `{{case_id}}`, with compatibility notes for existing `$variable` behavior if implementation keeps current syntax.
- Route checks: checkpoint verification, retry logic, timeout windows, expected terminal outcomes.
- Suite import/export: keep existing JSON import/export in `backend/python/src/ivr_assessor/frontend/templates/index.html:277-341` and `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:256-300`.

### Live Operations / Active Run

- Transcript timeline: prompt events, response injections, route decisions, transfers, loops, dead ends.
- Active IVR map: prompts as nodes, selections as branches, transfers as transitions, loops as recursive branches, terminal states as dead ends/endpoints.
- Inline operator tooling: DTMF keypad, speech injection, traversal automation toggle, branch save/tag controls as future additive UI.
- Assisted traversal suggestions: label as deterministic suggestions based on discovered branches or suite rules, never as autonomous conversation.
- Exception-based health: warnings, failures, degraded services, intervention requests; full subsystem telemetry only behind expanded diagnostics.

### Review / Replay / Analysis

- Run reconstruction: post-run transcript and event chronology, current `session.chronology` display in `backend/python/src/ivr_assessor/frontend/static/js/main.js:453-468`.
- Replay inspection: artifacts, recordings, snapshots, reports currently surfaced in `backend/python/src/ivr_assessor/frontend/static/js/main.js:507-520`.
- Route refinement: prompt relabeling, duplicate prompt merge, route classification, terminal/dead-end marking.
- Suite extraction: convert successful traversal paths into reusable suites; convert static responses into variables.
- Failure analysis: failed traversal path identification, retry/timing refinement, unresolved branches.

## 7. Terminology Replacement Map for Current UI Labels

- `Operator Console` → `IVR Operations Console` in `backend/python/src/ivr_assessor/frontend/templates/index.html:12-18`.
- `Target Session` → `Target Number` or `Target IVR` in `backend/python/src/ivr_assessor/frontend/templates/index.html:21-24`.
- `Run Suites` → `Suite Execution` in `backend/python/src/ivr_assessor/frontend/templates/index.html:26-33` and run suite modal labels in `backend/python/src/ivr_assessor/frontend/templates/index.html:277-341`.
- `Suite Editor` → `Suite Planning` in `backend/python/src/ivr_assessor/frontend/templates/index.html:28-30`.
- `Inspect` → `Review` in `backend/python/src/ivr_assessor/frontend/templates/index.html:28-31`.
- `Active Session` → `Live Operations` in `backend/python/src/ivr_assessor/frontend/templates/index.html:46-51`.
- `Session Timeline` → `Transcript Timeline` in `backend/python/src/ivr_assessor/frontend/templates/index.html:46-51`.
- `Routing` filter → `Traversal` or `Responses` in `backend/python/src/ivr_assessor/frontend/templates/index.html:55-62` and `backend/python/src/ivr_assessor/frontend/static/js/main.js:60-69`.
- `Replay` filter → `Review` or `Artifacts` depending on context in `backend/python/src/ivr_assessor/frontend/templates/index.html:55-62`.
- `Contextual Map` → `Active Call-Path Map` in `backend/python/src/ivr_assessor/frontend/templates/index.html:79-86`.
- `IVR Graph` → `IVR State Map` in `backend/python/src/ivr_assessor/frontend/templates/index.html:79-86`.
- `Control Bench` → `Response Controls` in `backend/python/src/ivr_assessor/frontend/templates/index.html:104-109`.
- `Manual Input` → `Response Injection` in `backend/python/src/ivr_assessor/frontend/templates/index.html:122-129`.
- `Enter DTMF or text…` → `Enter DTMF or speech response…` in `backend/python/src/ivr_assessor/frontend/templates/index.html:122-129`.
- `Session Signals` → `Run Notices` in `backend/python/src/ivr_assessor/frontend/templates/index.html:155-160`.
- `Runtime Drawer` → `Diagnostics` in `backend/python/src/ivr_assessor/frontend/templates/index.html:162-168`.
- `Smoke Check` / `Smoke` → `Readiness Check` / `Readiness` in `backend/python/src/ivr_assessor/frontend/templates/index.html:162-197`.
- `Test Cases` → `Route Checks` in `backend/python/src/ivr_assessor/frontend/templates/index.html:258-260`.
- `Live Events` → `Execution Events` in `backend/python/src/ivr_assessor/frontend/templates/index.html:314-317`.
- `Step Detail` → `Checkpoint Detail` in `backend/python/src/ivr_assessor/frontend/templates/index.html:320-325`.
- `Step ID` → `Checkpoint ID` in `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:118-141` if the underlying suite step remains a checkpoint-style check.
- `expects:` → `verifies:` in `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:99-101`.

## 8. File Changes for a Future Implementation Pass

### Modify: `README.md`

- Replace product positioning around “AI Voice Generation” with “TTS Response Audio” and emphasize local-first IVR route discovery, call-path automation, suite execution, and route refinement.
- Keep OpenAI references only where technically accurate for optional TTS configuration.

### Modify: `backend/python/src/ivr_assessor/frontend/templates/index.html`

- Update static labels for header navigation, phase names, live transcript, active map, response controls, diagnostics/review drawer, suite planning modal, and suite execution modal.
- Reorder wording only; do not add new script dependencies, endpoints, framework constructs, or new templates.

### Modify: `backend/python/src/ivr_assessor/frontend/static/js/main.js`

- Update dynamic labels emitted by timeline rows, heartbeat cards, graph metadata, control status, drawer sections, and mode toggle.
- Implement exception-first live status rendering using existing `AppState.runtimeMetrics`, `AppState.runtimeDiagnostics`, and `AppState.diagnose` fields; do not change polling intervals, API payloads, or websocket semantics.
- Keep `renderOperatorConsole()` and existing event handlers intact.

### Modify: `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js`

- Update suite editor copy from triggers/cases/replies toward prompt matches, route checks, responses, and variables.
- Update default variable labels/examples toward IVR operations examples while preserving current data model shape unless a later explicit migration is requested.

### Modify: `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js`

- Update run suite copy from generic step/test wording toward suite execution, checkpoint verification, execution events, and route checks.
- Keep polling mechanics, event names from `RUN_EVENTS`, and import/export behavior unchanged.

### Modify: `backend/python/src/ivr_assessor/frontend/static/css/main.css`

- Only adjust spacing/visibility if needed for phase navigation and collapsed diagnostics; no visual system rewrite.
- Preserve current graphite/slate system described in `.ai/HANDOFF.md`.

### Modify: `backend/python/src/ivr_assessor/frontend/static/css/run_suites.css`

- Only adjust labels/group presentation if modal grouping requires minor layout tweaks; no build step or framework.

## 9. Implementation Steps for a Future Pass

### Task 1: Product language pass

1. In `README.md`, replace the feature wording at `README.md:11-15` so it describes route discovery, call-path mapping, suite execution, and TTS response audio.
2. In `README.md`, update voice generation wording at `README.md:80-83` from product-facing AI language to optional TTS response audio.
3. In `backend/python/src/ivr_assessor/frontend/templates/index.html`, update header and nav labels at `backend/python/src/ivr_assessor/frontend/templates/index.html:12-33` to `IVR Operations Console`, `Target IVR`, `Planning`, `Suite Execution`, `Review`, `End Run`, and `Start Call` or `Start Run`.

### Task 2: Phase-oriented shell labels

1. In `backend/python/src/ivr_assessor/frontend/templates/index.html`, update live timeline copy at `backend/python/src/ivr_assessor/frontend/templates/index.html:45-76` to `Live Operations`, `Transcript Timeline`, and transcript-source-of-truth empty states.
2. In `backend/python/src/ivr_assessor/frontend/templates/index.html`, update map copy at `backend/python/src/ivr_assessor/frontend/templates/index.html:78-102` to `Active Call-Path Map` and `IVR State Map`.
3. In `backend/python/src/ivr_assessor/frontend/templates/index.html`, update operator controls copy at `backend/python/src/ivr_assessor/frontend/templates/index.html:104-171` to `Response Controls`, `Traversal Automation`, `Response Injection`, `Run Notices`, and `Operational Diagnostics`.

### Task 3: Live-mode simplification

1. In `backend/python/src/ivr_assessor/frontend/static/js/main.js`, rename timeline routing labels in `classifyTimelineEntry()`, `formatActionText()`, and `buildTimelineRows()` at `backend/python/src/ivr_assessor/frontend/static/js/main.js:60-118` to transcript, response, traversal, review artifact, and operational notice language.
2. In `backend/python/src/ivr_assessor/frontend/static/js/main.js`, revise graph language at `backend/python/src/ivr_assessor/frontend/static/js/main.js:212-282` from generic graph confidence to prompt matching / branch observations where appropriate.
3. In `backend/python/src/ivr_assessor/frontend/static/js/main.js`, replace heartbeat cards at `backend/python/src/ivr_assessor/frontend/static/js/main.js:285-350` with exception-first status: show failures/warnings/degraded/intervention states when present; otherwise show compact nominal status and target/run metadata.
4. In `backend/python/src/ivr_assessor/frontend/static/js/main.js`, rename mode toggle output at `backend/python/src/ivr_assessor/frontend/static/js/main.js:558-570` from `Auto-pilot` to `Traversal Automation` with `On`/`Manual Override` semantics.

### Task 4: Planning-mode configuration language

1. In `backend/python/src/ivr_assessor/frontend/templates/index.html`, update suite planning modal labels at `backend/python/src/ivr_assessor/frontend/templates/index.html:209-263` to `Suite Planning`, `New Route Suite`, `Route Checks`, `Variable Inputs`, and `Data Row Import`.
2. In `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js`, revise default variable labels at `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:8-17` toward `account_number`, `phone_number`, `zip_code`, and `case_id` examples if backward compatibility is acceptable for new suites.
3. In `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js`, replace trigger/case labels at `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:129-181` with `Route Check`, `Starting DTMF Path`, `Prompt Match`, `Response`, and `+ Add Prompt Match`.
4. Preserve saved suite schema handling in `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:187-245`; do not migrate persisted files without a separate plan.

### Task 5: Review/replay/analysis language

1. In `backend/python/src/ivr_assessor/frontend/templates/index.html`, update drawer labels at `backend/python/src/ivr_assessor/frontend/templates/index.html:178-206` to make diagnostics expandable under review instead of primary live telemetry.
2. In `backend/python/src/ivr_assessor/frontend/static/js/main.js`, update drawer section labels at `backend/python/src/ivr_assessor/frontend/static/js/main.js:431-536` to `Run Reconstruction`, `Checkpoint Trace`, `Replay Artifacts`, `Operational Readiness`, and `Actionable Issues`.
3. In `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js`, update suite execution labels at `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:88-154` and `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:191-245` from step/test copy to route check/checkpoint verification copy.

### Task 6: Minimal CSS support

1. In `backend/python/src/ivr_assessor/frontend/static/css/main.css`, add or adjust classes only if needed to support a compact exception-first live status and phase navigation labels.
2. In `backend/python/src/ivr_assessor/frontend/static/css/run_suites.css`, adjust modal group headings only if revised planning/execution labels wrap poorly.
3. Do not change layout topology, add a build step, or introduce a new visual system.

## 10. Acceptance Criteria

- Product-facing UI no longer uses `Auto-pilot`, `Reply`, `Trigger`, `Test Cases`, `Smoke Check`, or broad “AI” positioning where IVR operations language is more accurate.
- Header navigation clearly exposes the three phases: Planning, Live Run, and Review.
- Live mode keeps the transcript timeline as the primary center panel and the IVR map as the primary contextual side panel.
- Live mode does not permanently show full subsystem telemetry; detailed runtime/websocket/queue/readiness data remains collapsed or drawer-based unless warning/error/degraded conditions are present.
- Suite planning language explicitly supports response actions, DTMF sequences, speech responses, wait/retry conditions, prompt matching, transfer/escalation/hang-up concepts, and variable inputs.
- Suite execution language describes route checks, checkpoint verification, execution events, pass/fail/timeout outcomes, and expected prompts/events.
- Review language describes run reconstruction, replay artifacts, route refinement, prompt relabeling, duplicate prompt merging, failed path analysis, timing/retry refinement, and reusable suite extraction.
- Existing API routes and polling behavior in `backend/python/src/ivr_assessor/frontend/static/js/common/api.js:19-49` remain unchanged.
- No websocket protocol, replay semantics, topology, backend framework, frontend framework, or hot-path behavior changes are introduced.
- `rg -n "Auto-pilot|teaching|training the IVR|conversational adaptation|chatbot|autonomous AI conversation|agentic IVR reasoning" README.md backend/python/src/ivr_assessor/frontend` returns no product-facing matches after implementation, except any explicitly documented internal/API terms that are technically necessary.

## 11. Verification Steps

Because this pass is planning-only, do not run tests or modify files now. For a future implementation pass:

1. Run syntax checks:
   - `node --check backend/python/src/ivr_assessor/frontend/static/js/main.js`
   - `node --check backend/python/src/ivr_assessor/frontend/static/js/run_suites.js`
   - `node --check backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js`
2. Run targeted backend GUI tests if labels or route expectations are covered:
   - `/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/test_live_map_gui.py -q`
   - `/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/test_inspection.py -q`
3. Run terminology checks:
   - `rg -n "Auto-pilot|Reply \(or|\+ Add Trigger|Test Cases|Smoke Check|AI Voice Generation" README.md backend/python/src/ivr_assessor/frontend`
   - `rg -n "training the IVR|teaching the IVR|conversational adaptation|chatbot behavior|autonomous AI conversation|agentic IVR reasoning" README.md backend/python/src/ivr_assessor/frontend`
4. Manual browser verification:
   - Open the GUI with `./run_ivr_assessor.sh live-map-gui`.
   - Confirm Planning opens the suite planning/editor surface.
   - Confirm Live Run shows transcript timeline, active IVR state map, response controls, and compact nominal status when healthy.
   - Confirm Review opens run reconstruction/replay/diagnostics surfaces.
   - Confirm DTMF and speech injection controls still call existing APIs and show operator notices.
5. Optional broader validation after implementation:
   - `/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/ -q`

## 12. Risks & Mitigations

- **Risk: Over-renaming persisted suite concepts could imply a schema migration.** Mitigation: change product-facing labels first; keep internal field names and saved JSON schema unchanged unless a separate migration plan is approved.
- **Risk: Hiding telemetry could obscure active failures.** Mitigation: only hide nominal subsystem details; keep warnings, failures, degraded states, and intervention requests visible in live mode.
- **Risk: “Assisted traversal suggestions” could sound agentic.** Mitigation: label suggestions as deterministic and derived from known branches, prompt matches, or suite rules; never describe them as autonomous conversation or reasoning.
- **Risk: Variable syntax mismatch between requested `{{variable}}` language and current `$variable` hint.** Mitigation: first update wording to “variables” generically, then decide in a separate scoped plan whether to support `{{variable}}` syntax or retain `$variable` compatibility.
- **Risk: Review actions may imply backend capabilities that do not exist yet.** Mitigation: distinguish available inspection/replay surfaces from future route-refinement actions; do not add nonfunctional buttons without backing behavior.
- **Risk: Renaming diagnostics to review could bury troubleshooting.** Mitigation: keep a visible, compact `Operational Diagnostics` affordance and exception-first live notices.

## 13. Explicit Guardrails

- No implementation in this pass.
- No frontend rewrite or framework migration.
- No topology changes.
- No websocket protocol changes.
- No replay semantic changes.
- No generalized event system.
- No runtime hot-path changes.
- Preserve deterministic traversal behavior and local-first operational architecture.
- Keep all future changes surgical and inside existing UI/documentation boundaries unless separately approved.