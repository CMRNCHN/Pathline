# Agent 2 — CLI + API integration

Status: ready
Branch: next/replay-and-runtime-usability--agent-2 (when started)
Worktree: ../pathline-agent-2 (when started)

You own transport for replay inspection. You do not own data shape.

You may not start until Agent 1's Deliverables 1, 2, 3, and 4 are all
merged to `next/replay-and-runtime-usability`. Verify before beginning:

- `replay/inspection_models.py` exists on the feature branch
- `replay/bundle_resolver.py` exists on the feature branch
- `replay/inspection_service.py` exists on the feature branch
- `replay/inspection.py` is a compat shim re-exporting from the service

Read AGENTS.md at the repo root before doing anything.

## Files you own

- `replay/cli.py` — add new `inspect` subcommand only. Existing
  subcommands must remain unchanged.
- `analyst/backend/routes/replay_routes.py` — add new inspection route
  only. Existing routes must remain unchanged.
- Tests for the above, placed next to the existing CLI/route tests
  following the project's conventions.

You may not modify any other file. If you need a change elsewhere,
escalate via your final summary instead of editing.

## Required reading before edits

- `replay/cli.py` end-to-end. Understand the argument parsing
  convention, output formatting style, and how existing replay
  subcommands are structured.
- `analyst/backend/routes/replay_routes.py` end-to-end. Same idea —
  match existing route patterns.
- `replay/inspection_models.py` — the schema you're consuming.
- `replay/inspection_service.py` — the service entry point you call.
- `replay/reporting.py` — existing formatter functions you may reuse
  for text output. Do not modify this file.
- `tests/test_cli_smoke.py` and any other CLI tests — match the testing
  conventions.

## Tasks

### CLI subcommand

Add `pathline replay inspect --session-id <id>` to `replay/cli.py`.

- Default output: operator-friendly text. Format helpers may live in
  `replay/reporting.py` if similar helpers already live there, or next
  to the CLI command. Pick one location consistently — do not duplicate.
- `--format json` emits the canonical report verbatim
  (`ReplayInspectionReport.to_json()`).
- Calls `inspection_service` only. Build no payload of your own.
- Preserve all existing CLI subcommands exactly as they are.

### API route

Add `GET /api/replay-inspection/{session_id}` to
`analyst/backend/routes/replay_routes.py`.

- Returns the canonical report JSON.
- Calls `inspection_service` only. No transformation, no augmentation,
  no parallel payload assembly.
- Handles unknown session ids with a 404 response.
- Preserve all existing routes exactly as they are.

## Tests

### CLI tests

- Text output stability — snapshot-style. One fixture file under
  `tests/fixtures/` capturing the expected text output for a known
  session fixture. Test asserts the CLI's text output matches it byte
  for byte.
- JSON output stability — snapshot-style. One fixture file capturing
  the expected JSON for the same known session. Test asserts the CLI's
  `--format json` output matches it.
- Partial-artifact case — a session fixture missing some artifacts.
  Verify the CLI renders the partial report without crashing and the
  output reflects the missing artifacts explicitly.

### Route tests

- Payload shape — call the route with a known session id, parse the
  JSON, assert the schema_version and the presence of all twelve
  top-level sections.
- 404 behavior — call the route with an unknown session id, assert the
  response status is 404 and the body is a sensible error.
- (Optional) round-trip stability — assert the route's JSON output
  matches what the CLI produces in `--format json` mode for the same
  session id. This pins the "one canonical payload" invariant.

## Constraints

- You import `ReplayInspectionReport` and the inspection service. You do
  not construct reports.
- If you need a field that isn't in the schema, stop and escalate via
  your final summary. Do not add the field locally to your CLI or route.
- Keep adapters thin:
  - CLI command: parse args → call service → format → print.
  - Route: parse path → call service → return JSON.
- Text formatting helpers go in one place — `replay/reporting.py` or
  alongside the CLI command. Not both.
- Each deliverable ends with the required output summary from
  AGENTS.md: What changed / Why / Risks / Validation status /
  Removed/Moved / Touched outside ownership.

## Final validation

Before reporting done, run:

```
pytest tests/ -q
```

The full suite. Your changes touch CLI argument parsing and route
registration, both of which have indirect blast radius. Full-suite
green is required for merge.
