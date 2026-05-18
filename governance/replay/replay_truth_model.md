# Replay Truth Model

## RP-001: Purity
Replay must be a pure function of events.
- `events -> state`
- No external side effects during replay.
- No dependency on live runtime singletons (e.g., `STATE`) for state reconstruction.

## RP-002: Temporal Truth
- Replay is the definitive record of what occurred during a session.
- Events must be recorded with nanosecond-precision timestamps (where available) and strict sequential ordering.

## RP-003: Deterministic Reconstruction
- Replay must reconstruct the exact state of the IVR graph, transcripts, and media-sync cursors at any point in the timeline.
- Snapshotting is allowed for performance optimization but must be verifiable against the full event stream.

## RP-004: Boundary Enforcement
- Replay consumes events from the append-only ledger.
- Replay does not feed control back into the runtime.
- Replay is observational and diagnostic.
