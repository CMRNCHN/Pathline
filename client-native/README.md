# Native Client Integration (v1)

Production Pathline call placement and DTMF automation belong in the **Pathline client**, not a browser or external softphone.

See [docs/architecture-boundary.md](../docs/architecture-boundary.md) for the frozen module boundary.

## Why native / desktop SIP?

- Automation requires owning the **call media session** (dial + RTP + DTMF inject)
- External softphone + web UI breaks the loop — Pathline cannot inject DTMF into a session it does not own
- Secrets and audio must never traverse Pathline servers

## v1 Privacy Contract

The client MUST:

1. Store secrets in secure enclave / Keychain / Keystore — never send plaintext to server
2. Place calls via `CallTransport` (SIP, CallKit, or TelecomManager)
3. Run STT locally (Whisper.cpp, platform speech APIs)
4. Send only encrypted callstate blobs to `POST /v1/callstate`
5. Record audit events locally (`EventLedger`) — no secrets/transcripts in events
6. Support revoke (`POST /v1/revoke`) and delete (`DELETE /v1/callstate/{session_id}`)

The client MUST NOT:

- Send target phone numbers to Pathline servers
- Send transcripts or audio to Pathline servers
- Log plaintext DTMF sequences in audit events
- Use server-mediated flow without explicit v3 opt-in (removed from roadmap)

## CallTransport interface

Implement `client/src/transport/CallTransport.ts` per platform:

| Platform | Implementation |
|----------|----------------|
| Desktop MVP | Tauri + PJSIP/Linphone via `window.__pathlineSipBridge` |
| iOS | CallKit + in-call DTMF |
| Android | TelecomManager + in-call DTMF |
| Web dev | `SimulatorTransport` only — manual paste fallback |

## API Endpoints (v1 thin backend)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/token` | Mint ephemeral JWT (requires consent) |
| POST | `/v1/consent/session` | Link consent record to run session |
| POST | `/v1/callstate` | Submit encrypted callstate blob |
| GET | `/v1/callstate/{session_id}/export` | Export user's encrypted data |
| DELETE | `/v1/callstate/{session_id}` | Delete session data |
| POST | `/v1/revoke` | Revoke token |

## Session flow

```
1. User accepts consent → POST /v1/token
2. User enters secrets (local only) + target (local only)
3. RunSession.startCall → CallTransport.dial
4. Local STT → runEngine.processPhrase
5. dtmf.sendDtmfSequence → CallTransport.sendDTMF
6. EventLedger records hashed audit trail
7. Encrypt { status, transcript_hash, ledger_digest } client-side
8. POST /v1/callstate + POST /v1/consent/session
9. On done: revoke + delete
```

## Next steps

1. Scaffold Tauri desktop app wrapping `client/`
2. Implement `NativeSipBridge` in Rust (PJSIP)
3. Wire `RunSession` as the sole run orchestrator
4. iOS/Android after desktop SIP MVP validates the loop
