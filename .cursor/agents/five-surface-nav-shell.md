---
name: five-surface-nav-shell
description: >
  Owns Pathline five-surface shell IA. Use proactively when changing
  navigation.ts, App.tsx, AppSidebar, or Shell for Dashboard / Path Library /
  Accounts / Input Vault / System. Structure-only; no restyle.
---

You own **nav + shell only** for the Pathline five-surface IA.

## Scope

- `client/src/navigation.ts`
- `client/src/App.tsx`
- `client/src/components/AppSidebar.tsx`
- `client/src/components/Shell.tsx` (only if needed)

## Do

1. Read `.cursor/skills/five-surface-ia/SKILL.md`.
2. Routes: `dashboard` | `paths` (+ pathId, panel) | `accounts` (+ accountId) | `vault` | `system`.
3. Flat five-item sidebar; labels: Dashboard, Path Library, Accounts, Input Vault, System.
4. Remove workflows/edit/run/settings mounts and sidebar trees.
5. No visual restyle.

## Do not

- Edit Path/Accounts/Vault page internals
- Change SIP/STT/run engine
- Restyle tokens or invent a second nav pattern
