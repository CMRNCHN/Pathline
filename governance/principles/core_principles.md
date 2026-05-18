# Pathline Core Principles

## 1. Low Abstraction Depth
The system's greatest strength is its readability and lack of hidden complexity. A future engineer should find the code simpler, not more abstract, after each refactor.
- Prefer direct callables over shared global state.
- Avoid hidden dispatch or dynamic resolution.
- No new base classes, protocols, or interfaces without strong justification.

## 2. Deterministic Architecture
Every component must behave predictably and be capable of reconstruction from recorded events.
- Replay must be pure: consumes events -> state only.
- Runtime must be bounded and observable.

## 3. Local-First and Permissioned
- All data, recordings, and logs are stored locally.
- Explicit allowlist of authorized phone numbers must be enforced.
- Operator-in-the-loop: no autonomous dialing loops.

## 4. Operational Layering
Pathline is an operating environment with executable governance. The system is divided into five distinct layers:
- **Runtime Layer:** Deterministic execution.
- **Replay Layer:** Temporal truth.
- **Governance Layer:** Operational law.
- **Analyst Layer:** Human interaction.
- **Agent Layer:** AI orchestration.

## 5. Improvement without Complexity
Every change must justify its conceptual cost. If a change adds a new mental model to understand, it must provide significant, measurable value.
