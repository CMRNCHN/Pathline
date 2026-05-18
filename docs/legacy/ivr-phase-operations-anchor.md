# Pathline Phase-Oriented Operations Anchor

## Status

This document is the canonical Pathline planning/governance anchor for phase-oriented IVR operations language, documentation alignment, and future-agent planning scopes.

Planning artifacts are not implementation authorization. All runtime, topology, storage, protocol, replay, orchestration, or frontend-architecture changes require separate scoped implementation approval.

`.air/plans/*` files remain planning records. This `.ai/plans/` document is the preferred governance reference for future agents aligning product language or planning follow-on work.

## Canonical Workflow Phases

### Suite Planning / Configuration

Use **Suite Planning / Configuration** for pre-run setup and evidence preparation before IVRSuite places calls or executes routes.

This phase covers:

- Target authorization and dialing allowlist confirmation.
- Run scope, suite boundaries, and route checks.
- Reusable inputs for scripted suite execution.
- Prompt matching and response anchoring definitions.
- Traversal bounds, max-call limits, and pre-run evidence.

### Live Operations / Active Run

Use **Live Operations / Active Run** for supervising one bounded route discovery or suite execution run while the runtime is active.

This phase covers:

- Prompt timeline monitoring.
- IVR state mapping as prompts and transitions are observed.
- Deterministic traversal logic during route discovery.
- Response automation or manual human-operator response.
- Exception-first run alerts and bounded run status.

### Review / Replay / Analysis

Use **Review / Replay / Analysis** for post-run inspection, evidence review, and suite improvement.

This phase covers:

- Call-path replay and run reconstruction.
- Checkpoint verification review.
- Artifact, report, transcript, recording, replay, and evidence inspection.
- Route refinement based on observed IVR behavior.
- Reusable suite extraction from verified call paths.

## Approved IVR-Native Terminology

Use these terms for product-facing language, documentation, planning, and review/audit framing:

Approved terms: route discovery, call-path mapping, suite execution, traversal logic, response automation, checkpoint verification, IVR state mapping, prompt matching, response anchoring, route refinement, reusable suite extraction, and replay/review.

- **Route discovery** — bounded IVR exploration that maps reachable menu paths.
- **Call-path mapping** — the IVR path graph produced by observed prompts, choices, and transitions.
- **Suite execution** — scripted regression execution against known IVR paths and checkpoints.
- **Traversal logic** — deterministic route-selection behavior used during exploration.
- **Response automation** — configured keypad or spoken responses used to progress through an IVR.
- **Checkpoint verification** — validation that expected prompts, states, or artifacts appeared.
- **IVR state mapping** — recording observed IVR states and transitions.
- **Prompt matching** — comparing heard/transcribed prompts to expected prompt patterns.
- **Response anchoring** — tying configured responses to specific prompts, states, or route positions.
- **Route refinement** — post-run improvement of mapped routes, labels, checkpoints, or suites.
- **Reusable suite extraction** — converting validated routes into repeatable regression suites.
- **Replay/review** — post-run evidence inspection, diagnostics, and analysis.

## Retired Framing

Do not use these as product-facing IVRSuite framing:

- Training the IVR or teaching the IVR.
- Chatbot language.
- Conversational AI framing.
- Autonomous AI operator framing.
- Agentic IVR reasoning.
- Self-directed runtime language.

The term **operator** remains allowed when it clearly refers to the human IVRSuite user supervising, configuring, or reviewing runs.

## What This Document Authorizes

This document authorizes only governance and language-alignment work:

- Product-language alignment.
- Documentation wording alignment.
- Planning-agent alignment.
- Review and audit framing.
- Scoped future-plan structure.
- Distinguishing frontend-only opportunities from backend-supported opportunities.

## What This Document Does Not Authorize

This document does not authorize:

- Runtime behavior changes or hot-path modifications.
- Topology changes or GUI/server process splits.
- Storage migrations or storage semantic changes.
- WebSocket/protocol changes or token-auth changes.
- Replay semantic changes.
- Orchestration changes, autonomous agents, or AI-driven runtime routing.
- Frontend architecture, framework, or build-step changes.
- Broad abstractions, endpoint renames, or public contract changes.

## Frontend-Only Opportunities

The following may be planned as frontend-only language work when separately scoped:

- Copy and label updates that align UI wording to the three canonical phases.
- Empty-state wording for planning, active-run, and review surfaces.
- Static glossary/help text using the approved terminology.
- Review-drawer wording for replay/review and checkpoint verification.
- Route-refinement wording after completed runs.
- Terminology sweep work that does not change runtime behavior, protocols, storage, replay semantics, topology, frameworks, or build tooling.

