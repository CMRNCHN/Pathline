# Decision: bounded transcript simulation sits behind `STT_BACKEND`

Date: 2026-05-10

## Context

We need to validate downstream transcript handling, queue/checkpoint visibility,
websocket cadence, runtime metrics, and cleanup behavior before the real
FasterWhisper CT2 model is provisioned locally.

## Decision

Add a deterministic `STT_BACKEND=simulated` backend that uses the existing
`create_transcriber()` seam and the current `StreamingServer` WebSocket loop.

The simulated backend emits a fixed transcript script on buffered media chunks
instead of introducing a new injection route, event bus, or replay format.

## Why

- Preserves current topology and websocket contracts.
- Preserves replay/runtime contracts.
- Exercises the real downstream transcript filter and callback bridge.
- Avoids hot-path changes to the production FasterWhisper path.
- Keeps the validation path bounded and deterministic.

## Consequences

- Operational probes can validate transcript flow without CT2 availability.
- The simulation validates downstream behavior only; it does not validate
  FasterWhisper model loading, inference timing, or PCM/VAD segmentation.
