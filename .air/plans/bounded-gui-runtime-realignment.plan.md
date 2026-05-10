## 1. Goal
Implement a bounded visual modernization of the IVRSuite operator console so it feels like high-end operational runtime tooling—calm, premium, and information-dense—without changing frontend architecture, websocket behavior, replay semantics, backend topology, or deterministic runtime behavior.

## 2. Approach
Retain the current server-rendered page in `backend/python/src/ivr_assessor/frontend/templates/index.html:12-275`, the explicit DOM-driven behavior in `backend/python/src/ivr_assessor/frontend/static/js/main.js:1-214`, and the existing modal-based suite surfaces in `backend/python/src/ivr_assessor/frontend/templates/index.html:128-272`. Modernize through a design-token pass in `backend/python/src/ivr_assessor/frontend/static/css/main.css:3-170` and `backend/python/src/ivr_assessor/frontend/static/css/run_suites.css:1-75`, then restructure the page into a clearer operator shell that consumes the observability endpoints already exposed by `backend/python/src/ivr_assessor/live_map_gui.py:302-365` and `backend/python/src/ivr_assessor/live_map_gui.py:649-741`.

The implementation should prefer restrained visual hierarchy over decorative effects: lower-contrast surfaces, tighter typography control, semantic-only status color, calm motion, and explicit data groupings. This keeps the UI aligned with the repo’s stated preferences for low abstraction, explicit behavior, and lightweight frontend code.

## 3. Current Visual / UX Gaps
- The current shell is still visually organized as a mapper prototype: transcript stack + graph block + control sidebar (`backend/python/src/ivr_assessor/frontend/templates/index.html:28-126`) rather than an operator console.
- The palette is high-saturation and gradient-heavy, especially header, primary buttons, caption blocks, graph nodes, and control surfaces (`backend/python/src/ivr_assessor/frontend/static/css/main.css:17-28`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:33-37`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:50-53`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:59-60`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:76-99`).
- There is visual noise from glows, bright accent fills, and multiple competing gradients (`backend/python/src/ivr_assessor/frontend/static/css/main.css:19`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:25`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:35`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:51`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:76`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:93`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:95`).
- Status semantics are visually inconsistent: the header badge is updated inline in JS (`backend/python/src/ivr_assessor/frontend/static/js/main.js:45-58`), while the sidebar status box is static placeholder markup (`backend/python/src/ivr_assessor/frontend/templates/index.html:99-118`).
- The transcript feed is the visual center, but it is a raw log list driven by `addLog()` (`backend/python/src/ivr_assessor/frontend/static/js/common/dom.js:7-24`), which is not the best representation for long-running operator cognition.
- Typography hierarchy is shallow: small size deltas, all-caps labels everywhere, and many monospace treatments in surfaces that should read as structured UI rather than debug raw output (`backend/python/src/ivr_assessor/frontend/static/css/main.css:21`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:37-38`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:56`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:68`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:89`).
- Run suites already resemble a more structured operational panel (`backend/python/src/ivr_assessor/frontend/templates/index.html:200-270`, `backend/python/src/ivr_assessor/frontend/static/css/run_suites.css:1-75`) and should visually inform the main shell rather than feel like a separate product.

## 4. Updated Visual System Proposal
### Design principles
- **Restrained surfaces**: prefer graphite/slate layers with subtle separation instead of bright cards.
- **Operational emphasis**: data grouping first, decoration second.
- **Semantic color only**: accent for interaction/focus, green/amber/red only for real status meaning.
- **Long-session comfort**: low glare, high legibility, steady rhythm.
- **Premium density**: tighter than consumer SaaS, calmer than gaming dashboards.

### Color system recommendation
Refactor `:root` in `backend/python/src/ivr_assessor/frontend/static/css/main.css:3-10` into a more neutral systems palette:
- **Canvas**: near-black graphite, e.g. `#0b0d12` / `#101319`
- **Panel base**: `#141922`
- **Raised panel**: `#181f2a`
- **Inset / input**: `#11161e`
- **Borders**: cool gray alpha around `rgba(255,255,255,.06)` to `.10`, kept subtle
- **Primary text**: cool off-white, slightly less blue than current `--text-1`
- **Secondary text**: desaturated slate-gray
- **Accent**: subdued steel-blue or indigo-gray, less saturated than current `--accent`
- **Success/warn/danger**: muted semantic tones used only in pills, indicators, and state edges

