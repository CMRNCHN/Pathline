# Agent 1 — schema + service

Status: deliverable-1-merged, deliverable-2-merged, deliverable-3-running
Branch (D1): merged via squash to next/replay-and-runtime-usability
Branch (D2): next/replay-and-runtime-usability--agent-1-d2 (when started)
Worktree (D2): ../pathline-agent-1

You own the canonical replay inspection contract. Nothing downstream can
start until your Deliverable 1 (the schema file) is merged. Deliverables
2, 3, and 4 may proceed serially after that, but each must surface for
review before the next begins.

Read AGENTS.md at the repo root before doing anything. It defines the
shared rules, file-ownership table, definition of done, pre-edit ritual,
and required output protocol that apply to every agent.

## Files you own

- `replay/inspection_models.py` (new — Deliverable 1)
- `replay/bundle_resolver.py` (new — Deliverable 2)
- `replay/inspection_service.py` (new — Deliverable 3)
- `replay/inspection.py` (existing file, becomes compat shim — Deliverable 4)
- Focused tests for the above under `tests/`

You may not modify any other file. If you need a change elsewhere,
escalate via your final summary instead of editing.

## Required reading before edits

Read `replay/inspection.py` and `tests/test_inspection.py` first. The
existing module has callers (including
`analyst/backend/routes/replay_routes.py`, `replay/cli.py`, and
`replay/reporting.py`) and tests pinning its current behavior. Your
compat shim in Deliverable 4 must keep those callers working and those
tests passing without modification.

Also read:

- `replay/reporting.py`
- `replay/runtime_projection.py`
- `__init__.py` of each of `replay/timelines/`, `replay/snapshots/`,
  `replay/verification/`, `replay/media_sync/`, `replay/reducers/`
- `runtime/events/bookmark_service.py`
- `runtime/events/annotation_service.py`
- `runtime/state/event_ledger.py`
- `runtime/state/replay_state.py`

The bundle resolver in Deliverable 2 imports from these. Do not reinvent
existing accessors.

## Deliverable 1 — `replay/inspection_models.py` (MERGED)

Status: ✅ merged via PR. Both follow-ups (Anomaly severity validation,
explicit empty-cites rejection test) are also merged.

What's on main feature branch after this deliverable:

- `ReplayInspectionReport` dataclass, JSON-serializable,
  `schema_version="1.0"`.
- Twelve top-level sections: `identity`, `artifact_availability`,
  `session_metadata`, `summary`, `chronology`, `path`,
  `state_diagnostics`, `correlation`, `anomalies`,
  `bookmarks_annotations`, `media_status`, `next_steps`.
- `Anomaly` model with `code`, `severity` (validated at construction),
  `explanation`, `references`.
- `NextStep` model with `action`, `rationale`, `cites` (validated
  non-empty at construction).
- `Reference` model — tagged pointer (`kind` discriminator) into the
  report or its underlying artifacts.
- Snapshot test pinning the JSON shape of an empty report.

## Deliverable 2 — `replay/bundle_resolver.py`

Resolves available artifacts for a session id from the existing replay
and runtime modules — event log, snapshots, runtime diagnostics,
recordings, waveform metadata, bookmarks, annotations. Populates the
`artifact_availability` section of `ReplayInspectionReport`.

Requirements:

- Calls into existing accessors in `replay/timelines/`,
  `replay/snapshots/`, `replay/verification/`, `replay/media_sync/`,
  `runtime/events/`, `runtime/state/`. Do not reinvent these.
- Reports partial availability explicitly via the
  `ArtifactAvailabilityEntry`/`ArtifactAvailabilitySection` models.
- Never fails silently when an artifact is missing — partial
  availability is data, not an exception.
- Pure: no formatting concerns, no transport, no logging beyond what
  the existing accessors already do.

Tests:

- Resolver behavior with a session that has all artifacts.
- Resolver behavior with a session missing one or more artifacts
  (recording missing, snapshots missing, bookmarks missing, etc.).
- `availability.missing` correctly lists missing artifact kinds.
- No exceptions raised for any missing-artifact combination.

When you finish Deliverable 2, surface for review and stop. Do not
start Deliverable 3.

In your D2 final summary, include a list of every existing function the
bundle resolver calls, grouped by source module. This lets review
verify nothing was invented or duplicated.

Run before reporting validation status:

```
pytest tests/test_inspection.py tests/test_replay_*.py -q
```

These are the tests pinning current replay behavior. D2 doesn't modify
them but imports from the same modules — if the imports misread an API,
new failures will surface here.

## Deliverable 3 — `replay/inspection_service.py`

Orchestrates bundle resolution and report construction.

Requirements:

- Pure: no I/O outside the resolver, no formatting concerns, no
  transport.
- Imports `detect_anomalies` and `generate_next_steps` from
  `replay/anomaly_detection.py`. If that module doesn't exist yet
  (Agent 3 is the owner), stub the calls as `lambda report: []` and
  document the stub clearly so Agent 3 can fill it in.
- Public entry point produces a fully-populated `ReplayInspectionReport`
  for a given session id.

Tests:

- Service produces a report with the expected sections populated for a
  fixture session.
- Service produces a sensible partial report for a session with
  missing artifacts.
- Stubbed anomaly/next-step calls return empty lists and do not block
  report production.

When you finish Deliverable 3, surface for review and stop. Do not
start Deliverable 4.

## Deliverable 4 — `replay/inspection.py` becomes a compat shim

Convert the existing `replay/inspection.py` into a thin re-export of
the new service's public API.

Requirements:

- `tests/test_inspection.py` continues to pass without any modification.
- Any other test currently exercising `replay/inspection.py` continues
  to pass without any modification.
- All existing callers (analyst routes, CLI, reporting) continue to
  import the same names from `replay/inspection` and get equivalent
  behavior.

If a test fails after the shim is in place, the shim is wrong. Fix the
shim, do not edit the test.

Run before reporting validation status:

```
pytest tests/ -q
```

This is the full suite. By the time the compat shim lands, the new
modules are stable enough that a full-suite run is appropriate.

## Constraints

- No CLI, route, or UI logic anywhere in your files.
- You are the source of truth for payload shape. If Agents 2, 3, or 4
  want extra fields once they start, they escalate to the human; the
  human comes back to you to extend the schema. You do not add fields
  speculatively.
- Formatting (text rendering, pretty-printing) is not your concern.
  If `replay/reporting.py` already has formatters you can leave them
  alone; if you need to call them, do so without modifying them.
- Each deliverable ends with the required output summary from
  AGENTS.md: What changed / Why / Risks / Validation status /
  Removed/Moved / Touched outside ownership.
