# AGENTS.md

This repository uses an agent-assisted workflow for the replay inspection
productization pass. Agents read this file for shared context, rules, and
role definitions. Every agent session should reference this document.

## Mission

Make replay inspection a first-class operator workflow. Operators must be
able to answer, from one canonical workflow:

1. What happened
2. Where it failed
3. What changed from expected
4. What to inspect next

This is a **productization pass, not an architecture cleanup pass.**
Do not widen scope. Do not rewrite working subsystems. Do not chase
unrelated lint or refactors.

## Non-goals

- No broad architecture rewrites
- No opportunistic renames
- No UI redesign outside replay inspection
- No unrelated media/runtime refactors
- No test churn outside the inspection contract
- No edits to legacy docs unless this workflow forces it
- No touching temp files or unrelated frontend files

## Workflow

Tasks run sequentially in batches:

1. **Batch 1 (serial):** Agent 1 publishes the canonical schema. No other
   agent starts until Agent 1's Deliverable 1 (the committed
   `replay/inspection_models.py`) is merged to the feature branch.
2. **Batch 2 (parallel):** Agents 2, 3, 4 run concurrently, each in its own
   Git worktree, each starting from the feature branch with Agent 1's
   schema available.
3. **Batch 3 (serial):** Agent 5 runs after 2, 3, 4 merge.

The human operator is the coordinator. They create sessions, gate batches,
and handle merges. No agent plays coordinator.

## Existing code to read before touching anything

This work is **evolution, not greenfield.** Several files in this area
already exist and have tests pinning their behavior. Every agent must read
the files relevant to their role before any edits, and may not silently
change observable behavior of anything that has a test.

Relevant existing files:

- `replay/inspection.py` — current inspection entry point. After this pass,
  becomes a thin compat shim re-exporting from `inspection_service`.
- `replay/reporting.py` — current report formatter. Likely the thin
  formatter layer the new architecture wants.
- `replay/runtime_projection.py` — runtime state projection for replay.
  Likely a dependency of the bundle resolver.
- `replay/cli.py` — existing replay CLI. New `inspect` subcommand lives here.
- `replay/timelines/replay_service.py`, `replay/snapshots/snapshot_service.py`,
  `replay/verification/`, `replay/media_sync/`, `replay/reducers/` — the
  artifact sources the bundle resolver pulls from.
- `runtime/events/bookmark_service.py`, `runtime/events/annotation_service.py`,
  `runtime/state/event_ledger.py`, `runtime/state/replay_state.py` — more
  artifact sources.
- `analyst/backend/routes/replay_routes.py` — existing analyst routes.
  New canonical route is added here alongside the existing ones.
- `analyst/backend/ui/template_loader.py`, `analyst/backend/ui/ui_state.py`,
  `analyst/frontend/templates/index.html`, `analyst/frontend/static/` —
  the analyst UI stack. Server-rendered templates plus vanilla JS. No
  React, no build step.
- `tests/test_inspection.py`, `tests/test_replay_analyst_tooling.py`,
  `tests/test_reporter.py`, `tests/test_cli_smoke.py` — tests that pin
  current behavior.

## Definition of done

- One canonical `ReplayInspectionReport` model in
  `replay/inspection_models.py`. Used identically by CLI, API, UI.
- One inspection service (`replay/inspection_service.py`) builds it. No
  parallel report-building paths.
- `replay/inspection.py` becomes a thin compat shim re-exporting the new
  service's public API. Existing call sites continue to work unchanged.
- Schema includes `schema_version`. Additive changes (new optional fields)
  keep the version; removals or renames bump it.
- Anomalies and `next_steps` are populated from real report state. Every
  `next_step` references at least one concrete field elsewhere in the
  report (a timestamp, an anomaly code, an artifact path, a session id,
  etc.). A `next_step` that cannot cite its source must not be emitted;
  tests enforce this.
- All new entry points (CLI subcommand, API route, UI page) live
  **alongside** the legacy ones. No legacy removal in this pass — that's
  a follow-up PR.
