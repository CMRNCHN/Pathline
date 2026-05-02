# IVR Suite — Handoff to Next Agent

You're picking up an in-flight session. The previous agent (Opus) stopped here to save the user's quota. Read this end-to-end before touching anything.

---

## 1. What the project is

`/Users/cameroncohen/Developer/IVRSuite` — a Python tool that maps phone-tree IVRs.

- **Repo shape:** single tree at `backend/python/`. Source at `src/ivr_assessor/`, tests at `tests/`. Launcher at `run_ivr_assessor.sh` in repo root.
- **Stack:** Python 3.12, Typer CLI, a self-contained HTML/CSS/JS GUI served via stdlib `http.server` from `live_map_gui.py`. Twilio for telephony, Deepgram for transcription, ngrok for tunneling Twilio's media stream back to the local stream server.
- **How it runs:**
  ```bash
  cd ~/Developer/IVRSuite && ./run_ivr_assessor.sh live-map-gui
  ```
  GUI opens at `http://localhost:8080`. Stream server at `:8081`. The launcher sources `.env` if present.
- **CLI surface (key commands):** `live-map-gui`, `map`, `iterate-map` (new — see §3), `replay`, `dry-run`, `tracker-gui`, `sms-serve`, `call-template`, `batch-template`, `voice-generate`.

---

## 2. The user's frame of mind

The user opened this session frustrated: *"get this shit together its messy i want simple quick input, i want real mapping and i want it all to look nice and work well."* They're a non-developer using Cowork mode, watching this through the chat surface — they cannot see Figma renderings unless the agent attaches inline screenshots.

**Decisions already collected via AskUserQuestion (do not re-ask):**

| Question | User's pick |
|---|---|
| What part of IVRSuite is messy? | `ivr_mapper` module |
| What does "real mapping" mean? | Both accuracy AND visualization |
| What does "simple quick input" look like? | One field: phone number, hit go |
| 30s cap behavior? | Soft cap, finish the current prompt |
| Discovery loop strategy? | Deepest unexplored option (DFS) |
| Loop surface? | CLI command (only) |
| Stopping condition? | Two consecutive no-progress calls |
| Redesign — new file or existing? | New file, propose 2-3 layouts |
| Translate Figma to code? | Yes — rebuild `live_map_gui.py` to match |
| DTMF vs speech detection? | **Strict — only `[0-9*#]` is DTMF, else speech** |
| Chosen redesign direction? | **A — Cockpit** |
| Iterate in Figma first? | Yes (but blocked, see §6) |
| Cockpit rail width? | "your choice" — picked **320px** |
| What's pinned in the rail? | Smart input + keypad + presets |
| Smart input look? | Single line, focused glow |
| Auto-pilot toggle location? | Top of the rail, above smart input |
| Test-suite priority? | "recomeneded" — interpret as **build test suite first, redesign later** |
| Test format? | Both — JSON ground truth + GUI editor |
| Report contents? | Full transcript per case |

---

## 3. What's already done in this session (DO NOT REDO)

### Mapper accuracy — `src/ivr_assessor/ivr_mapper.py` (rewritten)
- Prompts grouped by a normalized key (`_normalize_prompt`): collapses whitespace, strips trailing punctuation, lowercases. So `"Welcome."` and `"Welcome"` merge.
- New `PromptNode.announced_options: set[str]` — every digit the IVR mentioned in the menu, parsed via `classify_prompt(...).options`. Separate from `branches` (which only tracks pressed keys), so the GUI can show "walked X of Y announced."
- Confidence is now a running average (`_accumulate_confidence`), not `max()`.
- Branches sort numerically (`_branch_sort_key`): 1, 2, 10 — not 1, 10, 2.

### Multi-session — `src/ivr_assessor/multi_session.py`
- `combined_graph()` merges `announced_options` across sessions. Imports `_branch_key_value` from `ivr_mapper`.

### Discovery loop — NEW `src/ivr_assessor/discovery_loop.py`
- `plan_dfs_path(graph)` → list of digits. Returns the deepest planned path that ends at an unexplored announced option. Walks through explored branches via `next_prompts`. Handles cycles via `seen` frozenset.
- `run_discovery_loop(target, runner, *, max_calls=12, no_progress_limit=2, initial_mapper=None)` → `(IvrMapper, DiscoveryReport)`. Runner is injected so the loop is testable. Stops on: (a) every announced option walked, (b) N consecutive calls add zero new nodes, (c) max_calls hit.

