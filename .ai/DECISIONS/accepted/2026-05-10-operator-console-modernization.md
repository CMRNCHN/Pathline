# Decision: operator console uses split polling and structured diagnostics without push changes

Date: 2026-05-10

## Context

The operator console modernization needed a richer session timeline, heartbeat strip,
graph context, and inspection drawer, but the repo constraints explicitly forbid
frontend framework changes, websocket protocol changes, and backend topology changes.

## Decision

Keep the existing explicit polling model and split rendering by concern:

- `/api/status` stays the fast poll for live caption, running state, mode, raw graph, and legacy log notices
- `/api/runtime-metrics` provides heartbeat, timer, queue, checkpoint, and runtime summaries
- `/api/runtime-diagnostics` provides the structured operator timeline and drawer inspection surfaces
- `/api/diagnose` remains slower/manual health visibility for the smoke tab

The frontend keeps a plain shared object in `common/state.js` and explicit DOM rendering in
`main.js`; no reactive framework, websocket push layer, or generalized state system is introduced.

## Consequences

- The UI gains structured operator visibility without altering deterministic runtime behavior.
- Timeline richness comes from already-exposed read-only endpoints rather than inferred client state.
- Live updates remain understandable and bounded, but multiple polling cadences must stay explicit
  and narrowly scoped to avoid accidental frontend complexity growth.
