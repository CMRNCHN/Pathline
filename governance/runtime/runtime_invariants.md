# Runtime Invariants

## R-001: Deterministic Hot Path
The core runtime execution path (audio -> STT -> routing -> TTS -> audio) must remain deterministic and bounded.
- No recursive AI agents.
- No autonomous LLM routing.
- No uncontrolled async reasoning.
- No hidden side effects.

## R-002: Bounded Execution
All runtime processes must have explicit bounds and lifecycle management.
- Max calls, wall-clock time, and depth limits must be strictly enforced.
- The prompt queue must be per-session and observable.

## R-003: Operational State Isolation
- State singletons (`STATE`, `RS_STATE`) must not be broken without a full transition plan.
- Route handlers must remain thin; business logic belongs in domain modules.
- Shared state must be localized to `backend/ui/ui_state.py`.

## R-004: Port Allocation
- GUI HTTP Server: Port 8080 (127.0.0.1)
- Streaming Server: Port 8081 (0.0.0.0)

## R-005: Event Immutability
- Events are immutable once committed to the ledger.
- The EventBus is the single source of truth for runtime occurrences.
