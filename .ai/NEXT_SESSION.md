# Pathline — Next Session Objectives (ENFORCEMENT PHASE)

Last Updated: 2026-05-18

---

## High-Priority Enforcement

1. **Import Boundary Stabilization**
   - Audit all cross-domain imports.
   - Eliminate any remaining leakage between `runtime/` and `analyst/`.
   - Ensure `replay/` does not depend on `analyst/` or `agents/`.

2. **Topology Enforcement**
   - Formalize the directional flow: Analyst → Governance → Replay → Runtime.
   - Implement checks to prevent any layer from bypassing Governance for state changes.

3. **Schema Validation**
   - Finalize machine-readable schemas in `schemas/`.
   - Ensure all event serialization/deserialization is validated against these schemas.

4. **Runtime/Replay Contract Freezing**
   - Define the immutable set of events required for full session reconstruction.
   - Freeze the event structure to ensure backwards compatibility for future replays.

5. **Stability Milestone Definition (M1)**
   - Verify all criteria in `PROJECT_STATE.md` under `PATHLINE_M1_STABLE`.
   - Document any remaining gaps preventing M1 sign-off.

6. **Deterministic Replay Validation**
   - Implement automated tests that verify replay identity (Event Log A → State X).
   - Ensure no side effects occur during the replay process.

7. **Governance Hardening**
   - Transition governance from "guidance" to "executable law".
   - Ensure invariants are checked at the boundary of the runtime kernel.

---

## Explicitly Deprioritized (DO NOT WORK ON)

- **AI Expansion**: No new LLM capabilities or agent orchestrations.
- **Autonomous Runtime Behavior**: No self-healing or autonomous decision loops.
- **Advanced Analytics**: No frequency analysis, silence detection, or complex metrics.
- **UI Feature Work**: No new dashboard widgets, themes, or non-essential visual updates.
- **Speculative Abstractions**: No "future-proofing" or unused generic interfaces.

---

## Authoritative Documentation

- `.ai/HANDOFF.md` — Active state and architectural truth.
- `.ai/PROJECT_STATE.md` — Stability milestones and project health.
- `README.md` — High-level system overview.