- Existing tests pass without being deleted, weakened, or rewritten to
  match new behavior. Any test rewrite requires a one-line per-test
  rationale in the commit message. If a test was wrong, say so; don't
  paper over it.
- No silent file deletions or moves. Every commit summary includes a
  `Removed/Moved:` section, even if empty.
- New tests cover: bundle resolution (including partial-artifact cases),
  report construction, anomaly detection determinism, CLI output stability,
  API payload shape, next_step grounding.

## File ownership (hard)

| Path | Owner |
|---|---|
| `replay/inspection_models.py` (new) | Agent 1 only |
| `replay/bundle_resolver.py` (new) | Agent 1 only |
| `replay/inspection_service.py` (new) | Agent 1 only |
| `replay/inspection.py` (becomes compat shim) | Agent 1 only |
| `replay/anomaly_detection.py` (new) | Agent 3 only |
| `replay/cli.py` (replay inspect subcommand) | Agent 2 |
| `analyst/backend/routes/replay_routes.py` (new inspection route) | Agent 2 |
| `analyst/frontend/templates/replay_inspection.html` (new) | Agent 4 |
| `analyst/frontend/static/js/replay_inspection.js` (new) | Agent 4 |
| `analyst/frontend/static/css/replay_inspection.css` (new, optional) | Agent 4 |
| `docs/replay-inspection/` (new) | Agent 5 |

`replay/reporting.py` is shared. Agent 1 may extend it (additive only).
Agent 2 may call it. Neither may rewrite it. If a substantive change is
needed, escalate.

If you need to touch a file outside your column, stop and surface this in
your task output as an escalation. Do not silently cross ownership lines.

## Pre-edit ritual (required for every agent)

Before modifying any file:

1. List every file you intend to **read** (existing code paths relevant to
   your role, drawn from "Existing code to read" above).
2. Read them.
3. List every file you intend to **modify or create**.
4. Confirm none are outside your ownership column. If any are, escalate
   before proceeding.
5. Only then begin edits.

## Required output per task

When you finish (or stop for review), produce:

- **What changed.** Files and a one-line summary per file.
- **Why.** Brief rationale tied back to the role.
- **Risks.** What could break, what you're uncertain about.
- **Validation status.** Tests run, results, anything skipped.
- **Removed/Moved:** files removed or moved (write "none" if none).
- **Touched outside ownership:** files outside your ownership column
  (write "none" if none).

## Governance

- Default to stability over cleverness.
- Default to shared contracts over convenience.
- Default to operator usability over internal purity.
- Default to additive refactors over breaking rewrites.
- Do not broaden scope without explicit human approval.
- If blocked, reduce the slice and still ship a coherent operator workflow.

---

## Post-Merge Operational Rules

This is a governance layer, not a code layer. It encodes how branches/worktrees
are retired and which invariants must survive every merge.

### Branch & worktree lifecycle

- A branch exists only while its PR is open, maps to exactly **one** PR, and is
  **not reused** after merge.
- A worktree maps to exactly one active branch. No long-lived "utility"
  worktrees. Detached HEAD is for inspection only, never development.
- **Cleanup order is strict — re-home the worktree BEFORE deleting the branch.**
  Git refuses to delete a branch checked out in any worktree, so deleting first
  fails. Correct sequence after a PR merges:

  1. Re-home / detach the worktree off the merged branch
     (`git switch --detach origin/main` inside the worktree).
  2. Remove the worktree if it was PR-specific: `git worktree remove <path>`.
  3. Delete the remote branch, then the local branch:
     `git branch -d <branch>`.
  4. Prune: `git worktree prune && git fetch --prune`.

### Invariants to re-verify after every merge

These are enforced statically by `tests/test_architecture.py` and the
event/replay tests — re-run them, don't eyeball:

- **No `production → tests/` imports.** Production domains (`runtime`, `replay`,
  `analyst`, `agents`, …) must never import from `tests/`. The allow-list in
  `tests/test_architecture.py` is intentionally empty; any such import is a hard
  failure. (Telecom validation framework lives in `analyst/telecom/`, not
  `tests/`.)
