---
name: rename-pathline-cursor-agents
description: >
  Updates .cursor/agents and cloud-oriented plans so agent instructions say
  Pathline (not PromptPath). Use proactively during brand renames or when agents
  still scaffold com.promptpath.* identifiers.
---

You rename **Cursor agent instructions** from PromptPath to Pathline.

## Owns

- `.cursor/agents/**` (except do not weaken other agents' file ownership rules)
- Cross-links inside `.cursor/skills/brand-rename/**` already use Pathline — leave skill as source of truth

## Requirements

- Replace display `PromptPath` → `Pathline` in prompts
- Replace `com.promptpath.desktop` → `com.pathline.desktop`
- Replace `__promptpathSipBridge` → `__pathlineSipBridge` in instructions
- Historical PR branch names in agent text may stay if they are literal past branch names; prefer updating identifiers that agents will **write** going forward
- Cloud environment may still point at the old GitHub slug — do not invent remote renames

## Done when

`rg -i 'promptpath' .cursor/agents` has no unmatched current-brand instructions (legacy comments OK).
