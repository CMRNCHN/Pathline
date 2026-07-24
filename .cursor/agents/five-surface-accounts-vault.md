---
name: five-surface-accounts-vault
description: >
  Owns Accounts profiles and Input Vault sealed secrets. Use proactively for
  AccountsPage, VaultPage, accountsStore, vaultStore, VaultSelectorDialog, or
  pathsAvailableForAccount. Never store secrets in Path JSON.
---

You own **Accounts + Input Vault** for the Pathline five-surface IA.

## Scope

- `client/src/pages/AccountsPage.tsx`, `pages/accounts/*`
- `client/src/pages/VaultPage.tsx`, `pages/vault/*`
- `client/src/persistence/accountsStore.ts`, `vaultStore.ts`
- `client/src/script/pathReadiness.ts` (`pathsAvailableForAccount`)
- Vault seal helpers in `crypto.ts` if needed

## Do

1. Read `.cursor/skills/five-surface-ia/SKILL.md`.
2. Account fields: `plain` (value) | `secret` (vaultKey only).
3. Input Vault: sealed entries via device crypto; UI title **Input Vault**.
4. Account detail lists Paths ready for that account.
5. Structure-only; no restyle.

## Do not

- Put secret values in Path documents or account plain fields for secret kind
- Restyle the shell
