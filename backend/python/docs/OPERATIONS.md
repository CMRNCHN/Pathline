# Pathline Operations Runbook

## Purpose

Pathline is a local-first, permissioned IVR route discovery, call-path mapping,
and suite execution system. Operators use it to:

- discover unknown IVR routes within explicit bounds
- map observed prompts and actions into a usable call path
- execute repeatable suites against known flows
- review run outcomes, recordings, and bounded diagnostics after the call

The validated runtime keeps the live call path deterministic and bounded. Deep
inspection exists for review, not for steering the active run.
Operator-facing language must stay IVR-native: use route discovery,
call-path mapping, suite execution, checkpoint verification, route refinement,
and replay/review language.

The canonical planning/governance anchor for product language is
`.ai/plans/ivr-phase-operations-anchor.md`.

## Operational phases

### 1) Suite Planning / Configuration

This phase defines what the next run is allowed to do.

What belongs here:

- confirm the target number is authorized and in scope
- choose the operating mode:
  - route discovery for unknown branches
  - suite execution for known flows
- prepare or update suite JSON, expected prompts, and approved actions
- set run bounds such as call count caps and wall-clock limits
- verify `.env`, telephony credentials, stream auth, and local runtime readiness
- review prior maps, reports, or recordings to decide what needs coverage next

What does not belong here:

- live call supervision
- interpreting partial runtime counters
- post-run conclusions before evidence exists

### 2) Live Operations / Active Run

This phase is for executing one bounded run and supervising it safely.

What belongs here:

- start the run and confirm the correct target/session begins
- watch operator-facing status: active prompt, elapsed time, current path, and map growth
- inject only approved DTMF or speech inputs when the run mode requires it
- stop the run if the target, branch, or prompt sequence moves out of scope
- capture operator notes about unexpected prompts, dead ends, or missing coverage

What should stay hidden or secondary during live operation:

- raw websocket lifecycle details
- deep runtime checkpoint chronology
- artifact directory counts and storage-path concerns
- credentials, auth tokens, and stream query parameters
- low-level media, VAD, and transcript-filter counters
- replay interpretation and suite redesign decisions

Live operation should stay focused on safe execution and operator-visible call
progress, not on low-level diagnostics.

### 3) Review / Replay / Analysis

This phase turns a completed run into the next bounded improvement.

What belongs here:

- review the saved map, suite output, reports, and any available recordings
- inspect bounded runtime diagnostics to understand chronology and failure points
- run deterministic replay inspection on a trace artifact when a trace is available
- compare expected prompts/actions against what the IVR actually presented
- refine suite inputs, branching expectations, and safety bounds for the next run

Current validated review surfaces:

- `inspect-runtime` summarizes runtime diagnostics from a live URL or saved metrics payload
- `inspect-replay` reconstructs a deterministic report from a supplied trace file
- runtime diagnostics include bounded last-session chronology for post-run inspection

Current boundary to remember:

- live mapping persists maps separately from replay trace storage
- replay inspection is a post-run analysis surface, not a live control path

## Terminology

- **Target number:** The authorized IVR number under test.
- **Route discovery:** Bounded exploration of previously unknown IVR branches.
- **Call path:** The ordered sequence of prompts and actions observed in one run.
- **Call-path mapping:** IVR path mapping from observed prompts, choices, and transitions.
- **Prompt timeline:** The live chronology of prompt matches, response anchors, traversal events, and notices.
- **IVR state mapping:** Recording observed IVR states and transitions.
- **Map:** The persisted IVR structure built from discovered prompts, options, and transitions.
- **Suite:** A defined set of prompt-triggered actions and expectations for repeatable execution.
- **Suite execution:** Running a prepared suite against a target IVR.
- **Traversal logic:** Deterministic route-selection behavior used during route discovery.
- **Response automation:** Configured keypad or spoken responses used to progress through an IVR.
- **Reusable inputs:** Named values reused across prompt matches and response anchors.
- **Route check:** A bounded checkpoint group for one planned IVR path.
- **Prompt match:** Text expected from the IVR before a response anchor is sent.
- **Prompt matching:** Comparing heard or transcribed prompts to expected prompt patterns.
- **Response anchor:** The approved DTMF or speech response tied to a prompt match or checkpoint.
- **Response anchoring:** Tying configured responses to specific prompts, states, or route positions.
- **Checkpoint verification:** The pass/fail outcome of an expected suite step during execution.
- **Route refinement:** Using replay, checkpoint verification, and evidence to improve the next bounded run.
- **Reusable suite extraction:** Converting validated routes into repeatable regression suites.
- **Active run:** The current live discovery or suite session.
- **Operator-visible status:** The live surfaces needed to supervise a run safely.
- **Runtime diagnostics:** Bounded post-run or on-demand inspection data about chronology and state.
- **Replay inspection:** Deterministic reconstruction of a supplied trace for analysis after a run.

## Workflow overview

1. Plan the target, bounds, and expected actions.
2. Choose route discovery or suite execution.
3. Verify local runtime readiness before dialing.
4. Run one bounded live session.
5. Review the resulting map, reports, and diagnostics.
6. Refine the next suite or discovery pass from observed evidence.

This loop keeps live operation simple and shifts interpretation into the review
phase, where replay and inspection tools can be used without affecting call flow.

## Operator commands

Launch the live operator surface:

```bash
./run_ivr_assessor.sh live-map-gui
```

Run bounded discovery:

```bash
./run_ivr_assessor.sh iterate-map --target-number +15555550100 --max-calls 12 --wall-clock-cap-s 30
```

Inspect runtime diagnostics:

```bash
./run_ivr_assessor.sh inspect-runtime --runtime-url http://127.0.0.1:8080/api/runtime-diagnostics
```

Inspect a replay trace deterministically:

```bash
./run_ivr_assessor.sh inspect-replay --trace-path backend/python/tests/fixtures/sample_ivr_trace.json
```

## Security baseline

- Never run against unauthorized targets.
- Never share logs or outputs containing account IDs, auth tokens, or stream tokens.
- Keep live-operation displays focused on call progress, not credential-bearing internals.
