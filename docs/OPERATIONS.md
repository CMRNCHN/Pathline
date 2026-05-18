# Pathline Operator Workflows

This document covers the five phases of Pathline operation: Prep, Discover, Call/Live, Run, and Review.

## Phase 1: Prep (Preparation)

### Define Your Target
1. Identify the IVR system: phone number, provider name, key flows.
2. Verify environment readiness (Twilio, STT/TTS backends).
3. Set safety bounds: max calls, wall-clock cap, and allowlist.

### Configuration
In the **Prep** workspace:
1. Enter target phone number.
2. Define "triggers" — prompt patterns that should receive specific responses.
   - Example: "Press 1 for billing" → respond "1"
   - Example: "Account number?" → respond "4155552222"
3. Configure ready-responses for manual probing.

## Phase 2: Discover (Mapping)

### Execute a Mapped Discovery
1. Go to the **Discover** workspace.
2. Click **Start Discovery** (bounded DFS: explores one unknown branch per call).
3. View the live graph building in real-time.
4. Monitor discovery metrics: states found, unknown states, coverage, depth.
5. **Probe Control:** Send custom DTMF or speech to test specific paths manually.

## Phase 3: Call/Live (Interactive)

### Start a Live Call
1. Enter a target number in the header.
2. Click **Live** or **Start Live Call** to initiate an interactive session.
3. Use the **Operator Console** to monitor transcripts and events in real-time.
4. Use **Ready Responses** (pre-defined shortcuts) or manual DTMF to interact with the IVR.
5. **Supervisor Mode:** Listen in and override autonomous behavior if needed (hot-swap to manual control).

## Phase 4: Run (Automation)

### Execute a Test Suite
1. Go to the **Run** workspace.
2. Select a suite from the library.
3. Click **Run Suite**.
4. Monitor automation health: success rate, confidence, drift alerts.
5. View active autonomous runs and path previews.

## Phase 5: Review (Analysis)

### Load a Session
1. Go to **Review** workspace
2. Select a recorded session from the Replay Selector
3. Timeline loads automatically

### Navigate the Timeline
- **|<** — Jump to start of session
- **<** — Previous transcript
- **Position** — Current event (drag or type to scrub)
- **>** — Next transcript
- **>|** — Jump to end of session

### Inspect State
- **Graph Panel:** View the detected state machine at any point in time
- **Transcript Panel:** Read the full conversation (clickable to seek)
- **Metrics:** Call duration, events processed, state transitions

### Export Results
- **JSON** — Full state snapshot and event log.
- **Mermaid** — State diagram (runnable in mermaid.live).
- **Markdown** — Human-readable summary.
- **Evidence Bundle** — Portable package with audio, logs, and manifest.

### Refine the Map
- Edit states, transitions, and annotations
- Save as a new map or update existing
- Use refined map in future suite runs

## Troubleshooting

### Stream Server Won't Start
```bash
# Port 8081 may be in use
fuser -k -9 8081/tcp
# Then restart the GUI
```

### Replay Not Loading
- Check that the session exists (look in Replay Selector)
- Ensure recording file is present (check `.ivr_assessor/replays/`)
- Try reloading the browser

### Transcription Failing
- Verify STT service connectivity or API key is set in `.env`
- Check logs for auth errors
- Fall back to manual DTMF input

### ngrok Connection Lost
- Check if ngrok is running: `ngrok http 8081`
- Restart ngrok and update the GUI stream URL in Settings
- Use **Auto-Fix** button to restore connection

## Terminology

| Term | Meaning |
|------|---------|
| **State** | A detected IVR prompt with associated options (e.g., "Press 1 for billing") |
| **Transition** | A path from one state to another triggered by a response (e.g., press 1) |
| **Route** | A sequence of states from entry to final outcome |
| **Snapshot** | A saved replay state (enables fast forward in large sessions) |
| **Drift** | Deviation from expected prompts (new prompt detected where old one was expected) |
| **Coverage** | Percentage of discovered states vs. total possible states |

## Safety Model

Pathline enforces an **allowlist** to prevent accidental dialing of unauthorized numbers:

1. All targets must be in the approved list (`ALLOWLIST_NUMBERS` in config)
2. Manual DTMF entry is restricted by rate-limiting (max 1 per second)
3. Suite execution stops if any bound is exceeded (max calls, wall-clock time)
4. All operations are operator-initiated; no autonomous behavior

---

**Questions?** Check `.ai/PROJECT_STATE.md` for architecture overview or see the GUI tooltips.