Frontend-only opportunities must remain lightweight vanilla JavaScript work and must not expand into a frontend rewrite.

## Backend-Supported Opportunities

The following are backend-supported opportunities only and require separate scoped planning, implementation approval, tests, and risk review before any code changes:

- New or changed persisted planning metadata.
- New diagnostics, reports, replay fields, or artifacts.
- Changes to route, suite, checkpoint, replay, snapshot, or benchmark semantics.
- Changes to API contracts, websocket events, token auth, or storage paths.
- Any runtime, traversal, response automation, or orchestration behavior changes.

Backend-supported opportunities are not authorized by this anchor.

## Runtime Guardrails

Future plans must preserve the hot path documented in `.ai/PROJECT_STATE.md:25-35`:

```text
Twilio μ-law audio
→ audio_pipeline.py
→ stt_service.py
→ transcript_filter.py
→ deterministic DFS routing
→ tts_service.py
→ Twilio response
```

Runtime behavior must remain deterministic, bounded, replayable, low-latency, queue-driven, observable, and testable as required by `.ai/ARCHITECTURE_RULES.md:9-28`.

Runtime plans must not introduce recursive AI agents, LangChain/LlamaIndex/CrewAI-style orchestration, autonomous LLM routing, giant context windows, uncontrolled async reasoning, or hidden side effects.

## Frontend Guardrails

Future frontend planning must preserve `.ai/ARCHITECTURE_RULES.md:31-49`:

- Use lightweight vanilla JavaScript only.
- Do not add React, Next.js, Vue, Svelte, Redux, MobX, Zustand, Vite, webpack, Rollup, or any frontend build step.
- Do not add hidden reactivity, hidden state-machine frameworks, or websocket abstraction frameworks.
- Keep frontend behavior explicit, deterministic, debuggable, and server-rendered from the Python GUI path.

## Backend and Topology Guardrails

Future backend/topology planning must preserve `.ai/PROJECT_STATE.md:39-49` and `.ai/ARCHITECTURE_RULES.md:31-38`:

- Keep the current single OS process topology unless a separate approved topology plan says otherwise.
- Do not migrate the GUI server path to FastAPI or async GUI frameworks without separate approval.
- Do not break the `STATE` / `RS_STATE` singleton patterns without a full approved plan.
- Do not change websocket protocol, websocket ownership, or token auth without separate approval.
- Keep route handlers thin and domain logic in the existing backend route/domain modules.

## Replay and Review Guardrails

Replay and diagnostics are post-run/review surfaces. They must not become live steering architecture, autonomous route selection, or runtime orchestration without separate scoped implementation approval.

Replay/review wording may clarify evidence inspection and checkpoint verification, but it must not imply permission to change replay semantics, storage format, runtime behavior, websocket protocol, or traversal logic.

## Future Agents Should Use This Document For

- Product-language alignment.
- Documentation wording and terminology decisions.
- Phase taxonomy for planning, active runs, and post-run review.
- Scoping future plans around frontend-only versus backend-supported work.
- Checking for disallowed chatbot, conversational AI, agentic IVR, training-the-IVR, teaching-the-IVR, or autonomous AI operator framing.
- Keeping `.air/plans/*` planning records subordinate to canonical `.ai/plans/` governance.

## Future Agents Must Not Infer

Future agents must not infer:

- Direct permission to implement code changes.
- Permission to edit runtime, frontend, protocol, replay, topology, storage, or build files.
- Permission to introduce frontend frameworks, build steps, orchestration frameworks, or abstraction-heavy systems.
- Permission to rewrite IVRSuite product architecture.
- Permission to run broad coding agents or uncontrolled refactors.
- Permission to AI-ify traversal behavior or replace deterministic DFS routing with autonomous reasoning.

## Validation Guidance

For governance-doc-only changes, repository tests are not required. Use targeted verification instead:

```bash
test -f .ai/plans/ivr-phase-operations-anchor.md
rg -n "Planning artifacts are not implementation authorization" .ai/plans/ivr-phase-operations-anchor.md
rg -n "Suite Planning / Configuration|Live Operations / Active Run|Review / Replay / Analysis" .ai/plans/ivr-phase-operations-anchor.md
rg -n "route discovery|call-path mapping|suite execution|traversal logic|response automation|checkpoint verification|IVR state mapping|prompt matching|response anchoring|route refinement|reusable suite extraction" .ai/plans/ivr-phase-operations-anchor.md
git diff --name-only
```
