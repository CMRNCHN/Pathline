# 1. Goal
Create `.ai/plans/ivr-phase-operations-anchor.md` as the canonical IVRSuite planning/governance anchor for phase-oriented IVR operations language and future-agent alignment.

# 2. Approach
Use `.air/plans/phase-oriented-ivr-product-language-anchor.plan.md:1-260` as the primary source because it already freezes the three workflow phases, terminology glossary, current UI/doc anchors, frontend-only opportunities, backend-supported opportunities, and guardrails. Create a dedicated `.ai/plans/` governance location because `.ai/HANDOFF.md:214-226` lists `.ai/` as the AI governance area and `.air/plans/` is currently plan-output storage rather than canonical project governance. The new document should be a readable governance artifact, not an implementation checklist, and must place the explicit non-authorization rule near the top.

# 3. File Changes
- **Create** `.ai/plans/ivr-phase-operations-anchor.md` — new canonical planning/governance anchor. Include the required governance rule near the top: “Planning artifacts are not implementation authorization. All runtime, topology, storage, protocol, replay, orchestration, or frontend-architecture changes require separate scoped implementation approval.”
- **Do not modify** `.air/plans/phase-oriented-ivr-product-language-anchor.plan.md:1-260` — keep it as the source plan record and copy/condense its content into the canonical governance document.
- **Do not modify** `.air/plans/ivr-operations-language-ui-plan.plan.md:1-220` — keep it as an earlier planning artifact; the new `.ai/plans/ivr-phase-operations-anchor.md` becomes the governance anchor future agents should prefer.
- **Do not modify** runtime/frontend files such as `backend/python/src/ivr_assessor/frontend/templates/index.html`, `backend/python/src/ivr_assessor/frontend/static/js/main.js`, `backend/python/src/ivr_assessor/live_map_gui.py`, `backend/python/src/ivr_assessor/inspection.py`, or `backend/python/src/ivr_assessor/streaming_server.py`.
- **Optional later modify only if desired** `.ai/HANDOFF.md:214-226` — add `.ai/plans/ivr-phase-operations-anchor.md` to the governance file list after the file exists. This is not required by the current request unless the user wants the handoff index updated.

# 4. Implementation Steps
## Task 1: Create governance directory and anchor
1. Create `.ai/plans/` if it does not exist; current inspection showed `.ai/plans does not exist`.
2. Create `.ai/plans/ivr-phase-operations-anchor.md` with a clear title such as `# IVRSuite Phase-Oriented Operations Anchor`.
3. Add a short “Status” block stating the document is canonical for planning/governance and does not authorize implementation.
4. Add the exact governance rule near the top: “Planning artifacts are not implementation authorization. All runtime, topology, storage, protocol, replay, orchestration, or frontend-architecture changes require separate scoped implementation approval.”

## Task 2: Freeze the canonical workflow phases
1. Add a section defining **Suite Planning / Configuration** as the phase for target authorization, run scope, route checks, reusable inputs, prompt matching, response anchoring, traversal bounds, and pre-run evidence.
2. Add a section defining **Live Operations / Active Run** as the phase for supervising one bounded route discovery or suite execution run through prompt timeline, IVR state mapping, traversal logic, response automation/manual response, and exception-first run alerts.
3. Add a section defining **Review / Replay / Analysis** as the phase for call-path replay, checkpoint verification review, artifact/evidence inspection, route refinement, and reusable suite extraction.
4. Preserve the current framing from `.air/plans/phase-oriented-ivr-product-language-anchor.plan.md:28-92`.

## Task 3: Standardize terminology and retired framing
1. Add an “Approved IVR-Native Terminology” section for route discovery, call-path mapping, suite execution, traversal logic, response automation, checkpoint verification, IVR state mapping, prompt matching, response anchoring, route refinement, reusable suite extraction, and replay/review.
2. Add a “Retired Framing” section that forbids product-facing training/teaching the IVR, chatbot language, conversational AI framing, autonomous AI operator framing, agentic IVR reasoning, and self-directed runtime language.
3. Clarify that “operator” is allowed when it means the human IVRSuite user.
4. Preserve the glossary intent from `.air/plans/phase-oriented-ivr-product-language-anchor.plan.md:94-133`.

## Task 4: Define planning vs implementation boundaries
1. Add a “What This Document Authorizes” section limited to language alignment, documentation alignment, planning-agent alignment, review/audit framing, and scoped future-plan structure.
2. Add a “What This Document Does Not Authorize” section explicitly excluding runtime behavior changes, topology changes, storage migrations, websocket/protocol changes, replay semantic changes, orchestration changes, frontend architecture/framework/build changes, broad abstractions, endpoint renames, and hot-path modifications.
3. Add a “Frontend-Only Opportunities” section derived from `.air/plans/phase-oriented-ivr-product-language-anchor.plan.md:199-209`, limited to copy, labeling, empty states, static glossary/help, review-drawer wording, route-refinement wording, and terminology sweep work.
4. Add a “Backend-Supported Opportunities” section derived from `.air/plans/phase-oriented-ivr-product-language-anchor.plan.md:211-219`, stating these require separate scoped planning and approval.

