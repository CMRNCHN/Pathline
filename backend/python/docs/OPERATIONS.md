# IVRSuite Operator Workflows

This document covers the three phases of IVRSuite operation: Plan, Run, and Review.

## Phase 1: Planning a Test Suite

### Define Your Target
1. Identify the IVR system: phone number, provider name, key flows
2. Document the known menu structure (if available)
3. List the test objectives: validate billing option, confirm account lookup, etc.

### Create a Suite
In the Live Map GUI:
1. Go to **Plan** workspace
2. Enter target phone number and any custom DTMF/speech inputs
3. Define "triggers" — prompt patterns that should receive specific responses
   - Example: "Press 1 for billing" → respond "1"
   - Example: "Account number?" → respond "4155552222"
4. Save suite (JSON)

Or use CLI:
```bash
./run_ivr_assessor.sh test-suite-wizard --output suites/billing_flow.json
```

### Bounds and Safety
- Max calls: how many dial attempts to allow
- Wall-clock cap: maximum test duration
- Allowlist: explicitly permit only approved phone numbers

## Phase 2: Live Operations

### Launch the GUI
```bash
./run_ivr_assessor.sh live-map-gui
```
Opens **Live Map** workspace — the main operator cockpit.

### Execute a Mapped Discovery
1. Enter target IVR phone number
2. Click **Start Discovery** (bounded DFS: explores one unknown branch per call)
3. View the live graph building in real-time
4. Monitor runtime metrics: call count, elapsed time, node count
5. Manual probing: send custom DTMF or speech to test specific paths
6. Stop when done (all interesting branches explored)

### Execute a Test Suite
1. Go to **Run** workspace
2. Select a suite from the library
3. Click **Run Suite**
4. Monitor results: pass/fail per route check, detailed logs
5. View success rate and confidence metrics

### Manual Testing
- **DTMF Input:** Send individual digit sequences (1, 2#, etc.)
- **Speech Input:** Type natural language responses (the system transcribes via Deepgram)
- **Recording:** All sessions auto-record for replay (stored locally)

## Phase 3: Review and Refinement

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
- **JSON** — Full state snapshot and event log
- **Mermaid** — State diagram (runnable in mermaid.live)
- **Markdown** — Human-readable summary

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
- Verify Deepgram API key is set in `.env`
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

IVRSuite enforces an **allowlist** to prevent accidental dialing of unauthorized numbers:

1. All targets must be in the approved list (`ALLOWLIST_NUMBERS` in config)
2. Manual DTMF entry is restricted by rate-limiting (max 1 per second)
3. Suite execution stops if any bound is exceeded (max calls, wall-clock time)
4. All operations are operator-initiated; no autonomous behavior

---

**Questions?** Check `.ai/PROJECT_STATE.md` for architecture overview or see the GUI tooltips.
