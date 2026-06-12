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

### Tier A — real carrier call

The loopback proves connect → originate → prompt-detection → DTMF → hangup
mechanics. A *true* end-to-end test against a real IVR needs audio flowing over
the network, which means an outbound **SIP trunk** to a carrier (Twilio SIP,
Telnyx, etc.) configured in the container's `pjsip.conf`, then:

```bash
PULSE_TARGET="+18005551234" PULSE_CARD_DIGITS="<real test card>" \
  ./tools/ivr_beacon/BeaconApp/.build/release/PathlinePulse
```

With a real call, `PULSE_ENDPOINT` keeps its `PJSIP/<target>` default and the
mixing bridge is harmless (media already flows from the far end). The trunk is
the one piece this repo can't provide for you.

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
| `PULSE_CARD_DIGITS` | `4111111111111111` (Visa test card placeholder) | DTMF sent after the card prompt — **override with the card you want to probe** |
| `PULSE_ARI_HOST` | `127.0.0.1` | Asterisk ARI host |
| `PULSE_ARI_PORT` | `8088` | Asterisk ARI port |
| `PULSE_ARI_API_KEY` | `ari:ari` | ARI `user:pass` |
| `PULSE_ARI_APP` | `pulse` | Stasis application name |
| `PULSE_TALK_SILENCE_MS` | `1500` | TALK_DETECT silence threshold (ms) — **needs calibration** |
| `PULSE_MIN_PROMPT_MS` | `2000` | minimum sustained-speech duration to count a prompt (ms) — **needs calibration** |

Example — point Pulse at a different IVR with a test card:
```bash
PULSE_TARGET="+18005551234" PULSE_MENU_DIGITS="1" PULSE_CARD_DIGITS="4111111111111111" \
  ./tools/ivr_beacon/BeaconApp/.build/release/PathlinePulse
```

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
2. Export `PULSE_CARD_DIGITS` with a real test card (and any other overrides).
3. Launch the binary; confirm the waveform icon appears in the menu bar.
4. Click **Run Probe**. Watch the dropdown advance through the phases:
   `connecting → inCall`, then `waitingForGreeting → waitingForCardPrompt →
   waitingForResult → done`, with `→ menu`, `→ card`, `→ hangup` and `‹dtmf …›`
   lines appearing in the transcript.
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
