# Pathline Pulse — Architecture

**Pulse is a UI-driven controller over an ARI event-based execution system.** It
originates IVR calls and walks their menus, but it does not itself perform call
control or speech detection — Asterisk does. Pulse observes an event stream and
issues control commands in response.

## Layers

**1. UI Layer**
- Menu bar operator interface: template selection, per-run card entry, probe
  creation + display.
- Local transient state only — **not a system of record.**

**2. Runtime Control Layer**
- ARI client: WebSocket event ingestion (`/ari/events`) in, HTTP control
  (`/ari/channels/*`) out.
- Translates inbound events into FSM transitions, and FSM decisions into
  call-control commands (originate, DTMF, hangup, bridge).
- Connection liveness and auto-reconnect.

**3. Execution Engine (black box)**
- Asterisk, via ARI. Owns call origination, media bridging, and prompt-boundary
  detection (TALK_DETECT silence DSP).
- Treated strictly as a black box. Pulse makes no assumptions about its internals.

**4. Event-Driven State**
- The ARI event stream is the source of truth. The FSM advances on events, never
  on timers.

## Execution Flow

```
Run Probe
  → reserve channel id → originate(endpoint, app=pulse, channelId)

ARI event stream drives the FSM:
  StasisStart            → enter call · bridge for media · arm TALK_DETECT
  ChannelTalkingFinished → (if real prompt) advance FSM + issue next command
  ChannelDestroyed       → terminate · finalize transcript

FSM phases:
  waitingForGreeting → (send menu DTMF) → waitingForCardPrompt
                     → (send card DTMF) → waitingForResult
                     → (hangup)         → done
```

## Client State Layer (ephemeral)

- Holds a UI-only projection of active probes.
- **Must be considered non-authoritative.** Asterisk/ARI is the execution
  authority; client state mirrors the event stream and is downstream of it.
- Invariant: client state is derived from events and may be discarded — it is
  reconstructable from the event stream and must never become the system of
  record. Channel↔probe binding and published collections are implementation
  detail, not architecture.

## Cardholder-Data Controls

The probe transmits real card numbers as DTMF, which places it in PCI scope. Four
enforced controls, each covered by a regression test that fails the build on leak:

| Control | Guarantee |
|---|---|
| Transcript redaction | Received DTMF logged without digit value; PAN cannot be reconstructed from echoes. |
| Memory wiping | PAN held for a single FSM transition, then cleared; UI field cleared on run. |
| No card-shaped defaults | Nothing PAN-shaped is baked into the binary or pre-filled. |
| Body-only transport | Card digits ride in the request body, never a URL/query (URLs are logged by every hop, even under TLS). |

## Open Validation Item

Transport encoding is source-verified against Asterisk's ARI Swagger spec and
`res_ari.c`/`http.c`: `dtmf` is a query-type parameter, read only from the
query/post-vars table that an `application/x-www-form-urlencoded` POST body feeds
(never a JSON body). Pulse sends DTMF that way. A live Asterisk run remains the
final end-to-end check, but no further transport-encoding change is anticipated.
