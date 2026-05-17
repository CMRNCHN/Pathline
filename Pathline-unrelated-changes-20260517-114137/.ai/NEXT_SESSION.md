# Next Session Objectives

Last Updated: 2026-05-15

---

## Immediate Priorities

1. **Real-call readiness**
   - Create a working `.env` with Twilio credentials, `IVR_STREAM_AUTH_TOKEN`, and the selected tunnel URL.
   - Decide whether local demos should default to `STT_BACKEND=simulated` until real STT/TTS assets are provisioned.

2. **TTS provisioning**
   - Install/provision Piper and set `PIPER_VOICE`, or switch `TTS_BACKEND=openai` with a valid `OPENAI_API_KEY`.
   - Keep the default hot path deterministic and bounded.

3. **Recovery policy refinement**
   - Decide whether bounded operator guidance in `RecoveryManager` is enough or whether explicit retry tiers are still needed.
   - Keep recovery deterministic and replay-visible.

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
