# EXECUTION PLAN: PRIORITIES

## 1. Stabilization (Agent A)
- Objective: 100% environment-agnostic test pass rate.
- Scope: `backend/python/tests/`.
- Boundary: No feature changes.

## 2. Autonomous Runtime Policies (Agent B)
- Objective: Implement recovery and chaos mitigation.
- Scope: `backend/python/src/ivr_assessor/runtime/`.
- Boundary: Preserve deterministic behavior.

## 3. UX Consistency & Demo (Agent C)
- Objective: Polish the warm charcoal interface and verify demo flows.
- Scope: `frontend/static/` and `templates/`.
- Boundary: No new frameworks; vanilla JS only.