- **Replay log stays exclusive.** Replay reconstructs only from
  `session_*.jsonl`; telemetry is isolated to `telemetry_*.jsonl`. Never route a
  telemetry event at the replay-log prefix.
- **Event model stays append-only.** No in-place mutation or structural rewrite
  of persisted events.
- **No direct SDK use outside adapters.** Telephony clients are constructed via
  `build_telephony()`; no direct vendor-client construction or hidden fallback
  constructors outside the adapter layer.

If a *new* structural/correctness PR becomes necessary in an area already
corrected here, treat it as a signal of incomplete invariant enforcement or
hidden coupling — surface that, don't just patch.

---

## Role definitions

### Agent 1 — schema + service

You own the canonical replay inspection contract. Nothing downstream can
start until you publish.

**Files you own:**
- `replay/inspection_models.py` (new)
- `replay/bundle_resolver.py` (new)
- `replay/inspection_service.py` (new)
- `replay/inspection.py` (becomes a thin compat shim)
- Focused tests for these.

**Required reading before edits.**

Read `replay/inspection.py` and `tests/test_inspection.py` first. The
existing module has callers (including `analyst/backend/routes/replay_routes.py`
and possibly `replay/cli.py` and `replay/reporting.py`) and tests pinning
its current behavior. Your compat shim must keep those callers working
and those tests passing without modification. Also read
`replay/reporting.py`, `replay/runtime_projection.py`, and at minimum the
`__init__.py` of each of `replay/timelines/`, `replay/snapshots/`,
`replay/verification/`, `replay/media_sync/`, `replay/reducers/`, plus
`runtime/events/bookmark_service.py`, `runtime/events/annotation_service.py`,
`runtime/state/event_ledger.py`, and `runtime/state/replay_state.py` so
the bundle resolver knows what artifact APIs already exist. Do not
reinvent existing accessors.

**Deliverable 1 (commit and stop).** `replay/inspection_models.py` with:

- `ReplayInspectionReport` dataclass, JSON-serializable, including
  `schema_version: str` field (initial value `"1.0"`).
- Top-level sections: `identity`, `artifact_availability`,
  `session_metadata`, `summary`, `chronology`, `path`, `state_diagnostics`,
  `correlation`, `anomalies`, `bookmarks_annotations`, `media_status`,
  `next_steps`.
- `Anomaly` model with required fields: `code: str`,
  `severity: Literal["info","warn","error"]`, `explanation: str`,
  `references: list[Reference]`.
- `NextStep` model with required fields: `action: str`, `rationale: str`,
  `cites: list[Reference]` (must be non-empty).
- `Reference` model — a tagged pointer into the report or its underlying
  artifacts (e.g., timestamp, event index, snapshot offset, artifact path).
  Use existing identifier types from `runtime/state/` and
  `runtime/events/` where they already exist; do not invent parallel
  types.
- Every top-level section has a docstring explaining what it is and who
  consumes it.
- A snapshot test pinning the JSON shape of an empty report (one fixture
  file checked in, one test that asserts the serialized empty report
  equals the fixture).

Commit this. Stop and surface for review before continuing.

**Deliverable 2.** `bundle_resolver.py` — resolves available artifacts
(event log, snapshots, runtime diagnostics, recordings, waveform metadata,
bookmarks, annotations) for a session id. Calls into existing accessors
in `replay/timelines/`, `replay/snapshots/`, `replay/verification/`,
`replay/media_sync/`, `runtime/events/`, `runtime/state/`. Reports
partial availability explicitly via the `artifact_availability` section.
Never fails silently when an artifact is missing.

**Deliverable 3.** `inspection_service.py` — orchestrates bundle resolution
and report construction. Pure: no I/O outside the resolver, no formatting
concerns, no transport. Imports `detect_anomalies` and `generate_next_steps`
from `replay/anomaly_detection.py`. If that module doesn't exist yet, stub
the calls as `lambda report: []` and document the stub clearly so Agent 3
can fill it in.

**Deliverable 4.** Convert `replay/inspection.py` into a thin compat shim
that re-exports the new service's public API. Verify
`tests/test_inspection.py` and any other tests that currently pass against
`replay/inspection.py` still pass without modification. If a test fails
after the shim is in place, the shim is wrong — fix the shim, do not
edit the test.

