# Pathline Pulse

A macOS menu bar app that probes an IVR through a **local Asterisk** instance
over [ARI](https://docs.asterisk.org/Configuration/Interfaces/Asterisk-REST-Interface-ARI/).
No cloud, no Twilio, no Deepgram — it originates a call, walks the menu by
sending DTMF when each prompt ends, and shows live probe state in the menu bar.

```
tools/ivr_beacon/
├── setup.sh                         # build + ARI preflight (run this first)
├── BeaconApp/
│   ├── Package.swift                # Swift 5.9, macOS 14+, no dependencies
│   └── Sources/PathlinePulse/
│       ├── PulseApp.swift           # menu bar UI + "Run Probe" trigger
│       ├── PulseState.swift         # @MainActor FSM, single source of truth
│       ├── AsteriskClient.swift     # ARI WebSocket in / HTTP control out
│       └── Config.swift             # PULSE_* env-var configuration + defaults
├── ivr/ · launchd/                  # legacy Twilio batch system (superseded — see below)
```

## How a probe runs

```
Run Probe ─▶ reserve channel id ─▶ ARI originate(channelId)
                                       │
        StasisStart ─▶ enable TALK_DETECT
        ChannelTalkingFinished ─▶ FSM advance ─▶ send menu DTMF
        ChannelTalkingFinished ─▶ FSM advance ─▶ send card DTMF
        ChannelTalkingFinished ─▶ FSM advance ─▶ hangup
        ChannelDestroyed ─▶ probe complete
```

All progression is driven by ARI events — there are no timers in the app. The
one timing knob is `TALK_DETECT`'s silence threshold (see calibration below).

## Quick start with Docker (no carrier, no real call)

The repo ships an Asterisk container with ARI enabled and a built-in test IVR
(extension `1000`). This is the fastest way to exercise the full
`originate → Stasis → TALK_DETECT → DTMF → hangup` loop without a SIP trunk or
a real phone call — point Pulse at a `Local` channel that runs that IVR:

```bash
# 1. Build & start the ARI-capable Asterisk container (from infrastructure/)
docker compose -f infrastructure/docker-compose.yml up asterisk -d

# 2. Confirm ARI is up (and the ari:ari credentials work)
curl -fsS "http://127.0.0.1:8088/ari/asterisk/info?api_key=ari:ari"

# 3. Build Pulse
bash tools/ivr_beacon/setup.sh

# 4. Loop against the container's IVR — no carrier involved
PULSE_ENDPOINT="Local/1000@ivr-test" \
PULSE_MENU_DIGITS="2" \
PULSE_CARD_DIGITS="5" \
  ./tools/ivr_beacon/BeaconApp/.build/release/PathlinePulse
```

The menu bar shows an **ARI status line** (green = connected) and **Run Probe**
is disabled until the WebSocket is up — so a down/misconfigured Asterisk is
visible immediately instead of looking frozen. Click **Run Probe** and watch the
row advance; the transcript shows diagnostics (`⚙ stasis · bridged`, `▸ prompt
started`, `→ menu`, `‹dtmf …›`) so you can see exactly why the FSM does or
doesn't move.

The container IVR's prompt semantics don't match a real card IVR — that's fine;
the point is to verify the event loop fires end to end and to calibrate
`PULSE_TALK_SILENCE_MS` / `PULSE_MIN_PROMPT_MS` against real spoken prompts
before you ever place a carrier call.

> **Loopback media note.** On a `Local` loopback the control leg has no audio
> unless it is bridged, so Pulse puts the channel into a mixing bridge on
> StasisStart — without it, TALK_DETECT never fires and the probe stalls in
> `waitingForGreeting`. This bridge path is new and not yet confirmed against a
> live run; the in-app diagnostics above are how you confirm it (you should see
> `▸ prompt started` lines appear).

### Tier A — real call over a SIP trunk

The loopback proves connect → originate → prompt-detection → DTMF → hangup
mechanics, but its synthesized audio doesn't reach the control leg, so the only
*true* end-to-end test is a real call — which needs an outbound **SIP trunk**.
The container ships one, rendered at startup from env vars so no credentials are
ever committed (`infrastructure/.env` is gitignored).

You bring the trunk. Two privacy-focused shapes are supported:

- **Privacy-respecting ITSP (registration) — active.** Sign up with a small
  BYO-SIP provider. Calling a **toll-free** line (like `+18009505114`) is free
  to originate, so a free-tier account can do it. Put the creds in
  `infrastructure/.env`:
  ```bash
  TRUNK_HOST=sip.your-provider.example
  TRUNK_USER=your-account
  TRUNK_PASS=your-secret
  # TRUNK_FROM_USER=your-account   # optional, defaults to TRUNK_USER
  ```
- **Local GSM/analog gateway (IP-auth) — placeholder.** A SIM/POTS box on your
  LAN; the most private option, no provider. Uncomment the `[gateway]` block in
  `infrastructure/docker/asterisk/pjsip_trunk.conf.template`, set `GATEWAY_IP` in
  `.env`, and dial via `@gateway` below.

Then rebuild the container and dial a real number through the trunk by selecting
the *Environment (PULSE_\*)* template (or any template whose endpoint routes the
trunk):

```bash
docker compose -f infrastructure/docker-compose.yml up asterisk -d --build
# container log should show: "SIP trunk enabled for <host>"

PULSE_ENDPOINT="PJSIP/18009505114@trunk" \
  ./tools/ivr_beacon/BeaconApp/.build/release/PathlinePulse
```

Enter your real test card in the menu bar, Run Probe, and the full loop fires
against the live IVR. On a real call the mixing bridge is harmless — media
already flows from the far end, so TALK_DETECT works. With no `TRUNK_*` set the
trunk is inert and the container behaves exactly as before.

## Asterisk prerequisites

Pulse needs a reachable Asterisk (local by default) with ARI/HTTP enabled and a
Stasis application named `pulse`. Minimum config:

`http.conf`
```ini
[general]
enabled = yes
bindaddr = 127.0.0.1
bindport = 8088
```

`ari.conf`
```ini
[general]
enabled = yes

[ari]              ; user:pass — matches the default PULSE_ARI_API_KEY "ari:ari"
type = user
password = ari
```

`extensions.conf` — hand calls to the `pulse` Stasis app, and provide an
outbound path (a PJSIP trunk/endpoint) so `PJSIP/<number>` can dial out.

Verify ARI is up before launching the app:
```bash
curl -fsS "http://127.0.0.1:8088/ari/asterisk/info?api_key=ari:ari"
```
`setup.sh` runs this same check for you.

## Build & run

```bash
bash tools/ivr_beacon/setup.sh                 # builds + checks ARI
./tools/ivr_beacon/BeaconApp/.build/release/PathlinePulse
```

Then click the waveform icon in the menu bar and choose **Run Probe**.

## Configuration (env vars)

Every value has a default that runs against a stock local Asterisk. Override any
of them in the environment **before launching the app** — no recompile needed.

| Variable | Default | Purpose |
|---|---|---|
| `PULSE_TARGET` | `+18009505114` | IVR number to dial |
| `PULSE_ENDPOINT` | `PJSIP/<PULSE_TARGET>` | full ARI originate endpoint; override to e.g. `Local/1000@ivr-test` for a no-carrier loopback test |
| `PULSE_MENU_DIGITS` | `**11` | DTMF sent after the greeting |
| `PULSE_CARD_DIGITS` | _(empty)_ | DTMF sent after the card prompt. **No default** — type the card per-run in the menu bar; only set this for an automated loopback test. See [Cardholder data](#cardholder-data-pci). |
| `PULSE_ARI_HOST` | `127.0.0.1` | Asterisk ARI host |
| `PULSE_ARI_PORT` | `8088` | Asterisk ARI port |
| `PULSE_ARI_API_KEY` | `ari:ari` | ARI `user:pass` |
| `PULSE_ARI_APP` | `pulse` | Stasis application name |
| `PULSE_TALK_SILENCE_MS` | `1500` | TALK_DETECT silence threshold (ms) — **needs calibration** |
| `PULSE_MIN_PROMPT_MS` | `2000` | minimum sustained-speech duration to count a prompt (ms) — **needs calibration** |

Example — point Pulse at a different IVR (type the card in the menu bar):
```bash
PULSE_TARGET="+18005551234" PULSE_MENU_DIGITS="1" \
  ./tools/ivr_beacon/BeaconApp/.build/release/PathlinePulse
```

## Templates & card entry (menu bar)

The dropdown has a **template picker** and a **card-number field**, so you don't
need env vars for routine runs:

- **Template** — selects where to call and how to reach the card prompt
  (endpoint + menu digits). Built-ins: *Environment (PULSE_\*)* (mirrors your env
  vars), *Local test IVR (container)*, *Card status line*.
- **Card number** — typed per run; never stored in a template. Run Probe is
  disabled until it's filled in.

Define your own templates by dropping a JSON array at `~/.pulse/templates.json`
(or point `PULSE_TEMPLATES` at a file). Each entry:

```json
[
  { "id": "acme", "name": "Acme card line", "endpoint": "PJSIP/+18005551234",
    "target": "+18005551234", "menuDigits": "**11" }
]
```

The env vars still work and show up as the *Environment* template.

## Cardholder data (PCI)

If you ever feed Pulse a **real** card number, you are handling cardholder data
and are in PCI DSS scope. An IVR probe is structurally unable to avoid this:
sending a card as DTMF requires the cleartext digits at send time, so you cannot
tokenize your way out of scope the way an e-commerce checkout can. Treat the
controls below as the minimum and pair them with a retention policy and an SAQ.

Pulse implements these data-protection controls in code:

- **PAN never enters the transcript.** `ChannelDtmfReceived` is logged as
  `‹dtmf received›` with the digit value redacted, so an IVR/loopback echo can't
  reconstruct the card number into the on-screen transcript. The card send itself
  is logged only as a digit *count* (`→ card (N digits)`), never the digits.
- **Minimal in-memory residency.** The card number is wiped from the probe the
  instant it's handed to the dialer (one FSM transition), and the menu-bar field
  is cleared the moment Run Probe fires. The PAN is never retained between runs.
- **No card-shaped default.** `PULSE_CARD_DIGITS` defaults to empty; nothing
  card-shaped is baked into the binary or pre-filled into the field.
- **PAN never appears in a URL.** DTMF (which carries the card number) is sent in
  the ARI request **body**, never the query string. A PAN in a URL leaks into
  access logs, proxy logs, and tracing systems *even under TLS* — TLS protects
  the wire, not the log files. The body keeps it out of every URL on the path.
- **Leak regression tests.** `Tests/PathlinePulseTests/PANLeakTests.swift` fails
  the build if a 13–19 digit PAN ever reaches a transcript (including via echoed
  DTMF) or survives in `CallProbe` after dialing. Run with `swift test`.

Operator responsibilities (not enforced in code):

- **Keep ARI on loopback or TLS.** The client still speaks cleartext `http://`,
  and the request *body* and the `api_key` credential travel over it. On loopback
  (`PULSE_ARI_HOST=127.0.0.1`, the default) nothing reaches a wire; for any remote
  ARI, terminate it over TLS.
- **Don't log request bodies.** The PAN is now out of URLs, but it's in the POST
  body — ensure Asterisk (and any proxy) isn't configured to log request bodies.
- Define and enforce a **retention policy**: delete any temporarily stored card
  as soon as the subscriber's payment clears. Don't persist PANs to disk.
- Complete the appropriate **SAQ** (likely SAQ D, since you store and process
  card data) and keep an access log + key-management story for anything at rest.

> **Verify on a live ARI.** The DTMF-in-body path relies on Asterisk reading the
> `dtmf` parameter from the JSON body. This is the documented ARI behaviour but
> has not been exercised here (no Asterisk/Swift toolchain in CI) — confirm the
> first live probe still advances past the card prompt before trusting it.

## DTMF transport probe (`probe-ari-dtmf.sh` + `ari-controller.js`)

The PCI note above hinges on one unverified fact: that ARI reads `dtmf` from the
request **body**. To settle that on a live ARI without trusting the Swift client
(whose request builder would only confirm its own assumption), two standalone,
contamination-free tools sit beside Pulse:

- **`probe-ari-dtmf.sh`** — a pure-curl probe that fires the same DTMF POST as
  JSON and as form-urlencoded, prints the raw wire trace + HTTP status for each,
  and **decides nothing**. It aborts unless given a genuinely live channel id, so
  a 404 from route resolution can't masquerade as encoding evidence.
- **`ari-controller.js`** — a standalone Node ARI controller that holds the
  channel live and logs DTMF as an **independent witness**. It claims the Stasis
  app, answers, and (like the Swift client) **bridges the channel into a mixing
  bridge to pump media** — a bare `answer()` leaves a `Local` loopback without
  two-way media. It is deliberately separate from Pulse so the thing under test
  isn't also the test fixture. The Node controller never interprets IVR
  behavior. It answers channels, maintains media flow, and records observable
  Asterisk events. The native IVR remains the sole authority for call
  progression and menu state.

The dialplan is **unchanged**: extension `1000` stays the native IVR, which is
the "did the IVR advance" ground truth (case A vs B). You reach Stasis through
the originate call, not the dialplan.

```bash
# 1. Asterisk up
docker compose -f infrastructure/docker-compose.yml up asterisk -d

# 2. Controller (run INSTEAD of Pulse — never both on the same app)
npm --prefix tools/ivr_beacon install      # one-time: pulls ari-client
node tools/ivr_beacon/ari-controller.js

# 3. Originate a live channel into the pulse app (far end runs the real IVR)
curl -sS -X POST \
  "http://127.0.0.1:8088/ari/channels?endpoint=Local/1000@ivr-test&app=pulse&channelId=probe-1&api_key=ari:ari"

# 4. Fire the probe; watch the controller log for the DTMF_RECEIVED witness
./tools/ivr_beacon/probe-ari-dtmf.sh probe-1
```

Then classify by hand from two facts per variant — the probe's `HTTP_STATUS` and
whether the IVR advanced (controller `DTMF_RECEIVED` + the echo/hangup on the
native IVR): **A** 2xx and advanced → no code change; **B** 2xx but nothing
happened → accepted-not-applied; **C** 4xx → rejected. Only then is the single
encoding cell touched.

> Two WebSocket subscribers fight over each channel. Run either the controller
> **or** the Swift Pulse app against `pulse`, not both.

## Calibration (do this with real traffic)

`PULSE_TALK_SILENCE_MS` and `PULSE_MIN_PROMPT_MS` are uncalibrated defaults:

- **Talk silence too low** → TALK_DETECT fires mid-prompt on a natural pause, so
  DTMF is sent before the IVR finished speaking. **Too high** → latency before
  every DTMF send. (Asterisk's own default is 2500 ms.)
- **Minimum prompt duration** guards against advancing on a short first sentence
  of a multi-sentence prompt. Raise it if the FSM jumps ahead; lower it if short
  but real prompts are being ignored.

Tune both against your IVR by overriding the env vars between runs and watching
the transcript in the menu bar — no rebuild required.

## Testing checklist

1. `bash tools/ivr_beacon/setup.sh` — confirm it builds and reports **ARI reachable**.
2. Launch the binary; confirm the waveform icon appears in the menu bar.
3. Pick a template and **type the card number** in the field (it's never stored).
4. Click **Run Probe**. Watch the dropdown advance through the phases:
   `connecting → inCall`, then `waitingForGreeting → waitingForCardPrompt →
   waitingForResult → done`, with `→ menu`, `→ card (N digits)`, `→ hangup` and
   `‹dtmf received›` lines appearing in the transcript (card digits redacted).
5. Confirm the call hangs up cleanly and the probe shows `completed`.

> **Status:** the full `originate → StasisStart → TALK_DETECT → DTMF → hangup`
> path has **not** yet been exercised against a live Asterisk end to end. The
> FSM, ARI wiring, and UI are in place and verified against the ARI reference;
> the first live run is the test this harness is meant to enable.

## Legacy batch system (superseded)

`ivr/` (`jobs.json`, `run_ivr_batch.sh`) and `launchd/` are the older Twilio
job-watcher that ran `tools/ivr_probe/probe.py` hourly. Pulse replaced that
interactive-vs-scheduled model (PR #24); those files are retained for reference
and are no longer installed by `setup.sh`. `tools/ivr_probe/probe.py` itself
still works as a standalone CLI via `runtime.telephony.build_telephony()`.
