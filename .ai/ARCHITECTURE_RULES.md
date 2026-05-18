# Hard Architectural Constraints

Last Updated: 2026-05-07

---

## Runtime Rules

The HOT PATH must remain:
- deterministic
- bounded
- replayable
- low-latency
- queue-driven
- observable
- testable

Realtime runtime must NOT contain:
- recursive AI agents
- LangChain orchestration
- autonomous LLM routing
- giant context windows
- uncontrolled async reasoning
- hidden side effects

---

## Backend Rules

DO NOT:
- add FastAPI yet (stdlib http.server is fine for current scale)
- add async frameworks to the GUI server
- add LLMs to any hot path
- break the singleton pattern for STATE / RS_STATE without a full plan

DO:
- keep route handlers thin — business logic belongs in analyst/backend/routes/
- keep state objects in analyst/backend/ui/ui_state.py
- keep streaming WebSocket logic in runtime/transport/ only

---

## Frontend Rules

DO NOT:
- add React, Next.js, Vue, Svelte
- add Redux, MobX, Zustand
- add Vite, webpack, or any build step
- add websocket abstraction frameworks

Frontend must remain:
- lightweight vanilla JS
- explicit — no hidden reactivity
- server-rendered (index.html served from Python)
- deterministic — no hidden state machines
- debuggable — any engineer can read the JS cold

Common layer (analyst/frontend/static/js/common/) is the only approved abstraction.

---

## Most Important Principle

**Improve structure WITHOUT increasing conceptual complexity.**

A future engineer reading this code should find it *simpler*, not more abstract,
than before each refactor session. If a change adds a new mental model to understand,
it needs strong justification.
