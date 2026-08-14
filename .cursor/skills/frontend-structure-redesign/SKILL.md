---
name: frontend-structure-redesign
description: >
  Structure-only UI passes for Pathline five-surface IA (Dashboard, Path
  Library, Accounts, Input Vault, System). Use when hierarchy/IA is approved
  and implementation must not restyle. Prefer five-surface-ia skill for the
  locked file map.
disable-model-invocation: true
---

# Frontend Structure Redesign

For the locked five-surface shell, read [five-surface-ia](../five-surface-ia/SKILL.md) first.

**Prefer [frontend-ui-architect](../frontend-ui-architect/SKILL.md)** for research before structure. Use this skill when structure direction is already decided.

Structure first, paint second. Do not restyle a confusing hierarchy.

## Pin the brief (required)

Before planning, state in one short block:

1. **Surface** — exact page(s) or shell region
2. **Audience** — Pathline operator on-device
3. **Single job** — what this surface must accomplish
4. **Preserve** — flows that must not change (SIP/STT/run engine)

## Pathline defaults

- Product words: **Path**, **Input Vault**, Step, When, Then, Input, Run
- Shipping UI is `client/` inside the Tauri shell
- Prefer existing shadcn in `client/src/components/ui/`
- Cards only for interaction; one job per section
- Flat five-item sidebar — never reintroduce Workflows/Edit/Run/Settings nav

## Anti-patterns

- Visual theme swap without changing hierarchy
- Adding a second sidebar or Settings footer
- Rewriting RunSession / transport / STT while “redesigning” UI
- Expanding scope beyond the pinned surface without an explicit ask
