# Known IVR Scripts

PromptPath v1 runs **known scripts only** — no discovery, no auto-adding prompts.

## Rule format

Each rule in `client/public/scripts/*.json`:

| Field | Purpose |
|-------|---------|
| `trigger` | Phrase heard → send `dtmf` (optional) |
| `response` | Phrase heard → set `status` on `key` |
| `key` | JSON field name in collected status |
| `status` | Value when `response` matches |
| `dtmf` | Touch-tone to send when `trigger` matches (`{secret}` placeholders) |
| `endCall` | End run and submit encrypted status |

Example:

```json
{
  "trigger": "",
  "response": "account is current|no payment due",
  "key": "balance_status",
  "status": "current",
  "endCall": true
}
```

## During a call

1. User selects script + enters local secrets + dials via native handoff
2. **Auto-listen** (Web Speech) or paste IVR phrases manually
3. **Trigger match** → prominent DTMF prompt (user taps on phone)
4. **Response match** → `collected[key] = status`
5. On `endCall`, encrypted status blob is sent to the API

## Authoring scripts

Use the **Scripts** tab in the app to create and edit IVR templates locally (stored in browser localStorage).

- **Send DTMF** rules — trigger phrase → touch-tone, with `{secret_key}` placeholders
- **Capture status** rules — IVR response → `key: status` in collected JSON
- **Local secrets** — any keys you need (`account_pin`, `zip_code`, `member_id`, etc.)
- Bundled examples are read-only; **Duplicate to edit** to customize
- Export / import JSON to share or back up scripts