### Typography recommendation
Keep the current Inter import in `backend/python/src/ivr_assessor/frontend/static/css/main.css:1`, but tighten hierarchy:
- **Shell titles**: 14–16px, semibold, neutral white
- **Panel titles**: 11–12px, semibold, not overly letterspaced
- **Body data**: 12–13px with slightly taller line-height for logs/timelines
- **Meta data**: 10–11px for timestamps/chips/captions
- **Monospace**: reserve for timestamps, IDs, DTMF values, queue counts, and raw diagnostics, not broad panel copy

### Depth / surface recommendation
Replace obvious glow/gradient treatments with:
- flat-to-subtle vertical tonal shifts on shell surfaces
- 1px low-contrast borders
- rare soft shadows for modal elevation only
- inset focus rings on controls
- grouped panel stacks with shared radius language

## 5. Panel Hierarchy Proposal
### A. Header / Operator Shell
Build from `backend/python/src/ivr_assessor/frontend/templates/index.html:12-26`:
- left: brand + compact operator nav label
- center: target/session controls
- right: mode chip, smoke/suite access, settings, minimal session badge
- add an explicit end-session action using existing `/api/end` (`backend/python/src/ivr_assessor/live_map_gui.py:711-712`)

Visual treatment:
- lower height pressure than current bright header (`backend/python/src/ivr_assessor/frontend/static/css/main.css:17-28`)
- flatter background, subtler logo treatment, reduced icon chroma
- primary action stays obvious, but no emerald marketing-style CTA treatment

### B. Heartbeat Strip
Insert directly below the header and above the main work area.
Surfaces:
- runtime readiness
- websocket status
- STT/TTS status
- queue depth
- checkpoint visibility
- active session state
- stale runtime detection
- health/diagnose signals

These should appear as compact, equal-weight cards or segmented status modules, populated from current diagnostics/runtime payloads in `backend/python/src/ivr_assessor/live_map_gui.py:314-342` and `backend/python/src/ivr_assessor/inspection.py:110-184`.

### C. Active Session Timeline
Make this the primary focal surface, replacing the current transcript-first emphasis in `backend/python/src/ivr_assessor/frontend/templates/index.html:31-47`.

Structure:
- compact title row with timer and filter controls
- pinned live caption strip
- typed timeline rows for transcript/action/websocket/checkpoint/replay/cleanup
- optional filter chips: `All`, `Transcript`, `Routing`, `WebSocket`, `Replay`, `Cleanup`

Use `/api/runtime-diagnostics` merged timeline from `backend/python/src/ivr_assessor/inspection.py:178-184` rather than relying only on log strings from `backend/python/src/ivr_assessor/backend/routes/mapper_routes.py:20-42`.

### D. Contextual IVR Graph / Mapper Pane
Reuse the current graph surface in `backend/python/src/ivr_assessor/frontend/templates/index.html:48-50` and renderer in `backend/python/src/ivr_assessor/frontend/static/js/main.js:20-40`, but demote its visual dominance.

Visual behavior:
- show graph metadata at the top
- highlight only the selected or currently-related prompt/action context
- keep it readable, compact, and contextual
- avoid turning it into a full visual canvas or animated map explorer

### E. Input / Control Surface
Unify the current mode/input/keypad/status stack from `backend/python/src/ivr_assessor/frontend/templates/index.html:53-124` into a calmer operator tools column or footer module:
- manual DTMF/text injection
- autopilot/manual mode
- bounded operator actions
- quick session tools

This surface should feel like a practical control bench, not a bright keypad panel.

### F. Diagnostics / Inspection Drawer
Make a bottom drawer that can expand/collapse without modal takeover.
Tabs:
- Runtime
- Session
- WebSocket
- Queue / Checkpoints
- Artifacts
- Smoke

Use current runtime data from `backend/python/src/ivr_assessor/inspection.py:110-184`, `backend/python/src/ivr_assessor/live_map_gui.py:327-341`, and `backend/python/src/ivr_assessor/streaming_server.py:197-225`.

