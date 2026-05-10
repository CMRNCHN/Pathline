# Next Session Objectives

Last Updated: 2026-05-07

---

## Immediate Priorities

1. **Backend event bus** (event_bus.py)
   - Centralize event dispatch between streaming_server.py and live_map_gui.py
   - Replace ad-hoc callback registration with a typed event bus
   - See RUNTIME_SPLIT_POINTS.md for split plan

2. **Session snapshots**
   - Capture full session state at end of each run
   - Store in storage/snapshots/
   - Enable replay from snapshot

3. **WER benchmark smoke test**
   - Add one real WAV fixture to tests/fixtures/audio/
   - Run wer_benchmark.py end-to-end

4. **Smoke test local pipeline**
   - Set STT_BACKEND=faster-whisper and TTS_BACKEND=piper in .env
   - Run ./run_ivr_assessor.sh live-map-gui
   - Make a real test call

---

## What NOT to Do Next Session

- Do NOT add a frontend framework
- Do NOT redesign the hot path
- Do NOT increase abstraction depth beyond what's needed for the event bus
- Do NOT split streaming_server.py yet (see RUNTIME_SPLIT_POINTS.md)

---

## Files to Read First

- .ai/HANDOFF.md — current state summary
- .ai/RUNTIME_SPLIT_POINTS.md — documented future split points
- backend/python/src/ivr_assessor/backend/routes/ — current route structure
- backend/python/src/ivr_assessor/live_map_gui.py — thin dispatcher (post-split)
