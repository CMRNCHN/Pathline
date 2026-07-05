# Implementation Roadmap

Aligned with [threat-model.md](./threat-model.md) and the canonical architecture.

## v1 — Current (client-native, thin server)

**Goal:** Minimize trust in PromptPath infrastructure.

- Single thin API (`services/api/`)
- Client-mediated flow only
- Secrets and target numbers stay on device
- Local STT on client (Web Speech API / native Whisper hook)
- Server receives: ephemeral auth, encrypted status blobs, hashed session IDs
- Revoke, export, delete, auto-purge

**Web client role:** Consent shell + status reporting. Native apps are the target for real call placement.

## v2 — Metadata correlation (deferred)

**Trigger:** Threat model requires reducing linkability at a single provider.

- DID pool with cooldown (`services/deferred/did-manager/`)
- Multi-provider distribution
- Rate limiting per DID

See `services/deferred/README.md`.

## v3 — Server-mediated exception (deferred)

**Trigger:** Client path insufficient (e.g. no native dialer, batch automation).

- Explicit opt-in consent ("audio passes through our servers")
- PJSIP orchestrator with TLS + DTLS-SRTP
- In-memory audio only; local Whisper on controlled infra
- No transcript persistence

See `services/deferred/orchestrator/`, `stt/`, `kms/`.

## Native Client

Production call placement belongs in `client-native/` (iOS/Android). The web client demonstrates the v1 privacy contract but cannot place PSTN calls natively.
