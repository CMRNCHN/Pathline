# Native Client Integration (v1)

Production PromptPath call placement belongs on the user's device, not in a browser.

## Why native?

- Browsers cannot reliably place PSTN calls or capture call audio
- Secrets and audio should never traverse PromptPath servers
- Local STT (Whisper) runs best on-device

The web client (`../client/`) is a **consent and status shell** that demonstrates the v1 privacy contract.

## v1 Privacy Contract

The native client MUST:

1. Store secrets in secure enclave / Keychain / Keystore — never send plaintext to server
2. Place calls via native dialer (CallKit / TelecomManager) or WebRTC with local SDP
3. Run STT locally (Whisper.cpp, platform speech APIs)
4. Send only encrypted status blobs to `POST /v1/status`
5. Support revoke (`POST /v1/revoke`) and delete (`DELETE /v1/status/{session_id}`)

The native client MUST NOT:

- Send target phone numbers to PromptPath servers
- Send transcripts or audio to PromptPath servers (only encrypted status + transcript hash)
- Use server-mediated flow without explicit v3 opt-in

## API Endpoints (v1 thin backend)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/token` | Mint ephemeral JWT (requires consent) |
| POST | `/v1/status` | Submit encrypted status blob |
| GET | `/v1/status/{session_id}/export` | Export user's encrypted data |
| DELETE | `/v1/status/{session_id}` | Delete session data |
| POST | `/v1/revoke` | Revoke token |

Base URL: `http://localhost:8000` (dev)

## Suggested stack

| Platform | Dialer | STT | Secure storage |
|----------|--------|-----|----------------|
| iOS | CallKit | Whisper.cpp / Speech framework | Keychain |
| Android | TelecomManager | Whisper.cpp / SpeechRecognizer | Keystore |

## Session flow

```
1. User accepts consent → POST /v1/token
2. User enters secrets (local only) + target number (local only)
3. Native dialer places call
4. Local STT processes audio → transcript hash computed locally
5. Encrypt { status, transcript_hash, completed_at } client-side
6. POST /v1/status with encrypted blob
7. On done: POST /v1/revoke + DELETE /v1/status/{id}
```

## Next steps

Scaffold iOS/Android projects here when ready. Until then, use the web client for consent/status testing and `tel:` links for dialer handoff on mobile browsers.
