# Decision: Bounded runtime observability stays inline with existing state surfaces

Date: 2026-05-09

## Context

External FasterWhisper model provisioning is temporarily blocked by network policy.
We still need stronger operational visibility around startup, websocket lifecycle,
cleanup sequencing, queue behavior, replay artifacts, and stale runtime detection.

## Decision

Add observability through the existing `AppState`, `live_map_gui.py`, and
`streaming_server.py` metrics surfaces instead of introducing a separate event bus,
monitoring subsystem, or new runtime abstraction.

Specifically:

- keep startup chronology in `AppState.startup_events`
- add a bounded runtime checkpoint ring buffer to `AppState`
- instrument prompt queue depth via an observable queue wrapper
- expose websocket lifecycle chronology and cleanup counters from `StreamingServer`
- expose replay/report/snapshot directory summaries from the existing GUI metrics route

## Why

- Preserves current topology and websocket semantics
- Preserves replay semantics and deterministic startup behavior
- Improves operational visibility without broadening architecture
- Keeps the work useful even while STT model provisioning is blocked

## Consequences

- Runtime metrics are richer and more actionable before full media-flow validation resumes
- Deterministic smoke tests can validate lifecycle and cleanup behavior without real STT
- No new dependencies or orchestration layers were introduced