### LiveMappingSession — `src/ivr_assessor/live_map.py`
Two new optional fields:
- `wall_clock_cap_s: float | None = None` — soft 30s cap. Checked at the **top** of each loop iteration, so the current prompt finishes before we bail. Uses `time.time` by default; injectable via `_clock` for tests.
- `forced_branches: list[str] = field(default_factory=list)` — pre-planned DTMF path the discovery loop wants this session to walk first. The session pops a digit when its menu announces that digit; otherwise falls through to existing `choose_candidate` exploration.

### CLI — `src/ivr_assessor/cli.py`
New `iterate-map` command:
```bash
./run_ivr_assessor.sh iterate-map --target-number +18005550199 \
  --max-calls 12 --wall-clock-cap-s 30
```
Wires `LiveMappingSession` into the discovery loop. Currently uses `RecordingTelephonyClient` + `ScriptedPromptSource` (so it dry-runs with `--prompt` flags). For real Twilio use, the runner will need swapping for `TwilioTelephonyClient`. Marked as a follow-up.

### GUI polish — `src/ivr_assessor/live_map_gui.py`
- **Header phone field** auto-formats US numbers as you type (`_formatPhone`), shows a green status dot when filled (`.has-value` toggled by `_refreshTargetState`), and submits on Enter.
- **Manual override sections** (Paste & Fire / TTS / Manual Transcript) collapsed into one `<details class="adv">` disclosure. Default state shows just keypad + presets.
- **Empty-state copy** updated to match the new flow.
- **Node footer** shows a `walked / announced` coverage badge (`badge-cov`, purple) using `node.announced_options`.
- **Layout engine** (`buildLayout`) replaced. Old version: recursive width-summing, broke on shared/cyclic prompts. New version: BFS depth assignment, parent centering over children's bounding box, per-row x-slot sweep to guarantee no overlap, fall-back for orphans. **Back-edges** (child at same-or-earlier depth) draw as dashed bezier from parent's right side into child's left, separating "going deeper" from "looping back."

### Tests — NEW `tests/test_discovery_loop.py`
Covers `plan_dfs_path` (4 cases) and `run_discovery_loop` (3 cases: stops on no-progress, stops on all-walked, respects max_calls).

### Figma file — created
- File: **IVR Mapper — Redesign Directions**
- File key: `WDaOyHEifp9cySf8MC1Wxh`
- URL: https://www.figma.com/design/WDaOyHEifp9cySf8MC1Wxh
- Three frames live:
  - `1:2` — **A. Cockpit** (1440×900) ← user picked this one
  - `1:562` — B. Split (1440×900)
  - `1:1118` — C. Single column (480×980)
- Note: file is in user's *starter-tier* "no" team (`1575980893744480496`) because creating in the pro team (`1358513349074809327`) returned "Invalid planKey" — likely an MCP bug. Worth retrying the pro key in a fresh session.

---

## 4. What's pending / what to do next

In **user-stated priority order:**

### Priority 1 — Test-suite runner (the user's most recent ask)
Build keyword-triggered DTMF/speech responses + batch test cases + transcript report. Spec from the user:

> "I want to have words within prompts that trigger pre-entered dtmf responses where i can load up a series of tests with different responses and you let me know via recording or transcript what the ivrs responses are"

**Design (decided this session):**
- **Test case JSON schema:**
  ```json
  {
    "name": "Pay bill — account 12345",
    "target_number": "+18005550199",
    "initial_path": ["1", "3"],
    "triggers": [
      {"phrase": "account number", "response": "12345", "kind": "dtmf"},
      {"phrase": "billing department", "response": "billing please", "kind": "speech"}
    ]
  }
  ```
