# Agent 5 — validation + docs

Status: ready
Branch: next/replay-and-runtime-usability--agent-5 (when started)
Worktree: ../pathline-agent-5 (when started)

You are the merge gate. Nothing ships until you sign off.

You may not start until Agents 2, 3, and 4 have all merged to
`next/replay-and-runtime-usability`. Verify before beginning:

- New CLI subcommand `pathline replay inspect` is on the feature
  branch.
- API route `GET /api/replay-inspection/{session_id}` is on the
  feature branch.
- `replay/anomaly_detection.py` is on the feature branch.
- `analyst/frontend/templates/replay_inspection.html` and related
  JS/CSS are on the feature branch.

Read AGENTS.md at the repo root before doing anything.

## Files you own (new)

- `docs/replay-inspection/operator-guide.md`
- `docs/replay-inspection/developer-contract.md`

You may also fix tests under `tests/` — but only in cases where a test
broke because of inter-agent integration, not because the test itself
was wrong. See task 1 below for the rules.

## Required reading before edits

- Every commit from Agents 1 through 4. Use `git log
  --since=<feature-branch-start>` and read each PR's description and
  diff. List the files each agent touched. Verify none touched files
  outside their ownership column without explicit escalation in their
  final summary. Flag any violations in your final summary.
- AGENTS.md and every task doc in this directory — these are the
  contracts you are validating against.
- All four new modules:
  - `replay/inspection_models.py`
  - `replay/bundle_resolver.py`
  - `replay/inspection_service.py`
  - `replay/anomaly_detection.py`
- The compat shim `replay/inspection.py`.
- New tests added under `tests/`.

## Tasks

### 1. Validation

Run the full test suite:

```
pytest tests/ -q
```

Categorize every failure:

- (a) Caused by Agent 1's work (schema, resolver, service, compat
  shim).
- (b) Caused by Agent 2 (CLI, API route).
- (c) Caused by Agent 3 (anomaly detection, next steps).
- (d) Caused by Agent 4 (UI page route, template, JS).
- (e) Pre-existing failure unrelated to this pass.
- (f) Integration failure — none of the above in isolation, surfaces
  only when their work is combined.

For (a)–(d): surface the failure trace and stop. Do not fix code you
don't own. The owning agent gets a follow-up task to fix it.

For (e): note it in your summary as out-of-scope; do not touch it.

For (f): fix it yourself only if the fix is mechanical (import path
correction, fixture wiring, a test that needs the new field on a
constructor call). If the fix requires non-trivial code changes,
escalate to the human — do not start refactoring product code.

**Do not fix tests by weakening them. Do not delete failing tests.**
If a test is genuinely wrong — describes obsolete behavior, was always
broken, etc. — escalate with a one-line rationale. The human decides
whether to delete or rewrite.

### 2. Operator guide

Write `docs/replay-inspection/operator-guide.md`.

Audience: an operator who has never used the replay inspection workflow
and wants to use it now. Concrete examples. No marketing prose. No
history of the feature. No "in the future we will..." aspirations.

Sections, in this order:

- One-paragraph overview: what this workflow does and when to use it.
- CLI usage: `pathline replay inspect --session-id <id>`. Show a
  realistic invocation, show the expected text output (abbreviated if
  long), describe `--format json` and when an operator would use it.
- API usage: `GET /api/replay-inspection/{session_id}`. Show a curl
  example. Note the JSON contract briefly and link to the developer
  contract doc for the full schema.
- UI usage: navigate to `/replay-inspection?session_id=<id>` (or
  whatever path Agent 4 used). Describe the page sections in the order
  they appear. Note that clicking a next step jumps to its cited
  field.
- Interpreting anomalies: brief explanation of each anomaly code and
  what it means.
- Interpreting next steps: what the action verbs mean and what the
  citations point at.
- Troubleshooting: what to do if the page shows missing artifacts;
  what to do if an anomaly fires without a clear cause; how to report
  bugs in the inspection workflow.

### 3. Developer contract

Write `docs/replay-inspection/developer-contract.md`.

Audience: a developer modifying or extending the inspection workflow.

Sections, in this order:

- One-paragraph overview: the canonical-report-and-service architecture.
- Schema: full reference for `ReplayInspectionReport` and its sections.
  Include the field listings, types, and what each section's docstring
  says.
- `schema_version` policy: additive changes keep the version; removals
  or renames bump it. What "additive" means in practice.
- Constructor invariants:
  - `Anomaly.severity` must be one of `info`/`warn`/`error`.
  - `NextStep.cites` must be non-empty.
  - Both are enforced at construction time.
- Service contract: the inspection service's public API, what callers
  pass in, what they get back.
- Compat shim: `replay/inspection.py` re-exports the new public API.
  Existing callers continue to work unchanged. List what's re-exported.
- Extension points:
  - Adding a new anomaly: where to add it (`replay/anomaly_detection.py`),
    what the code/severity conventions are, how to test.
  - Adding a new next-step kind: same idea.
  - Adding a new report section: how to extend the schema, bump the
    version if appropriate, update the resolver, update the CLI/API/UI.

### 4. Final integration summary

Produce a final summary in your task output (separate from the docs
themselves, which are for future readers). The summary includes:

- **Changed files**, grouped by agent. List every file each agent
  added or modified.
- **Architectural summary** — one paragraph: "The replay inspection
  workflow is now anchored on a canonical `ReplayInspectionReport`
  produced by `replay/inspection_service.py`, consumed by the CLI, an
  analyst API route, and a server-rendered UI page..."
- **Operator workflow summary** — one paragraph: "An operator can now
  inspect a session via `pathline replay inspect`, `GET
  /api/replay-inspection`, or the analyst UI's replay inspection
  page..."
- **Validation results** — test counts, any skipped tests with
  justification, any pre-existing failures noted as out-of-scope.
- **Follow-ups, clearly marked as out of scope.** Things you noticed
  while reading the diffs that should be addressed in a future pass.
  Do not implement them.

## Constraints

- Do not refactor product code unless required to unblock validation.
- Docs are concise and workflow-oriented. No history lessons, no
  aspirational future state, no "we considered X but chose Y" detours
  unless the reader needs that information to use or modify the
  workflow.
- If you can't get the full suite to green, ship a coherent reduced
  slice and document what was cut.
- Your final summary is what the human reads to decide whether the
  whole pass is mergeable to main. Be honest about what's working and
  what isn't.
