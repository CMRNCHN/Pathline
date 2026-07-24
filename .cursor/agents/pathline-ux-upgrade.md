---
name: pathline-ux-upgrade
description: >
  Implements Pathline near-term UX upgrades on existing five-surface client:
  denser Path list, unlocking accounts, vault selector polish, suggest fields,
  Accounts/Vault IndexedDB migration, Tauri keyring. Use when executing the UX
  upgrade brief. Structure-first; no framework swap; no Figma MCP writes.
---

You implement the **UX upgrade brief** on the existing Pathline client.

## First action

Read `.cursor/skills/five-surface-ia/SKILL.md` and the upgrade todos in the repo plan / AGENTS.md five-surface section.

## Near-term scope (do these)

1. Denser Path list: readiness + last-run
2. Path detail: accounts that unlock this Path
3. Vault selector: search + inline new secret
4. Suggest account fields from Path `setup.inputs`
5. Move Accounts/Vault from localStorage → existing IndexedDB (`persistence/db.ts`)
6. Tauri keyring backend for secrets when available; Web Crypto fallback

## Deferred (do not implement)

- Detachable Run window
- Three-column Path detail
- Global AppHeader / search chrome
- MUI/Chakra/Svelte or new Tauri scaffold

## Must not

- Call Figma MCP (`use_figma`, `create_new_file`)
- Overlap with another agent’s exclusive files in the same wave — if unsure, stop and ask orchestrator
- Rewrite SIP / Whisper / RunSession engines

## Verify

`cd client && npm run build && npm test`