- **Suite file** = a JSON array of test cases.
- **Runner** = new module `src/ivr_assessor/test_suite.py`. Reuses `LiveMappingSession` per case. Triggers fire when the live transcript contains the phrase (case-insensitive substring). Capture full transcript via the existing Deepgram callback path in `live_map_gui.py:_on_transcript`.
- **Output:** per-case JSON report at `~/.ivr_assessor/reports/<suite>/<case>.json` with: every prompt, every action sent, which triggers fired, final node, full timeline. Plus a Markdown summary.
- **GUI:** add a "Test Suite" tab in the left sidebar (next to Controls/Activity/Flows/Library). Editor reads/writes the same JSON files. Reuses existing Flow editor patterns where possible (`renderFlowEditor` in `live_map_gui.py`).

There is already a `Flow` system in the GUI (`flow-list`, `flow-item`, `runFlow`, `tickFlow`, `checkFlowAgainstTranscript`) — read it before designing the test suite. The test suite is conceptually a *batch* of flows with reporting. **Don't duplicate. Extend.**

### Priority 2 — Smart input with strict DTMF detection (task #9)
**Where:** `src/ivr_assessor/live_map_gui.py`. Replace the three manual sections inside `<details class="adv">` with a single input.

**Spec:**
- Single-line input box. CSS: `bg-2` background, `accent` border at 0.55 opacity, accent glow shadow.
- Detection chip in top-right of the input wrapper:
  - `⚡ DTMF` (accent color) when text matches `^[\s0-9*#]+$` after trimming
  - `🗣 Speech` (accent2 / purple) otherwise
  - Empty → faded "Auto-detect" label
- Hint line below: `digits, *, # → DTMF · everything else → speech`
- Send button (compact, accent gradient, `Send ↵`)
- Submit on Enter. The send handler dispatches to either `sendDigitSequence` (DTMF) or `sendSay` (speech) based on detection.
- Live re-classification on every `input` event.

JS regex: `/^[\s0-9*#]+$/` after `.trim()`. Empty string → no chip.

### Priority 3 — Translate Cockpit (Frame A v1) to `live_map_gui.py` (task #10)
The v1 Cockpit is in Figma. Rail dimensions: 320px wide. Pinned content: smart input + keypad + presets. Auto-pilot toggle moves to top of rail (currently in the toolbar above the map).

Preserve all existing JS hooks: `poll`, `padPress`, `sendPrompt`, `renderFlow`, `pasteFire`, `firePreset`, `runFlow`, etc. Only the markup, CSS, and where buttons live should change.

### Priority 4 — Run pytest end-to-end
Sandbox bash was offline this whole session (`Workspace still starting...`) so **no test ran**. The previous agent traced through every test case mentally and believes them to pass, but verify:
```bash
cd backend/python && .venv/bin/python -m pytest -q
```
If anything fails, look first at `tests/test_multi_session.py:test_multi_session_keeps_independent_session_state` — the assertion `branches == {}` for an unwalked prompt was a thing we redesigned around (the `announced_options` field exists specifically so this assertion can still hold). If that test fails, the redesign regressed something.

### Priority 5 — Fix the stream auth issue
User pasted this log:
```
[dial] calling +18009505114…
[twilio] call SID: CAf1195697ec2052a8f3714b16d8537f55
[twilio] call CAf1195697… status: in-progress
[stream] rejected unauthorized connection to /stream
[ok] session ended cleanly
```
Twilio connected to the stream server but the server rejected it as unauthorized. There's a token in the same paste:
```
token=RXIjncUWxxTkt8-xzKtIpTefkdg2yWs3vrrzaBsBzcQ
```
Look at `streaming_server.py:default_stream_auth_token` and `append_stream_auth_token`. Suspected issue: the GUI's `stream_url` setting either (a) doesn't get the token appended when configured manually, (b) gets a stale token from a previous server boot, or (c) the server regenerates the token at boot but the GUI cached the old one. The fix is probably making the token deterministic per environment, or auto-refreshing the GUI's saved stream URL each time the persistent stream server starts.

The GUI already does some of this in `_run_session_thread`:
```py
live_ngrok = _detect_ngrok_url()
if live_ngrok:
    corrected = _to_wss(live_ngrok)
```
…but `_to_wss` calls `append_stream_auth_token` which presumably reads the current server's token. Trace whether the persistent stream server's token is what Twilio gets sent. If the user manually pasted an old `wss://…?token=…` URL into Settings, that's stale.

