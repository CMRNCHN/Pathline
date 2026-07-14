# Architecture Boundary (Frozen)

Pathline is a **privacy-preserving local call automation agent** with verifiable execution history.

Do not split this boundary again.

## Ownership

| Component | Owner |
|-----------|-------|
| Call session (SIP / native) | Pathline client |
| Audio | Device |
| STT | Device |
| Phrase matching | Pathline |
| Secrets | Device |
| DTMF injection | Pathline (via transport) |
| Audit ledger | Device |
| Server | Identity + encrypted artifact storage only |

## Client module stack

```
Pathline Client
│
├── transport/          Call session — dial, RTP, DTMF inject
│   ├── CallTransport.ts
│   ├── SipTransport.ts
│   └── AudioSession.ts
│
├── engine/             Authority — Path execution
│   ├── runEngine.ts
│   └── runSession.ts
│
├── dtmf/               Timing + send(sequence) — no SIP/UI
│   └── dtmf.ts
│
└── callstate/          Observation — event ledger + projection
    ├── ledger.ts
    └── project.ts
```

## Rules

1. **runEngine** decides step state, expected phrases, and next actions. It does not know SIP or PSTN.
2. **CallTransport** owns media. The engine never talks to carriers directly.
3. **callstate** is observation-only. Events: `CALL_STARTED`, `PROMPT_DETECTED`, `PHRASE_MATCHED`, `DTMF_SENT`, `STEP_COMPLETED`, `CALL_ENDED`. No secrets, transcripts, or audio in events.
4. **DTMF audit** stores `{ step, digits: count, hash }` — never plaintext sequences.
5. **Softphone-as-dependency is removed.** External softphones cannot be the automation endpoint.

## Removed from roadmap

- Server orchestrator as default path (violates privacy model)
- Browser as telephony/automation endpoint
- Central transcript storage (audit ≠ surveillance)

## MVP prototype

Desktop Pathline client (Tauri + React + PJSIP/Linphone + local Whisper):

```
Run → dial → SIP session → local STT → phrase match → runEngine → dtmf → transport inject → ledger → encrypted export
```

Mobile PSTN automation is deferred until desktop SIP proves the loop.

## Native bridge

`SipTransport` delegates to `window.__pathlineSipBridge` when injected by the Tauri shell. Web-only dev uses `SimulatorTransport`.
