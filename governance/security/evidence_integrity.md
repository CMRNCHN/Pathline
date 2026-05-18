# Evidence Integrity and Security

## S-001: Append-Only Evidence
- All session logs, recordings, and snapshots must be stored in an append-only, immutable fashion.
- Evidence must be hash-verifiable to ensure no tampering.

## S-002: Access Control (Allowlist)
- Pathline must enforce an explicit allowlist of authorized phone numbers.
- No autonomous dialing of numbers not present in the allowlist.

## S-003: Privacy and Secrets
- Never commit real secrets or credentials to the repository.
- Treat `.env` files and local storage as sensitive.
- Local-first: all sensitive data remains on the operator's machine.

## S-004: Evidence Manifests
- Every session must generate a signed/hashed manifest linking all related artifacts (logs, audio, snapshots).