## Task 5: Preserve guardrails for future agents
1. Add runtime guardrails referencing `.ai/PROJECT_STATE.md:25-35` for the hot path and `.ai/ARCHITECTURE_RULES.md:9-28` for deterministic, bounded, replayable runtime constraints.
2. Add frontend guardrails referencing `.ai/ARCHITECTURE_RULES.md:31-49`: vanilla JavaScript only, no frontend frameworks, no build step, no hidden reactivity/state-machine frameworks.
3. Add backend/topology guardrails referencing `.ai/PROJECT_STATE.md:39-49` and `.ai/ARCHITECTURE_RULES.md:31-38`: no GUI FastAPI migration, no topology split, no singleton breakage, no websocket protocol or token auth changes without separate approval.
4. Add replay/review guardrails stating replay and diagnostics are post-run/review surfaces and must not become live steering architecture without separate approval.

## Task 6: Add future-agent usage instructions
1. Add “Future Agents Should Use This Document For” with: product-language alignment, documentation wording, phase taxonomy, planning scopes, frontend-only vs backend-supported distinction, and disallowed framing checks.
2. Add “Future Agents Must Not Infer” with: direct implementation permission, permission to edit runtime/frontend/protocol/replay/topology, permission to introduce frameworks, permission to rewrite product architecture, permission to run broad coding agents, or permission to AI-ify traversal behavior.
3. Add a short “Validation Guidance” section with a terminology sweep command and note that tests are not required for governance-doc-only changes.

# 5. Acceptance Criteria
- `.ai/plans/ivr-phase-operations-anchor.md` exists and is the dedicated canonical governance anchor.
- The explicit governance rule appears near the top exactly: “Planning artifacts are not implementation authorization. All runtime, topology, storage, protocol, replay, orchestration, or frontend-architecture changes require separate scoped implementation approval.”
- The document establishes the three canonical workflow phases: Suite Planning / Configuration, Live Operations / Active Run, and Review / Replay / Analysis.
- The document standardizes approved terminology: route discovery, call-path mapping, suite execution, traversal logic, response automation, checkpoint verification, IVR state mapping, prompt matching, response anchoring, route refinement, reusable suite extraction, and replay/review.
- The document retires product-facing chatbot, conversational AI, agentic IVR, training-the-IVR, teaching-the-IVR, and autonomous AI operator framing.
- The document distinguishes frontend-only opportunities from backend-supported opportunities.
- The document explicitly preserves runtime, websocket/protocol, replay semantic, topology, frontend-framework, and build-step guardrails.
- No runtime code, frontend implementation files, websocket/protocol code, replay behavior, topology files, or framework/build configuration are modified.

# 6. Verification Steps
- Run `test -f .ai/plans/ivr-phase-operations-anchor.md` to confirm the file exists.
- Run `rg -n "Planning artifacts are not implementation authorization" .ai/plans/ivr-phase-operations-anchor.md` to confirm the governance rule is present.
- Run `rg -n "Suite Planning / Configuration|Live Operations / Active Run|Review / Replay / Analysis" .ai/plans/ivr-phase-operations-anchor.md` to confirm the phases are present.
- Run `rg -n "route discovery|call-path mapping|suite execution|traversal logic|response automation|checkpoint verification|IVR state mapping|prompt matching|response anchoring|route refinement|reusable suite extraction" .ai/plans/ivr-phase-operations-anchor.md` to confirm approved terminology is present.
- Run `git diff --name-only` and confirm the only intended changed file is `.ai/plans/ivr-phase-operations-anchor.md`, unless the optional `.ai/HANDOFF.md` index update is explicitly approved.
- No test suite is required because this is planning/governance documentation only.

# 7. Risks & Mitigations
- **Risk: Future agents treat the anchor as a backlog of implementation tasks.** Mitigation: put the non-authorization governance rule near the top and repeat “separate scoped implementation approval” in backend-supported opportunities.
- **Risk: The new document competes with `.air/plans/*` artifacts.** Mitigation: state that `.ai/plans/ivr-phase-operations-anchor.md` is canonical for governance, while `.air/plans/*` remain planning records.
- **Risk: Backend-supported opportunities become implicit permission to alter diagnostics, replay, storage, or runtime.** Mitigation: label them as opportunities requiring separate planning, tests, and approval.
- **Risk: Frontend-only opportunities expand into a frontend rewrite.** Mitigation: explicitly ban framework/build changes and limit frontend-only work to labels, copy, empty states, drawer wording, and static help/glossary improvements.
- **Risk: Retiring agentic language accidentally removes valid human-operator terminology.** Mitigation: clarify that “operator” remains valid when it refers to the human IVRSuite user.


Proceed with creating `.ai/plans/ivr-phase-operations-anchor.md` as the canonical IVRSuite phase-oriented operations governance anchor.

Implement exactly the scoped documentation/governance change described in the plan.

Constraints:
- create `.ai/plans/` if missing
- create `.ai/plans/ivr-phase-operations-anchor.md`
- include the exact non-authorization governance rule near the top
- no runtime code edits
- no frontend implementation edits
- no websocket/protocol changes
- no replay semantic changes
- no topology changes
- no framework/build changes
- no broad refactors

Expected changed file:
- `.ai/plans/ivr-phase-operations-anchor.md`

Do not modify `.air/plans/*`.
Do not modify runtime, frontend, websocket, replay, topology, or build files.
Do not update `.ai/HANDOFF.md` unless you ask first.

After completion:
- run the listed `rg`/`test -f` verification commands
- run `git diff --name-only`
- confirm only the intended file changed
- summarize the governance rule added
- summarize how future agents should use the anchor
- summarize what future agents must not infer from it