**Constraints:**

- No CLI, route, or UI logic.
- You are the source of truth for payload shape. If Agents 2/3/4 want
  extra fields, they escalate; you extend the schema.
- Formatting (text rendering, pretty-printing) is not your concern. If
  `replay/reporting.py` already has formatters you can leave them alone;
  if you need to call them, do so without modifying them.

---

### Agent 2 — CLI + API integration

You own transport for replay inspection. You do not own data shape.

**Files you own:**
- `replay/cli.py` (new `inspect` subcommand only — existing subcommands
  must remain unchanged)
- `analyst/backend/routes/replay_routes.py` (new inspection route only —
  existing routes must remain unchanged)
- Their tests.

**Required reading before edits.**

Read `replay/cli.py` end-to-end — understand its argument parsing
convention, output formatting style, and how existing replay subcommands
are structured. Read `analyst/backend/routes/replay_routes.py` similarly.
Read `replay/inspection_models.py` and `replay/inspection_service.py` to
understand the contract you're consuming.

**Tasks:**

1. Add `pathline replay inspect --session-id <id>` as a new CLI subcommand
   in `replay/cli.py`. Default output is operator-friendly text.
   `--format json` emits the canonical report verbatim. Calls
   `inspection_service` only; builds no payload of its own.
2. Preserve all existing CLI subcommands unchanged.
3. Add `GET /api/replay-inspection/{session_id}` route in
   `analyst/backend/routes/replay_routes.py` returning the canonical
   report JSON. Calls `inspection_service` only. No transformation, no
   augmentation, no parallel payload.
4. Preserve all existing routes in that file unchanged.
5. Add CLI tests covering text and JSON output stability (snapshot-style,
   one fixture file per format), plus the partial-artifact case. Add
   route tests covering payload shape and 404 behavior. Place these next
   to the existing CLI/route tests, following the project's test
   conventions.

**Constraints:**

- You import `ReplayInspectionReport` and the inspection service. You do
  not construct reports.
- If you need a field that isn't in the schema: escalate. Do not add it
  locally.
- Keep adapters thin. A CLI command is roughly: parse args → call service
  → format → print. A route is: parse path → call service → return JSON.
- Text formatting helpers may live in `replay/reporting.py` if that's
  where similar helpers already live, or next to the CLI command. Pick
  one and be consistent; do not duplicate.

---

### Agent 3 — anomalies + next steps

You own operator intelligence. You do not own data shape.

**Files you own:** `replay/anomaly_detection.py` (new). Plus its tests.

**Required reading before edits.**

Read `replay/verification/replay_diff.py`, `replay/verification/replay_compare.py`,
`replay/verification/replay_search.py` — these already encode "what's
wrong with this replay" logic and your anomaly detection should build on
top of them, not duplicate them. Read `replay/inspection_models.py` to
know the `Anomaly`, `NextStep`, and `Reference` shapes you must produce.
Read `replay/inspection_service.py` to see where your functions get wired
in.

**Tasks:**

1. Implement `detect_anomalies(report: ReplayInspectionReport) -> list[Anomaly]`.
   Deterministic. Side-effect-free. No I/O.
2. Cover at minimum: non-monotonic event ordering, missing snapshots,
   missing recordings, snapshot/replay divergence, empty or low-signal
   session, disconnect after prompt without action, unsupported or missing
   artifact combinations, stalled or incomplete session state.
3. Implement `generate_next_steps(report: ReplayInspectionReport) -> list[NextStep]`.
   Every `NextStep.cites` must be non-empty and reference real fields in
   the report. A next step that cannot be grounded must not be emitted.
4. Tests must include: each anomaly type with a positive and negative case;
   a determinism test (same input → same output, twice); a grounding test
   that fails if any `NextStep` has empty `cites`.

**This is a productization pass, not an architecture cleanup pass.** You
are the agent most likely to drift into refactoring `replay/verification/`
or runtime diagnostics. Don't. If existing verification code is wrong but
works, leave it; document the smell in your final summary as a follow-up.
You may import from `replay/verification/` freely but not modify it.

