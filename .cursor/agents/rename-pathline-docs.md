---
name: rename-pathline-docs
description: >
  Converts PromptPath→Pathline in README, docs/, and architecture markdown.
  Use proactively during brand renames; owns documentation zone only.
---

You rename **documentation** from PromptPath to Pathline.

## Owns

- `README.md`
- `docs/**`
- Root `*Architecture*.md` (rename files with `git mv` when the filename contains PromptPath)

## Rules

- Display: `PromptPath` → `Pathline`
- Paths in examples: `~/Developer/projects/PromptPath` → `~/Developer/projects/Pathline` (or note clone path)
- Binaries in docs: `promptpath` → `pathline`, `PromptPath.app` → `Pathline.app`
- Python modules in docs: `promptpath_api` → `pathline_api`
- Do not edit `client/`, `desktop/`, `services/`, or `scripts/` — other agents own those
- Follow `.cursor/skills/brand-rename/SKILL.md`

## Done when

`rg -i 'promptpath' README.md docs PromptPath* Architecture*` only hits intentional historical notes (prefer none).
