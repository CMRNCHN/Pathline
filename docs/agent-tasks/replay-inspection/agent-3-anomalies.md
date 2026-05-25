# Agent 3 — anomalies + next steps

Status: ready
Branch: next/replay-and-runtime-usability--agent-3 (when started)
Worktree: ../pathline-agent-3 (when started)

You own operator intelligence. You do not own data shape.

You may not start until Agent 1's Deliverables 1, 2, 3, and 4 are all
merged to `next/replay-and-runtime-usability`. Verify before beginning
that `replay/inspection_models.py` and `replay/inspection_service.py`
exist on the feature branch — your functions get wired into the service
through stubs Agent 1 left in place.

Read AGENTS.md at the repo root before doing anything.

## Files you own

- `replay/anomaly_detection.py` (new)
- Tests for it under `tests/`

You may not modify any other file. **In particular, you may not modify
anything under `replay/verification/`** — this is the most common scope
drift for this role. Import freely from verification, but do not change it.

## Required reading before edits

- `replay/verification/replay_diff.py`
- `replay/verification/replay_compare.py`
- `replay/verification/replay_search.py`

These already encode "what's wrong with this replay" logic. Your
detection should build on top of them, not duplicate them.

- `replay/inspection_models.py` — to know the `Anomaly`, `NextStep`,
  and `Reference` shapes you must produce. Note that `NextStep` raises
  at construction if `cites` is empty, and `Anomaly` raises if
  `severity` is not in `{info, warn, error}`. Use these constraints to
  your advantage — write code that lets them catch your mistakes.
- `replay/inspection_service.py` — to see where your functions get
  wired in. You implement two top-level functions:
  - `detect_anomalies(report: ReplayInspectionReport) -> list[Anomaly]`
  - `generate_next_steps(report: ReplayInspectionReport) -> list[NextStep]`

## Tasks

### Anomaly detection

Implement `detect_anomalies(report) -> list[Anomaly]`.

Requirements:

- Deterministic. Same input must produce identical output every time.
- Side-effect-free. No I/O, no logging, no globals.
- Reads only from the report. Does not call into the resolver or any
  other service.
- Each anomaly includes `code`, `severity`, `explanation`, and a
  non-empty `references` list pointing at the report fields or
  artifacts that triggered it.

Coverage required, at minimum:

- Non-monotonic event ordering (event timestamps that go backwards in
  the chronology).
- Missing snapshots (artifact_availability marks snapshots missing).
- Missing recordings (artifact_availability marks recording missing).
- Snapshot/replay divergence (state diagnostics indicates snapshot
  offset disagrees with replay reconstruction).
- Empty or low-signal session (event count below a threshold, or no
  prompts in chronology).
- Disconnect after prompt without action (last chronology entry is a
  disconnect immediately following a prompt with no intervening
  action).
- Unsupported or missing artifact combinations (e.g., a recording
  present but no waveform metadata).
- Stalled or incomplete session state (correlation section shows long
  idle, or session_metadata.ended_at is None on what should be a
  finished session).

Severity guidance:

- `info` — observable but not necessarily a problem (e.g., low event
  count for a brief test call).
- `warn` — operator should look (e.g., missing waveform when recording
  exists).
- `error` — operator must look (e.g., snapshot/replay divergence).

### Next-step generation

Implement `generate_next_steps(report) -> list[NextStep]`.

Requirements:

- Deterministic. Side-effect-free.
- Every `NextStep.cites` must be non-empty and reference real fields
  in the report. The `NextStep` constructor enforces non-empty already;
  your job is to make sure the citations are *meaningful*, not just
  non-empty.
- A next step that cannot be grounded must not be emitted. If you find
  yourself wanting to say "investigate this generally," drop it.
- Generated from actual report state, not placeholders. If
  `state_diagnostics.snapshot_offset` is None, do not emit a next step
  that cites it.

Examples of good next steps:

- "Inspect audio around 12.4s — the chronology shows a 4-second gap
  between the prompt and the next action." Cites the chronology
  entry, the timestamp, and the largest_gap_ms summary field.
- "Compare against snapshot offset 230 — replay reconstruction shows
  state divergence here." Cites the state_diagnostics fields and the
  triggering anomaly.
- "Review disconnect reason — session ended after a prompt with no
  user response." Cites the final chronology entry and the relevant
  anomaly.

Examples of bad next steps (do not emit):

- "Look into the session" — no specific citation.
- "Check for errors" — too vague to ground.
- Citing a field that is `None` or empty in the report.

## Tests

Required tests:

- Each anomaly type with a positive case (input that triggers it) and
  a negative case (input that doesn't).
- A determinism test — call `detect_anomalies` twice on the same
  report, assert identical output. Same for `generate_next_steps`.
- A grounding test — for any report producing any next steps, assert
  every `NextStep.cites` is non-empty. The `NextStep` constructor
  already enforces this, but the explicit test catches a regression
  if someone ever weakens the constructor.
- A "no false positives" test — a healthy report with full artifacts,
  no divergence, no gaps — should produce no `error` or `warn`
  anomalies.

## This is a productization pass, not an architecture cleanup pass

You are the agent most likely to drift into refactoring
`replay/verification/` or runtime diagnostics. Don't.

If existing verification code is wrong but works, leave it. Document
the smell in your final summary as an out-of-scope follow-up. You may
import from `replay/verification/` freely but you may not modify it.

## Constraints

- No UI work. No CLI work. No route work.
- No hidden heuristics. Every anomaly explains itself in the
  `explanation` field. If a reader can't understand why the anomaly
  fired from the explanation alone, rewrite the explanation.
- You consume `Anomaly`, `NextStep`, and `Reference` from Agent 1's
  module. If you need new fields on any of these, stop and escalate
  via your final summary. Do not add them yourself.
- Final summary follows AGENTS.md: What changed / Why / Risks /
  Validation status / Removed/Moved / Touched outside ownership.

## Final validation

Before reporting done, run:

```
pytest tests/ -q
```

The full suite. Your changes are isolated to a new module, but the
inspection service imports your functions, so a broken signature can
ripple into the service tests.
