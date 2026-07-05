# PromptPath Threat Model

Canonical threat model for v1 implementation. Drives which controls are in scope and which residual risks are accepted.

## Adversaries in Scope

| Adversary | In scope | Required assurance |
|-----------|----------|-------------------|
| Passive network eavesdropper | Yes | Prevent casual interception of secrets and status payloads |
| Active MitM on client↔server path | Yes | TLS + strict verification; client-side encryption of any sensitive blobs |
| Compromised PromptPath host / insider | Partial | Minimize data at rest; no plaintext secrets; hashed session IDs only |
| SIP provider / carrier access | Yes (accepted residual) | Document visibility; reduce concentration via v2 DID strategy |
| Correlation attacker (metadata) | Partial | Client-mediated default; v2 DID pool if correlation becomes priority |
| Lawful process against PromptPath | Partial | Minimize retained data; short TTL; purge on revoke |

## Out of Scope (v1)

- Hiding call metadata from carriers (impossible on PSTN)
- Resisting lawful process when user data was never collected
- Long-term traffic analysis resistance (no timing jitter unless required later)

## Security Objectives (v1)

1. **Content confidentiality** — User secrets and call audio never traverse PromptPath servers in the default path.
2. **Metadata exposure reduction** — Server stores only hashed session IDs and opaque encrypted status blobs; no phone numbers, no transcripts.
3. **Data minimization** — Automatic purge after retention window; immediate delete on user revoke.
4. **Operational safety** — Explicit consent; lawful-use terms; lab testing before third-party IVR.

## v1 Architecture Decision

**Client-mediated only.** The user's device:

- Places the call (native dialer / WebRTC)
- Holds secrets in memory / secure local storage
- Runs STT locally (optional)
- Sends only encrypted status to the thin backend

The server provides:

- Ephemeral auth tokens
- Encrypted status ingest (opaque blobs)
- Notifications (redacted)
- Revoke / export / delete

## Control Mapping

| Control | v1 | v2 | v3 |
|---------|----|----|-----|
| Client-side secret encryption | ✓ | ✓ | ✓ |
| Local STT on device | ✓ | ✓ | optional fallback |
| Ephemeral JWT tokens | ✓ | ✓ | ✓ |
| Hashed session IDs | ✓ | ✓ | ✓ |
| Auto-purge / revoke / delete | ✓ | ✓ | ✓ |
| DID pool + cooldown | — | ✓ | ✓ |
| Multi-provider distribution | — | ✓ | ✓ |
| Server-mediated orchestrator | — | — | ✓ (exception path) |
| PJSIP + DTLS-SRTP agent | — | — | ✓ |
| Production KMS/HSM | — | partial | ✓ |

## Residual Risk (Accepted)

Regardless of implementation, carriers and SIP providers retain:

- Source and destination numbers
- Call timestamps and duration
- Billing and account metadata
- SIP registration and routing metadata

These are documented, not hidden.

## Change Control

Changes to this threat model require explicit review per the canonical architecture document.