## 6. CSS Modernization Approach
### Task 1: Establish a calmer token system
- **Modify** `backend/python/src/ivr_assessor/frontend/static/css/main.css:3-10`
  - replace current saturated blue/green-forward token set with graphite/slate system tokens
  - split tokens into canvas, panel, raised-panel, input, border, text, accent, and semantic status families
  - add spacing/radius/shadow/focus tokens so panel styling is consistent

### Task 2: Flatten and unify shell surfaces
- **Modify** `backend/python/src/ivr_assessor/frontend/static/css/main.css:16-100`
  - remove strong gradients, glow-heavy treatments, and loud button fills
  - reduce reliance on fully rounded “badge SaaS” styling where not operationally useful
  - standardize panel radius, border, and padding rhythm
- **Modify** `backend/python/src/ivr_assessor/frontend/static/css/run_suites.css:1-75`
  - bring suite modal styling into the same neutral systems palette and spacing rhythm as the main shell

### Task 3: Create reusable panel classes
- **Modify** `backend/python/src/ivr_assessor/frontend/static/css/main.css:145-170`
  - add utility classes for panel titles, secondary text, chips, timeline rows, state pills, split panes, drawer tabs, and empty states
  - keep utilities minimal and explicit; no utility-framework sprawl

### Task 4: Rebuild the main layout around operator cognition
- **Modify** `backend/python/src/ivr_assessor/frontend/templates/index.html:12-126`
  - replace transcript + graph vertical stack plus right sidebar with:
    - operator header
    - heartbeat strip
    - primary timeline pane
    - contextual graph pane
    - calmer control surface
    - diagnostics drawer shell
- **Modify** `backend/python/src/ivr_assessor/frontend/static/css/main.css:30-100`
  - define the new layout grid/flex structure and responsive collapse behavior for narrower widths

## 7. Frontend Behavior / Rendering Plan
### Task 5: Add bounded shared page state
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/common/state.js:1-7`
  - expand `AppState` with explicit fields such as `runtimeDiagnostics`, `runtimeMetrics`, `diagnose`, `selectedTimelineFilter`, `selectedTimelineEvent`, `drawerOpen`, and `activeDrawerTab`
  - keep this as a plain object only; do not introduce a generalized state framework

### Task 6: Extend API surface using existing endpoints
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/common/api.js:19-44`
  - add `getRuntimeMetrics()`, `getRuntimeDiagnostics()`, `getDiagnose()`, `getMaps()`, and `endCall()`
  - optionally add lightweight export helpers if artifacts are surfaced in the drawer

### Task 7: Replace flat log rendering with a typed timeline
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/common/dom.js:7-33`
  - preserve `addLog()` for legacy suite/test feed compatibility
  - add new render helpers for timeline rows, heartbeat cards, state pills, diagnostics tables, and graph metadata headers
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/main.js:42-214`
  - split polling by concern:
    - `/api/status` for fast control/caption updates
    - `/api/runtime-diagnostics` for structured timeline and drawer content
    - `/api/diagnose` slower or on-demand for operator diagnostics
  - render the header badge, heartbeat strip, live caption, timeline, graph context, and drawer from structured payloads rather than inline styles and raw log strings

### Task 8: Visually connect timeline to graph
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/main.js:20-40`
  - evolve `renderGraph()` so it can show a selected or inferred active prompt context
  - add metadata labels for node count / current target / saved map context
  - keep the graph renderer deterministic and text-driven; no animation-heavy visualization

### Task 9: Fold suite/smoke surfaces into the visual system
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:16-322`
  - stop treating run suites like a separate visual island
  - integrate its launch affordance into the operator shell / smoke tools entry
  - preserve current runner behavior and polling semantics
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:24-294`
  - only update visual entry affordances or labels as needed so the legacy editor still feels consistent with the new shell

## 8. Minimal-Motion Guidance
Use motion only where it improves operational comprehension.

### Keep
- subtle hover/focus feedback on controls
- low-duration panel/drawer expansion transitions (120–180ms)
- progress fill updates for suite runs
- small opacity changes on live status transitions where helpful

### Remove or reduce
- pulsing glow dots as the default for every active state (`backend/python/src/ivr_assessor/frontend/static/css/main.css:35-36`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:52`)
- aggressive scale transforms on keypad press (`backend/python/src/ivr_assessor/frontend/static/css/main.css:87`)
- bright hover states with large focus glows (`backend/python/src/ivr_assessor/frontend/static/css/main.css:71`, `backend/python/src/ivr_assessor/frontend/static/css/main.css:86`)
- decorative animation in non-stateful areas

