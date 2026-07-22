---
name: frontend-ui-architect
description: >
  Researches Pathline frontend surfaces, diagnoses layout and IA friction, and
  produces a UI Architecture Brief with wireframes and a component-to-file map
  before any code changes. Use when the Workflow editor or other client UI feels
  wrong, when the user asks for UI layout research, structure recommendations,
  frontend alignment, or invokes /frontend-ui-architect. Default to read-only
  recommendations unless the user explicitly asks to implement.
disable-model-invocation: true
---

# Frontend UI Architect

Research and recommend first. Align structure with real files in `client/` before painting.

## Modes

| Mode | When | Edits code? |
|------|------|-------------|
| **Audit** | User says UI feels off; no plan yet | No |
| **Recommend** | User wants layout/structure direction | No |
| **Implement** | User approves a brief or says "build it" | Yes — follow [implementation.md](implementation.md) |

Default to **Recommend**. Do not restyle or refactor until the user accepts the brief.

## Quick start

1. **Pin the surface** — name page(s), primary user job, and what must not change (data model, Run flow, vocabulary).
2. **Read the frontend** — owning pages, child components, CSS in [`client/src/styles.css`](../../client/src/styles.css), shadcn primitives in [`client/src/components/ui/`](../../client/src/components/ui/).
3. **Diagnose friction** — hierarchy, density, interaction model, validation UX, mobile/focus.
4. **Deliver a UI Architecture Brief** — use the template below.
5. **Map to code** — every recommended region links to a file and existing component.
6. **Stop** unless the user asks to implement.

For **Edit Workflow** specifically, also read [workflow-editor.md](workflow-editor.md).

## Pathline constraints

- UI copy: **Workflow**, **Step**, **Run**, **Inputs** — not Path / Rule / Script in user-facing text.
- Inline step semantics stay: When [phrase] → action → conditional value; no wizard screens.
- `client/` only; Tauri shell wraps it. Do not move telephony/STT/API into UI work.
- Reuse shadcn + CSS variables; no parallel design system.
- Cards only where interaction needs a boundary; cut decorative chrome.

## Research checklist

Copy and complete:

```
UI research:
- [ ] Surface pinned (page + job + preserve-list)
- [ ] Files read (page, sections, styles)
- [ ] Regions inventoried top-to-bottom
- [ ] Primary vs secondary actions identified
- [ ] Friction list (user task failures, not taste)
- [ ] Competitor / pattern scan (1–2 analogies only — IVR builders, call scripts, automation editors)
- [ ] Brief written with wireframe + component map
- [ ] P0/P1/P2 implementation phases
```

### What to read (Pathline client)

| Surface | Start here |
|---------|------------|
| Edit Workflow | [`client/src/pages/edit/EditForm.tsx`](../../client/src/pages/edit/EditForm.tsx), [`InlineStepRow.tsx`](../../client/src/pages/edit/InlineStepRow.tsx), [`ruleIntent.ts`](../../client/src/script/ruleIntent.ts) |
| Run flow | [`RunPage.tsx`](../../client/src/pages/RunPage.tsx), [`RunConfigureStep.tsx`](../../client/src/components/run/RunConfigureStep.tsx), [`RunActivePanel.tsx`](../../client/src/components/run/RunActivePanel.tsx) |
| Shell | [`Shell.tsx`](../../client/src/components/Shell.tsx), [`AppSidebar.tsx`](../../client/src/components/AppSidebar.tsx) |
| Tokens | [`client/src/styles.css`](../../client/src/styles.css) |

Use screenshots the user provides; cite them in the brief as evidence.

## UI Architecture Brief (required output)

```markdown
# UI Architecture Brief — [Surface name]

## Job
One sentence: what the operator accomplishes on this screen.

## Preserve
- [ ] Data model / API unchanged
- [ ] Product vocabulary
- [ ] [other non-negotiables]

## Current structure
Top-to-bottom regions with file citations.

## Friction diagnosis
| Issue | Evidence (file or screenshot) | User impact |
|-------|-------------------------------|-------------|

## Recommended structure
One-sentence concept + ASCII wireframe of first viewport.

## Hierarchy
Primary / secondary / tertiary for this surface.

## Interaction model
How edits save, validate, reorder, and error — in plain language.

## Component map
| Region | Recommended layout | shadcn / existing component | Target file |
|--------|-------------------|----------------------------|-------------|

## Copy & validation
Label changes, placeholder rules, error placement (sentence case, active voice).

## Phased implementation
- **P0** — fixes task failure or confusion
- **P1** — structure clarity
- **P2** — polish / motion / density

## Out of scope
What this brief intentionally does not change.

## Open questions
Only blockers that need a human product call.
```

## Recommendation quality bar

- Every friction item ties to **evidence**, not preference.
- Wireframe must show **one clear job** in the first viewport.
- Component map must use **files that exist** today or name a new file with a single clear owner.
- Prefer **one signature structural change** (e.g. "Steps read as a vertical call script") over five small tweaks.
- Reject generic SaaS patterns unless justified for call automation.

## Handoff to implementation

When the user approves the brief:

1. Read [implementation.md](implementation.md).
2. Optionally invoke the [`frontend-ui-architect`](../../agents/frontend-ui-architect.md) agent in implement mode or implement inline.
3. One surface per PR; run `cd client && npm run build && npm test`.

## Related skills

- Structure-only shorthand: [frontend-structure-redesign](../frontend-structure-redesign/SKILL.md)
- Visual identity pass (after structure): use the user's `frontend-design` skill — never before structure is settled.
