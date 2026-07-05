PromptPath Architecture

Privacy‑first principle
- Privacy by minimization: Avoid collecting or retaining sensitive data whenever possible. Every retained secret, transcript, or log is an asset that must be protected; minimizing collection is the single strongest privacy control.

1. Threat Model
- Enumerate the adversaries you intend to defend against (select any combination): passive network eavesdropper, active MitM, compromised host/insider, provider/carrier access or lawful process, correlation attacker linking calls to users via metadata.
- For each adversary, record the required assurance level (e.g., prevent casual interception vs. resist provider correlation vs. resist legal process). This decision drives which controls are feasible.

2. Security Objectives
- Content confidentiality: prevent unauthorized access to call media and injected sensitive content.
- Metadata exposure reduction: reduce linkability between calls and user identities where feasible.
- Data minimization & retention: keep only necessary data and purge it promptly.
- Operational safety: avoid behaviors that trigger carrier anti‑fraud systems and ensure explicit user consent and lawful usage.

3. Content Confidentiality
- Transport encryption: require SIP over TLS and SRTP between trusted hops. Transport encryption protects communications between trusted endpoints. Unless both endpoints support true end‑to‑end media encryption, intermediaries that terminate the session (such as SIP providers) may still have access to media.
- Require DTLS‑SRTP where both endpoints support it; otherwise document the security limitations of alternative keying methods (e.g., SDES).
- TLS: use modern TLS with PFS (ECDHE), strict certificate verification, and certificate pinning or mTLS where operationally feasible.
- Key handling: decrypt only in memory using keys released by a KMS/HSM. Do not persist decrypted keys or raw sensitive audio/text to disk.
- Ephemeral credentials: issue per‑call, short‑lived credentials or tokens (JWT/OAuth) for SIP registration and provider APIs; revoke on session termination.
- Local STT/TTS: run speech models on infrastructure you control when possible; if cloud STT/TTS is used, ensure contractual, technical, and procedural protections and encrypt data in transit and at rest.
- Logging: redact content from logs; treat any stored audio/transcript as sensitive by default.

4. Metadata Exposure Reduction
- Client‑mediated preference: where platform capability allows, the user’s device should place the call and handle audio capture/injection so credentials and raw audio do not traverse your servers. This shifts trust away from your infrastructure but does not hide metadata from the telecom provider.
- Server‑mediated constraints: if server mediation is necessary:
  - Require client-side encryption of secrets; server decrypts only in memory using KMS/HSM‑released keys.
  - Use ephemeral session tokens and short TTLs for server operations.
  - Store only minimal hashed/peppered session identifiers for debugging.
- Provider strategy:
  - Use multiple providers to reduce concentration of metadata at a single vendor; this reduces correlation risk but does not eliminate provider‑level visibility (billing/KYC remains a link).
  - Implement a DID pool with controlled rotation and cooldown before reuse—document cooldown windows and provisioning cadence. Avoid one‑time DIDs or rapid provisioning patterns that trigger fraud detection.
- Timing measures: omit scheduling jitter unless the threat model specifically requires long‑term traffic correlation resistance; avoid anomalous timing patterns that could trigger carrier scrutiny.

5. Data Lifecycle
- Avoid creation: prefer in‑memory TTS injection and transient handling of audio/text.
- Encryption at rest: any persisted sensitive artifacts must be encrypted with keys in a KMS/HSM; access must be audited and limited.
- Automatic purge: implement automatic retention windows and secure deletion for audio, transcripts, secrets, and logs.
- Logging policy: redact phone numbers, SIP headers, and PII; retain only what’s required for debugging and for a strictly bounded period.
- Transcripts: treat as highly sensitive data; encrypt, restrict access, and purge promptly unless the user explicitly opts in to retention.

6. Operational Security
- Default‑deny: every component should start with no permissions and receive only the minimum network access, credentials, and capabilities required for its function.
- Network & hosts: run in private VPCs, restrict network paths, use strict firewall rules, and minimize public endpoints.
- Identity & access: enforce RBAC, strong authentication (MFA), least privilege, and audited admin actions.
- KMS/HSM: store and manage keys in a KMS/HSM; only release decryption keys to authorized processes for short durations.
- Monitoring & detection: IDS/IPS, integrity monitoring, and alerts for unusual infrastructure or call activity; monitor provider blacklists/feedback.
- Rate limiting & backoff: per‑DID and per‑account rate limits to avoid carrier anti‑fraud triggers.
- Consent & user controls: explicit consents, written authorization capture, and user APIs for revoke/export/delete.
- Provider contracts: require providers to disclose retention/recording policies; prefer providers that support TLS + SRTP/DTLS and per‑call credentialing where available.
- Secure development practices: hardened images, immutable infrastructure, regular patching, and secure CI/CD with secret scanning.

7. Residual Metadata
- Residual metadata is an inherent property of the public telephone network and cannot generally be eliminated through application design alone.
- Items that remain visible to carriers, SIP trunks, and intermediaries regardless of media/signaling encryption:
  - Calling number (source)
  - Called number / destination DID
  - Call start and end timestamps
  - Call duration
  - Provider account identity and DID ownership
  - Billing records and payment-related metadata
  - SIP registration events and signaling metadata
  - Network routing info and source IP addresses

8. Deployment Checklist
- Define the threat model and acceptable residual risk in writing.
- Choose client‑mediated or server‑mediated architecture and document tradeoffs.
- Implement client‑side encryption of user secrets; decrypt only in memory with KMS/HSM keys.
- Implement ephemeral per‑call credentials and short TTL session tokens.
- Enforce SIP/TLS and DTLS‑SRTP between trusted hops where supported; require DTLS‑SRTP when both endpoints support it.
- Prefer local STT/TTS for sensitive audio; if using cloud STT/TTS, ensure contractual retention limits and encryption.
- Implement DID pool + provider distribution + cooldown if correlation resistance is required; document cadence and limits.
- Enforce minimal logging, automatic purge, and secure deletion policies.
- Harden infrastructure (VPC, firewalls, IDS), apply RBAC/MFA, and use KMS/HSM for key management.
- Implement explicit consent, revoke, and data export/delete APIs.
- Test in a lab (Asterisk + SIPp) before any third‑party calls; obtain explicit written authorization for any third‑party IVR interactions.

9. Appendix — Control Mapping
- Content confidentiality controls: DTLS‑SRTP, SIP/TLS, mTLS, certificate pinning, in‑memory handling, KMS/HSM key control, ephemeral credentials, local STT/TTS.
- Metadata exposure reduction controls: client‑mediated calls, client‑side secret storage, minimal logging, DID rotation + provider distribution + cooldown (reduces concentration), multiple providers.
- No metadata protection: calling/called numbers, timestamps, durations, routing, billing records, registration events — these remain visible to carriers/providers.

10. Canonical Status
- This is the frozen, canonical security architecture.
- Changes to this architecture should require an explicit design review and documented justification.
- Implementation and validation should proceed against this specification; further architectural changes should only be made in response to concrete implementation constraints, security findings, or newly identified requirements.