### Motion rules
- default transition durations: 120–160ms
- no infinite animation except where active live-state genuinely needs attention
- status motion should indicate change, not decorate the idle state
- drawer and filter interactions should feel crisp, not playful

## 9. Frontend-Only Opportunities
These can be shipped without backend changes using current APIs and payloads:
- the new operator shell layout and visual system
- heartbeat strip for runtime/session/queue/checkpoint/staleness using current diagnostics payloads
- typed active session timeline from `/api/runtime-diagnostics`
- contextual graph pane using current `/api/status` graph and map endpoints
- diagnostics drawer for runtime/session/websocket/queue/artifact summaries
- calmer input/control surface with explicit operator actions
- visual alignment of run suites and test suites with the main shell

## 10. Backend-Supported Opportunities
These remain optional additive follow-ups, not blockers for the modernization pass:
- explicit TTS backend state in the 8080 GUI payload if pre-session TTS visibility is desired; today it is only available in stream-server health (`backend/python/src/ivr_assessor/streaming_server.py:606-615`)
- richer artifact history endpoints beyond summary counts from `backend/python/src/ivr_assessor/live_map_gui.py:327-341`
- replay artifact inspection endpoints building on `backend/python/src/ivr_assessor/inspection.py:51-85`
- future comparison mode for artifacts/snapshots as a separate read-only diagnostic feature

## 11. File Changes
### Frontend-first modernization phase
- **Modify** `backend/python/src/ivr_assessor/frontend/templates/index.html:12-126`
  - restructure main operator shell and insert heartbeat strip + diagnostics drawer skeleton
- **Modify** `backend/python/src/ivr_assessor/frontend/templates/index.html:200-270`
  - align run-suites modal entry and shell adjacency with the new visual model
- **Modify** `backend/python/src/ivr_assessor/frontend/static/css/main.css:3-170`
  - replace current palette/depth/spacing/motion rules and add new layout/panel/timeline/drawer styling
