---
name: pathline-accounts-vault
description: >
  Implements or extends Pathline Accounts profiles and Input Vault sealed
  secrets in client/. Use when adding account fields, vault CRUD,
  pathsAvailableForAccount, or Account↔Vault binding. Never store secrets in
  Path JSON.
disable-model-invocation: true
---

# Pathline Accounts + Input Vault

## Models

- Account (`persistence/accountsStore.ts`): `fields[name] = plain{value} | secret{vaultKey}`
- Input Vault (`persistence/vaultStore.ts`): sealed via `crypto.sealVaultSecret` / `unsealVaultSecret`
- Readiness: `pathReadiness.pathsAvailableForAccount(account, paths)`

## Rules

1. Secret kind stores **vaultKey only** — never plaintext in the account record.
2. UI label is **Input Vault**, not Vault alone in nav.
3. Structure-first; reuse existing shadcn; no parallel design system.
4. After changes: `cd client && npm run build && npm test`
