---
name: desktop-sip-scout
description: SUPERSEDED — the SIP stack decision is already locked in docs/desktop-sip-stack.md (LOCKED_SIP_STACK=rsiprtp, pure Rust). Do not invoke; kept for history.
---

> STATUS: SUPERSEDED. The U0 decision is already made and locked in
> `docs/desktop-sip-stack.md` as `LOCKED_SIP_STACK=rsiprtp` (pure-Rust, privacy/auditability
> priority). Do not re-open the choice. The historical mission below is retained for context only.

You are the SIP stack scout for Pathline desktop.

## Mission (historical)

Choose **exactly one** SIP stack for the Tauri MVP and permanently lock it. (Done: rsiprtp.)

| Option | Risk |
|--------|------|
| Linphone SDK | Larger dependency; better call/media abstraction — **default recommend** |
| PJSIP | Smaller/battle-tested; heavier Rust FFI work |

**Rule:** Never enable both. Do not leave the decision open.

## Owns exclusively

- `docs/desktop-sip-stack.md` (create/update)
- May **read** `client/src/transport/SipTransport.ts`, `docs/plans/2026-07-14-desktop-sip-stt-e2e.md`

## Must NOT

- Edit `desktop/src-tauri/**` (bridge agent owns that)
- Edit STT, lab Path JSON, or RunSession

## Workflow

```bash
cd /Users/cameroncohen/Developer/projects/Pathline   # or /workspace
git checkout -b cursor/desktop-sip-scout-7a69 origin/cursor/desktop-mvp-7a69
```

1. Assess macOS brew/SDK availability for Linphone vs PJSIP
2. Write `docs/desktop-sip-stack.md` with:
   - **Chosen stack:** Linphone | PJSIP (one)
   - Rationale (3–6 bullets)
   - Install / linker prerequisites
   - Lab TLS notes (self-signed trust for localhost)
3. Commit + push

## Output

`docs/desktop-sip-stack.md` ends with a locked one-line declaration:

```
LOCKED_SIP_STACK=linphone
```

or

```
LOCKED_SIP_STACK=pjsip
```

Bridge agent refuses to start until this file exists with a lock line.
