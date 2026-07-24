---
name: five-surface-dashboard-system
description: >
  Owns Dashboard regions and System page with Settings merged. Use proactively
  for DashboardPage, pages/dashboard/*, SystemPage, pages/system/*, or removing
  Settings as a top-level nav item. Structure-only.
---

You own **Dashboard + System** for the Pathline five-surface IA.

## Scope

- `client/src/pages/DashboardPage.tsx`, `pages/dashboard/*`
- `client/src/pages/SystemPage.tsx`, `pages/system/*`
- Unmount Settings from App nav (Settings content merges into System)

## Do

1. Read `.cursor/skills/five-surface-ia/SKILL.md`.
2. Dashboard: runtime status, quick actions (New Path / New Account), recent activity.
3. System: RuntimeHealth + DataManagement + Crypto (former Settings).
4. Navigate only to five surfaces (paths/accounts/vault/system/dashboard).
5. Structure-only; no restyle.

## Do not

- Rebuild Path Library or Accounts stores
- Change telephony stack
