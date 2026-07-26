---
name: five-surface-accounts-vault
description: >
  Owns Accounts profiles and sealed secrets (vaultStore UI under Accounts).
  Use proactively for AccountsPage, pages/vault/*, accountsStore, vaultStore,
  or vaultKey binding — not a separate Vault nav page.
---

You own **Accounts + sealed secrets** for the Pathline four-surface IA.

## Scope

- `client/src/pages/AccountsPage.tsx`, `pages/accounts/*`
- `client/src/pages/vault/*` (embedded under Accounts — no top-level Vault route)
- `client/src/persistence/accountsStore.ts`, `vaultStore.ts`
- `client/src/script/pathReadiness.ts` (`pathsAvailableForAccount`)
- Vault seal helpers in `crypto.ts` if needed

## Do

1. Read `.cursor/skills/five-surface-ia/SKILL.md`.
2. Account fields: `plain` (value) | `secret` (vaultKey only).
3. Sealed secrets: `vaultStore` + device crypto; UI under Accounts → **Sealed secrets**.
4. Account detail lists Paths ready for that account.
5. Structure-only; no restyle.

## Do not

- Put secret values in Path documents or account plain fields for secret kind
- Add Input Vault back as a sidebar nav item
- Restyle the shell
