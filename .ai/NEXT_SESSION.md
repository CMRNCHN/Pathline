# Next Session Objectives

Last Updated: 2026-05-13

---

## Immediate Priorities

1. **Visual Timeline Scrubber & Media Synchronization**
   - Implement a graphical scrubber for the replay timeline.
   - Synchronize audio playback with the operational cursor.
   - Enable seek-to-event from the scrubber.

2. **WER benchmark smoke test**
   - Add one real WAV fixture to tests/fixtures/audio/
   - Run wer_benchmark.py end-to-end

3. **Autonomous Recovery Policies**
   - Define policy-driven recovery actions in `RecoveryManager`.
   - Implement automatic retry with backoff for transient failures.

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