- **Modify** `backend/python/src/ivr_assessor/frontend/static/css/run_suites.css:1-75`
  - harmonize suite modal visuals with the premium dark systems palette
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/common/api.js:19-44`
  - expose diagnostics/runtime APIs to the frontend
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/common/state.js:1-7`
  - add bounded shared page state for filters, selection, diagnostics, and drawer tabs
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/common/dom.js:7-33`
  - add explicit render helpers for new UI surfaces
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/main.js:20-214`
  - render heartbeat, timeline, graph context, and drawer using structured payloads
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/run_suites.js:16-322`
  - align smoke/suite launch with the operator shell
- **Modify** `backend/python/src/ivr_assessor/frontend/static/js/modules/test_suites.js:24-294`
  - small integration affordance updates only if needed

### Optional backend-support phase
- **Modify** `backend/python/src/ivr_assessor/live_map_gui.py:302-365`
  - add read-only aggregation only for missing inspection data such as TTS state or artifact listings
- **Modify** `backend/python/src/ivr_assessor/inspection.py:51-184`
  - reuse inspection helpers for any additive artifact inspection support
- **Modify** `backend/python/tests/test_live_map_gui.py:1-64`
- **Modify** `backend/python/tests/test_inspection.py:1-92`
  - extend test coverage only if new read-only endpoints are added

## 12. Phased Implementation Strategy
### Phase 1: Token and surface modernization
- update palette, typography, border/shadow/radius system
- neutralize gradients/glows
- align main and modal surfaces visually
- no layout/behavior changes yet

### Phase 2: Operator shell realignment
- restructure the main page into header + heartbeat + primary timeline + graph + controls + drawer
- keep all current controls and modals functional
- move from mapper-first to operator-first layout

### Phase 3: Structured timeline and diagnostics rendering
- consume runtime diagnostics endpoints
- add timeline filters and typed rows
- populate heartbeat and drawer from structured payloads
- visually connect timeline context to graph context

### Phase 4: Smoke/suite integration polish
- fold run suites into the visual system
- tighten live event feed readability
- align test-suite modal styling and controls with the new shell

### Phase 5: Optional backend-supported inspection enhancements
- only if needed after the frontend pass proves the remaining gaps

## 13. Acceptance Criteria
- The main console visually shifts from bright mapper prototype styling to a subdued premium operational shell using only the existing HTML/CSS/JS stack.
- The palette is dark graphite/slate with restrained accents and semantic-only status color; bright gradient-heavy styling is removed from the main shell.
- The primary information focus becomes the active session timeline, not the raw transcript box.
- A heartbeat strip is visible and populated from existing runtime surfaces without websocket protocol changes.
- The IVR graph remains present but contextual, with reduced visual dominance and clear relation to selected session context.
- Input, DTMF, mode, and bounded operator controls remain explicit and functional through existing routes.
- The diagnostics/inspection drawer surfaces runtime/session/websocket/queue/artifact data from current backend payloads where available.
- Run suites and smoke validation remain functionally unchanged while visually aligning with the new shell.
- No frontend framework, build pipeline, orchestration layer, websocket contract change, replay semantic change, or backend topology change is introduced.

## 14. Verification Steps
### Manual verification after implementation
- Load the operator console and confirm header, heartbeat, timeline, graph, control surface, and diagnostics drawer are all visible and readable without modal dependence.
- Confirm color usage is restrained: blue accent only for interaction/focus, green/amber/red only for semantic states.
- Start a session and verify the UI still uses existing controls from `/api/start`, `/api/inject-dtmf`, `/api/inject-voice`, `/api/set-mode`, and `/api/end` (`backend/python/src/ivr_assessor/live_map_gui.py:703-714`).
- Confirm timeline filters do not alter runtime behavior; they only change frontend visibility.
- Confirm the graph remains stable and contextual when timeline selections change.
- Open run suites and test suites to verify modal styling and behavior still work.
- Confirm long-session readability: no overly bright glow, no distracting idle animations, stable scroll behavior.

### Test commands once implemented
- `pytest backend/python/tests/test_live_map_gui.py -q`
- `pytest backend/python/tests/test_inspection.py -q`
- `pytest backend/python/tests/test_streaming_server_auth.py -q`
- If backend-support additions are made: `pytest backend/python/tests/ -q`

## 15. Risks & Mitigations
- **Risk: The visual pass drifts into a de facto frontend rewrite.**
  - Mitigation: limit work to template/CSS/rendering helpers and existing API usage; keep DOM ownership explicit in current files.
- **Risk: A premium aesthetic is interpreted as more gradients/glow.**
  - Mitigation: set the design bar around neutral surfaces, semantic color discipline, and sparse motion.
- **Risk: Timeline richness increases cognitive load.**
  - Mitigation: add filters, consistent event row types, and calm spacing; default to the most operator-useful categories.
- **Risk: Styling diverges between main shell and run-suite/test-suite surfaces.**
  - Mitigation: move both onto the same token system in `main.css` and `run_suites.css`.
- **Risk: Missing backend data leads to invented state.**
  - Mitigation: render unavailable data explicitly as `Unknown`, `Not surfaced`, or summary-only rather than inferring unsupported state.
- **Risk: The work touches many frontend files.**
  - Mitigation: implement in phases and keep scope bounded to visual modernization and structured rendering, not new product areas.

## 16. Guardrails
- Preserve vanilla JavaScript and explicit DOM rendering patterns in `backend/python/src/ivr_assessor/frontend/static/js/main.js:1-214` and `backend/python/src/ivr_assessor/frontend/static/js/common/*.js`.
- Do not introduce React, Vue, Svelte, a build pipeline, or generalized state management.
- Do not change websocket semantics, auth, or push/poll architecture.
- Do not change replay semantics, runtime topology, or the deterministic audio/session hot path.
- Keep motion lightweight and purposeful.
- Prefer operational clarity over decorative novelty.
- The resulting interface should read as premium runtime tooling, not a futuristic hacker dashboard or consumer SaaS app.