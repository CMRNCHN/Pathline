# Implementation Roadmap

Aligned with [threat-model.md](./threat-model.md), [architecture-boundary.md](./architecture-boundary.md), and the canonical architecture.

## v1 — Client-owned call automation (current)

**Goal:** PromptPath client owns the call session and automation loop. Server stores identity + encrypted artifacts only.

- Single thin API (`services/api/`)
- **Client owns:** SIP/native transport, local STT, runEngine, DTMF injection, event ledger
- Secrets, phone numbers, and audio stay on device
- Server receives: ephemeral auth, consent audit link, hashed session IDs, encrypted callstate blobs
- Revoke, export, delete, auto-purge

**Web client role:** Consent shell, Path authoring, manual fallback (paste phrases). **Not** the automation endpoint.

**Production MVP:** Desktop Tauri client + embedded SIP (`client/src/transport/`).

## v2 — Metadata correlation (optional)

**Trigger:** Threat model requires reducing linkability at a single provider.

- DID pool with cooldown
- Multi-provider distribution

Does not change the client-owned automation boundary.

## Native mobile (after desktop SIP MVP)

CallKit / Android Telecom + in-call DTMF + on-device Whisper. Same `CallTransport` interface, different implementation.

## Explicitly removed

| Idea | Reason |
|------|--------|
| Server orchestrator as default | Audio/secrets cross infrastructure — violates privacy model |
| Browser automation endpoint | Cannot own telephony media session |
| External softphone dependency | Breaks automation ownership |
| Central transcript storage | Turns audit into surveillance |
| Plaintext DTMF in audit logs | Use `{ step, digits, hash }` only |

## Deferred exception path (v3 — not planned)

Server-mediated calls require explicit separate consent ("audio passes through our servers"). Code remains in `services/deferred/` for reference only — not on the product roadmap.

See `services/deferred/README.md`.