### Priority 6 — Cockpit v2 in Figma (only if redesign requested again)
Was being built when the Figma starter-plan rate limit hit. The v2 was supposed to differ from v1 by: 320px rail, auto-pilot toggle moved into the rail (above the smart input), single-line smart input replacing the three manual sections, kept presets at the bottom. **Don't bother with this unless the user asks again — the v1 is already a fine basis to translate from.**

---

## 5. Code map (where to find what)

```
backend/python/src/ivr_assessor/
├── __main__.py               # entry: `python -m ivr_assessor`
├── cli.py                    # Typer CLI; live-map-gui, map, iterate-map (new), …
├── live_map.py               # LiveMappingSession (now has wall_clock_cap_s, forced_branches)
├── live_map_gui.py           # ~3000 LOC HTML+CSS+JS+Python http server in one file
├── ivr_mapper.py             # IvrMapper + PromptNode + announced_options (rewritten)
├── multi_session.py          # MultiSessionOrchestrator + combined_graph (updated)
├── discovery_loop.py         # NEW — plan_dfs_path + run_discovery_loop
├── prompt_intelligence.py    # classify_prompt + extract_branch_hint
├── exploration.py            # choose_candidate (least-explored)
├── scenario_runner.py        # choose_next_action
├── event_ledger.py           # EventLedger
├── reporter.py               # Markdown report generation
├── streaming_server.py       # WebSocket Twilio media stream + Deepgram bridge
├── twilio_client.py          # Twilio REST + voice TwiML
├── transcription.py          # Deepgram client
├── response_library.py       # Audio clip library
├── ai_voice.py               # OpenAI TTS
├── batch_template.py         # Existing batch runner (read before building test-suite)
├── call_template.py          # Templated call plans
├── phone_tracker_gui.py      # Separate tracker GUI (tkinter) — different UI
├── live_map_gui.py           # ← redesign target
├── replay_mode.py            # Replay traces
├── map_store.py              # Saved-map persistence (JSON files)
├── execution_controller.py   # Allowlist/dial gating
└── models.py                 # CallEvent, CallPlan
```

```
backend/python/tests/
├── test_ivr_mapper.py             # contract: graph keyed by canonical prompt text
├── test_prompt_intelligence.py
├── test_live_map.py               # contract: branches[X].next_prompts populated
├── test_multi_session.py          # contract: unwalked prompt → branches == {}  ← critical
├── test_discovery_loop.py         # NEW
├── test_dry_run.py
├── test_event_ledger.py
├── test_execution_controller.py
├── test_reporter.py
├── test_response_library.py
└── test_scenario_runner.py
```

---

## 6. Environment notes / gotchas

- **Sandbox bash was offline the entire session.** Every `mcp__workspace__bash` call returned `"Workspace still starting"` and never recovered. No test ran, no shell verification done. The next agent should try bash early and not block on it.
- **Computer-use couldn't resolve any terminal app** by name (Terminal, iTerm, Warp, Ghostty, Alacritty all returned `notInstalled`). Likely a Cowork-side allowlist issue. Don't try to auto-launch a terminal — give the user the command to paste.
- **Figma starter-plan rate limit is hit** for the existing file (`WDaOyHEifp9cySf8MC1Wxh`). Use the pro team key `1358513349074809327` for any new file (the previous attempt with that key was rejected, but it might have been a transient bug — worth retrying once).
- **Tokens / secrets in user logs.** The user pasted `token=RXIjncUWxxTkt8-xzKtIpTefkdg2yWs3vrrzaBsBzcQ`. Treat as their own credential leakage; don't repeat it in your responses, don't transmit it anywhere.

---

## 7. Suggested first message from the next agent

Something like:

> Caught up on `HANDOFF.md`. Starting on Priority 1 — the test-suite runner. First step is reading `batch_template.py`, `scenario_runner.py`, and the existing Flows code in `live_map_gui.py` so I extend rather than duplicate. Will report back with a concrete plan before writing code.

That keeps you out of expensive Opus territory while preserving every decision that's been made.

---

*Generated by the previous agent (Opus) before stopping to save quota. Anything in this file marked "spec" or "decided" is settled with the user — don't re-ask.*
