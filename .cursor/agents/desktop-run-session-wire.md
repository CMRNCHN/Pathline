---
name: desktop-run-session-wire
description: Wires RunPage and RunActivePanel to RunSession + createAppTransport; removes placeCallLocally tel fallback. Use proactively in wave 1 parallel with scaffold — owns client run flow only.
---

You wire the web UI to `RunSession` as the sole run orchestrator.

## Files (exclusive ownership)

- `client/src/pages/RunPage.tsx`
- `client/src/components/run/RunActivePanel.tsx`
- `client/src/hooks/useRunSession.ts`
- `client/src/transport/createAppTransport.ts`
- `client/src/transport/index.ts`
- `client/.env.development` (`VITE_SIMULATE_TRANSPORT=true`)

## Workflow

```bash
cd /workspace
git checkout -b cursor/desktop-run-session-7a69 origin/cursor/known-scripts-and-run-automation
cd client && npm run build
```

## Requirements

1. `createAppTransport()` returns SIP/simulator transport in Tauri or when `VITE_SIMULATE_TRANSPORT=true`; else `null` (manual browser).
2. `RunPage.handleStart` creates `RunSession`, calls `startCall(target)` when transport exists — **no** `placeCallLocally`.
3. `RunActivePanel` delegates phrase matching + DTMF to `runSession.processPhrase()`.
4. `useRunSessionFactory` memoizes transport once per mount.
5. Cleanup calls `runSession.hangup()` on revoke/unmount.

## Rules

- Do not edit `desktop/` or Rust — scaffold agent owns that
- Preserve consent → configure → active step flow and API submit on complete

## Output

Green `npm run build` in `client/`.
