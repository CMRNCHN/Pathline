# Pathline Pulse — Boundary Contract (Forward Design Spec)

> **Status: forward design spec.** This defines the *target* boundary between the
> ARI event stream, the FSM, and client state. Sections are tagged **[Built]**
> (true of current code) or **[Target]** (not yet implemented; design intent).
> Companion to `ARCHITECTURE.md`, which describes current state only.

The contract has one governing principle: **the ARI event stream is the single
authority.** Everything downstream — FSM phase, transcript, UI — is a deterministic
projection of that stream and must be reconstructable from it.

---

## 1. Event-Schema Authority

**[Target]** A single canonical schema module is the *only* place ARI event JSON
is decoded. No other component may field-scan or re-parse raw event payloads.

- One decode point, one typed representation. Today decode is a minimal inline
  struct in the runtime client **[Built]**; the target promotes it to a dedicated,
  owned schema with explicit, exhaustive event-type handling.
- The schema is **versioned**. A decoded event carries enough identity (type,
  channel id, and event-specific fields) that a stored event is self-describing
  for replay independent of the live connection.
- Three distinct failure rules, kept separate so "unknown type" is never misread
  as "drop the stream":
  - **Malformed event** (undecodable frame) → **drop the event**, note it, never
    advance the FSM, never crash.
  - **Unknown schema version** → **drop the event** — its fields cannot be trusted.
  - **Unknown event type** (well-formed, known version, unrecognized `type`) →
    **ignore and continue** — skip this one event, keep processing the stream.

Authoritative fields the contract depends on:

| Field | Source | Used for |
|---|---|---|
| `type` | event | routing to the transition table |
| `channel.id` | event | ownership filter (channel↔probe binding) |
| `digit` | `ChannelDtmfReceived` | redacted arrival note only (value never stored) |

---

## 2. ARI Event → FSM Transition Table

**[Built]** Ownership filter precedes everything: an event whose `channel.id` is
not bound to a probe is ignored (foreign legs from bridges/transfers never mutate
state). All progression is event-driven; there are no timers.

| Event | Guard | Phase before → after | Side effect |
|---|---|---|---|
| `StasisStart` | — | `waitingForGreeting` (unchanged) | status→inCall · create+join mixing bridge · arm TALK_DETECT |
| `ChannelTalkingStarted` | — | unchanged | record talk-start timestamp |
| `ChannelTalkingFinished` | prompt ≥ `MIN_PROMPT_MS` | `waitingForGreeting` → `waitingForCardPrompt` | send **menu** DTMF |
| `ChannelTalkingFinished` | prompt ≥ `MIN_PROMPT_MS` | `waitingForCardPrompt` → `waitingForResult` | send **card** DTMF, then wipe PAN |
| `ChannelTalkingFinished` | prompt ≥ `MIN_PROMPT_MS` | `waitingForResult` → `done` | hangup |
| `ChannelTalkingFinished` | prompt < `MIN_PROMPT_MS` | unchanged | note "short blip ignored" |
| `ChannelDtmfReceived` | — | unchanged | note "dtmf received" (value redacted) |
| `ChannelDestroyed` | — | any → `done` | destroy bridge · status→completed · finalize |

Guard semantics **[Built]**: the prompt-duration guard **fails open** — if no
matching `ChannelTalkingStarted` was seen, the transition proceeds rather than
stalling the probe.

---

## 3. What the Client Is Forbidden to Store

**[Built, enforced by tests]** These are hard invariants. Each has a regression
test that fails the build on violation.

- **The PAN beyond a single FSM transition.** The card number exists only from
  entry until it is handed to the dialer; it is wiped immediately after.
- **The PAN in any URL.** Card digits travel in the request body, never a query
  string. URLs are logged by every hop, even under TLS.
- **Raw received-DTMF digit values.** `ChannelDtmfReceived` is recorded as an
  arrival with the value redacted — an echoed card can never be reconstructed.
- **A card-shaped default.** Nothing PAN-shaped is baked into the binary or
  pre-filled into the UI.

**[Target]** Extends the same invariant to the event log (§4): the persisted
stream must itself be PAN-free — card-send events store a digit *count*, never the
digits, so the authority record can never become a cardholder-data store.

---

## 4. Replay Reconstruction Rules

**[Target]** Not yet implemented. Defines how state is rebuilt from the event log.

- **The event log is the authority.** Raw decoded events are persisted in order,
  each stamped with arrival time and `channel.id`.
- **Client state is a pure fold over the log.** Phase, status, and transcript are
  computed by replaying events through the same transition table in §2. There is
  no state that exists outside this fold.
- **Replay = re-fold.** Reconstructing a past probe means replaying its events
  from the log; the result must be byte-identical to the live projection.
- **Redaction happens at ingestion, not at display.** The PAN-free invariant (§3)
  is applied when events enter the log, so no downstream consumer — replay, audit,
  export — can ever surface cardholder data. The log is safe to retain.
- **Determinism requirement.** The transition table must be a pure function of
  (current phase, event, guard inputs). Any non-determinism (wall-clock, network
  ordering beyond what's stamped) is a contract violation.

---

## Open Validation Item

Resolved by source verification (Asterisk's ARI Swagger spec, `res_ari.c`,
`http.c`): `dtmf` is a query-type parameter, read only from the merged
query/post-vars table — never from a JSON body, which would silently 400 "DTMF is
required". The §2 "send card DTMF" side effect now sends
`application/x-www-form-urlencoded` (`dtmf=<digits>`) in the request body,
satisfying both ARI's parameter contract and §3's no-PAN-in-URL invariant. The
transition table itself (§2) is unaffected. A live Asterisk run remains the final
end-to-end check.