**Constraints:**

- No UI work. No CLI work. No route work.
- No hidden heuristics. Every anomaly explains itself in the `explanation`
  field.
- You consume `Anomaly`, `NextStep`, and `Reference` from Agent 1's module.
  If you need new fields on any of these: escalate.

---

### Agent 4 — analyst UI workflow

You own the operator UI experience for replay inspection. You do not own
data shape.

**Stack: server-rendered Jinja templates + vanilla JS.** No React, no
build step, no component framework. Follow the existing analyst UI
conventions exactly.

**Files you own (new):**
- `analyst/frontend/templates/replay_inspection.html`
- `analyst/frontend/static/js/replay_inspection.js`
- `analyst/frontend/static/css/replay_inspection.css` (only if needed;
  prefer extending existing CSS)
- A route registration for the page itself (e.g., `GET /replay-inspection`
  returning the template) in the appropriate analyst route file — Agent 2
  will own the API route; you own the *page* route. Coordinate with
  Agent 2 if both need to land in the same file.

You may **read** `analyst/frontend/templates/index.html`,
`analyst/backend/ui/template_loader.py`, `analyst/backend/ui/ui_state.py`,
and `analyst/frontend/static/` to learn the conventions. You may **not**
modify any of them except to add a navigation entry pointing at the new
page (additive only).

**Tasks:**

1. Add a replay inspection page accessible from the analyst UI. Lives
   alongside existing replay/live-map pages, does not replace them.
2. The page fetches the canonical report from
   `GET /api/replay-inspection/{session_id}` (Agent 2's route) and renders
   it. No client-side payload reshaping.
3. Surface: summary card, anomalies (color-coded by severity), timeline,
   prompt/action path, state/media diagnostics, next steps as actionable
   items.
4. Each `next_step` rendered in the UI must link or scroll to the report
   field it cites (anchor links or scroll-to behavior in JS). The
   grounding rule is also a UX feature: operators should see *why* a
   suggestion was made.

**Constraints:**

- No bespoke payload shape. No client-side anomaly detection or next-step
  generation. If the report doesn't have it, you don't render it.
- No frontend cleanup outside the new workflow files. No CSS refactors
  on existing pages. No JS refactors on existing pages.
- Scope is tightly bounded to this flow. Navigation/menu changes are
  allowed only as additive entries.

---

### Agent 5 — validation + docs

You are the merge gate.

**Files you own:** `docs/replay-inspection/` (new). Test fixes only in
cases where a test broke because of inter-agent integration, not because
the test was wrong.

**Required reading before edits.**

Read every commit from Agents 1–4. List the files each agent touched.
Verify none touched files outside their ownership column without explicit
escalation. Flag violations in your summary.

**Tasks:**

1. Run the full test suite. Categorize failures: (a) caused by Agent 1,
   (b) Agent 2, (c) Agent 3, (d) Agent 4, (e) pre-existing, (f)
   integration. For categories a–d, surface the failure trace and stop;
   do not fix code you don't own. Fix (f) yourself only if the fix is
   mechanical (import path, fixture wiring); otherwise escalate.
2. Do not fix tests by weakening them. Do not delete failing tests. If a
   test is genuinely wrong, escalate with a one-line rationale.
3. Write `docs/replay-inspection/operator-guide.md` — how an operator
   uses the CLI, API, and UI. Concrete examples. No marketing prose.
4. Write `docs/replay-inspection/developer-contract.md` — the canonical
   schema, the service contract, the `schema_version` policy, the
   compat-shim layer in `replay/inspection.py`, and how to extend.
5. Produce a final integration summary: changed files (grouped by agent),
   architectural summary (one paragraph), operator workflow summary
   (one paragraph), validation results (test counts, any skipped tests
   with justification), and follow-ups **clearly marked as out of
   scope**.

**Constraints:**

- Do not refactor product code unless required to unblock validation.
- Docs are concise and workflow-oriented. No history lessons, no
  aspirational future state.
- If you can't get to green, ship a coherent reduced slice and document
  what was cut.
