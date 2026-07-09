# Call Scripts

How to map and automate IVR navigation in PromptPath.

## Core idea

**Phrase-triggered, not timer-driven.**

You teach the navigator what to do when the IVR says something specific. Timeouts exist only as a last-resort fallback — they are unreliable because IVR prompt lengths vary.

```
IVR speaks → local STT → match phrase in script → send DTMF → new state → repeat
```

## Incremental mapping (discover mode)

This matches the workflow you described: map the IVR as you encounter new menus.

### 1. Start with an empty or partial script

Create a YAML file in `flows/` with just the entry state:

```yaml
id: my-bank-ivr
version: 1
name: My Bank
secrets: [account_pin, ssn_last4]
start_at: main_menu

states:
  main_menu:
    on_unknown: discover
    when: []
```

### 2. Run a call (or paste the IVR phrase manually)

When the IVR says something you haven't mapped yet, the navigator enters **discover** mode and pauses.

### 3. Add the mapping for that ground

Tell it:

- **What you heard** — `"enter your pin followed by pound"`
- **What to send** — `{account_pin}#` (secrets in braces)
- **Where to go next** — `ssn_entry` (new or existing state)

That gets appended to the script under the current state.

### 4. Repeat until `done`

Keep going state by state until you reach a phrase that delivers the status:

```yaml
- hear: ["your balance is", "claim status is"]
  capture: status
  goto: done
```

`capture: status` means "this transcript contains the answer we're looking for."

### 5. Save the script

Export from the web UI or copy your mappings into `flows/my-bank-ivr.yaml`. Next call runs automatically.

## Script format

```yaml
id: unique-id
version: 1
name: Human-readable name
secrets: [account_pin, ssn_last4]   # referenced as {account_pin}

timing:
  silence_after_prompt_ms: 800      # wait for IVR to finish speaking
  timeout_fallback_ms: 20000        # only if NO phrase matched

start_at: main_menu

states:
  state_name:
    listen: true
    on_unknown: discover   # discover | fail | wait
    when:
      - hear: ["phrase one", "alternate wording"]
        send: "1"                    # DTMF to inject
        goto: next_state
      - hear: ["enter your pin"]
        send: "{account_pin}#"       # secret → digits
        goto: pin_confirmed
      - hear: ["your balance is"]
        capture: status              # final answer captured here
        goto: done

  done:
    terminal: true
```

### Fields

| Field | Purpose |
|-------|---------|
| `hear` | Phrases to match in STT transcript (substring match, multiple aliases OK) |
| `send` | DTMF string. Use `{secret_name}` for PINs, account numbers, etc. |
| `goto` | Next state after sending |
| `capture` | Label for extracted status text |
| `on_unknown: discover` | Pause and let you map this prompt |
| `terminal: true` | Call complete |

## Branching (multiple IVR outcomes)

One state can split into **multiple branches** — each `when` entry listens for a different IVR response. This is how you model "the IVR could say X, Y, or Z after card entry."

```yaml
first_status_check:
  on_unknown: discover
  when:
    # Branch A — current
    - hear: ["account is current", "no payment due"]
      capture: first_status_current
      goto: done_current

    # Branch B — past due (needs more navigation)
    - hear: ["past due", "payment is required"]
      capture: first_status_past_due
      goto: past_due_menu

    # Branch C — invalid card (terminal)
    - hear: ["card not found", "invalid card number"]
      capture: first_status_invalid
      goto: done_error

    # Branch D — IVR wants more input first
    - hear: ["billing zip code", "verify your identity"]
      send: "{zip_code}#"
      goto: verify_then_recheck
```

### Rules

1. **First match wins** — list more specific phrases before generic ones
2. **`capture` names the branch** — use distinct keys (`first_status_current`, `first_status_past_due`) so you know which outcome fired
3. **`goto` can differ per branch** — terminal states for simple outcomes, new states when you need to navigate further
4. **Discover new branches live** — when the IVR says something unmapped, add a new `when` entry under that state
5. **No `send` needed for listen-only branches** — if the IVR just tells you status, only `capture` + `goto`

### Your script (fixed + extended)

```yaml
start_at: main_menu

states:
  main_menu:
    on_unknown: discover
    when:
      - hear: ["monitored or recorded", "touch tone"]
        send: "**11"
        goto: cc_number_entry

  cc_number_entry:
    on_unknown: discover
    when:
      - hear:
          - "please enter your full credit card number"
          - "credit card"
          - "telephone keypad"
        send: "{cc_num}#"
        goto: first_status_check

  first_status_check:
    on_unknown: discover
    when:
      - hear: ["account is current", "no payment due"]
        capture: first_status_current
        goto: done_current
      - hear: ["past due", "minimum payment"]
        capture: first_status_past_due
        goto: past_due_menu
      - hear: ["invalid", "not found"]
        capture: first_status_invalid
        goto: done_error

  done_current:
    terminal: true
  done_error:
    terminal: true
```

Full example: `flows/credit-card-status.yaml`

## Touch-tone mode

Many IVRs start in voice mode. Add an explicit step:

```yaml
- hear: ["press star for touch tone", "use your keypad"]
  send: "*"
  goto: main_menu
```

Or the IVR may be keypad-only from the start — skip that step.

## Tips for reliable phrase matching

1. **Use multiple `hear` aliases** — IVR wording varies: `"press 1"`, `"option 1"`, `"for account services press 1"`
2. **Match the end of the prompt** — wait for silence (`silence_after_prompt_ms`) before sending DTMF
3. **Don't match too early** — short phrases like `"press 1"` can false-match; prefer longer unique strings when possible
4. **Separate navigation from capture** — `send` steps move through menus; `capture` steps read the final status
5. **Avoid timers for navigation** — only use `timeout_fallback_ms` as a safety net

## Testing without a live call

```bash
source .venv/bin/activate
pip install -e packages/shared-python
python scripts/test-navigator.py flows/lab-account-status.yaml
```

Or use the web UI:
- **Flow Mapper** tab — visual graph editor (click nodes, split branches)
- **Navigator panel** — paste IVR phrases during a call

See [docs/call-scripts.md](./docs/call-scripts.md) for the full guide.

## Lab IVR

`flows/lab-account-status.yaml` maps to the Asterisk lab IVR.

**Full walkthrough:** [docs/lab-run.md](./lab-run.md)

```bash
./scripts/lab.sh
```

Register softphone `lab` / `lab` @ `127.0.0.1:5060`, dial extension `1000`, and use the web **Lab account status** script.

## Privacy

- Scripts and secrets stay on device
- Only `capture: status` transcript (or its hash) goes into encrypted status upstream
- DTMF templates reference `{secret}` — resolved locally, never sent to server
