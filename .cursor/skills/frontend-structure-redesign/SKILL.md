---
name: frontend-structure-redesign
description: >
  Shorthand for structure-only UI passes after frontend-ui-architect. Use when
  the user already has an approved layout direction and wants implementation
  focused on hierarchy and IA, not research. For diagnosis and recommendations
  first, use frontend-ui-architect instead.
disable-model-invocation: true
---

# Frontend Structure Redesign

**Prefer [frontend-ui-architect](../frontend-ui-architect/SKILL.md)** for research, friction diagnosis, wireframes, and component maps. Use this skill only when structure direction is already decided.

Structure first, paint second. Do not restyle a confusing hierarchy.

## Pin the brief (required)

Before planning, state in one short block:

1. **Surface** — exact page(s) or shell region (e.g. Edit Workflow, Run active, App sidebar)
2. **Audience** — who uses it (Pathline: operator on-device, not a marketing visitor)
3. **Single job** — what this surface must accomplish in one sentence
4. **Preserve** — flows, vocabulary, and components that must not change

If the user did not name a surface, ask once (Edit Workflow / Run flow / Shell+Dashboard / Full client). Do not invent a multi-page redesign without confirmation.

## Pathline defaults (this repo)

- Product words: **Workflow**, **Step**, **Run**, **Inputs** — never Path/Rule/Script in UI copy unless code still uses those identifiers internally.
- Shipping UI is `client/` inside the Tauri shell; browser is authoring/manual fallback only.
- Prefer existing shadcn primitives and tokens in [`client/src/styles.css`](client/src/styles.css) and [`client/src/components/ui/`](client/src/components/ui/). Extend tokens; do not fork a second design system.
- Keep When/Then step semantics and fail-closed desktop behavior; redesign presentation, not telephony architecture.

## Hard structure rules

Taken from the product design rules — enforce them as structure, not decoration:

- **One composition** for the first viewport (not a dashboard unless the surface is a dashboard).
- **One job per section** — one purpose, one headline, usually one short supporting line.
- **Brand first** on branded surfaces — product name is a hero-level signal, not only nav text.
- **Cards only for interaction** — if removing border/shadow/radius does not hurt the task, remove the card.
- **No hero clutter** — no stat strips, pill clusters, or floating badges on hero media.
- **Reduce chrome** — cut competing text blocks, icon rows, and nested panels that do not encode state.

Avoid AI-default looks unless the brief demands one: purple-on-white gradients, warm cream + terracotta serif, broadsheet hairline newspaper layouts, generic dark+acid-green.

## Workflow

Copy and track:

```
Structure redesign:
- [ ] 1. Pin surface, audience, job, preserve-list
- [ ] 2. Inventory current structure (regions, hierarchy, dead weight)
- [ ] 3. Draft structure plan (wireframe in prose/ASCII + token notes)
- [ ] 4. Uniqueness critique (reject generic defaults)
- [ ] 5. Implement structure (layout/IA) with existing components
- [ ] 6. Visual pass only after structure reads clearly
- [ ] 7. Mobile + focus + prefers-reduced-motion check
```

### 1–2. Inventory

List current regions top-to-bottom. For each: job, primary control, removable chrome. Cite real files (e.g. `EditForm.tsx`, `InlineStepRow.tsx`, `AppSidebar.tsx`).

### 3. Structure plan

Produce a compact plan before coding:

- **Layout concept** — one sentence + ASCII wireframe of the first viewport
- **Hierarchy** — what is primary / secondary / tertiary
- **Signature** — one structural or interaction idea the surface will be remembered by (not five decorations)
- **Tokens** — 4–6 named colors, display+body type roles, only if changing identity; otherwise map to existing CSS variables

### 4. Uniqueness critique

Ask: “Would I propose this same layout for an unrelated SaaS settings page?” If yes, revise hierarchy or signature before writing code.

### 5–6. Implement

- Change structure in the owning page/components; reuse shadcn.
- Prefer CSS variables and existing utility patterns over new global frameworks.
- Motion: 2–3 intentional moments max; respect `prefers-reduced-motion`.
- Copy: active voice, sentence case, same verb for the same action; errors say what failed and what to do next.

### 7. Done check

- First viewport has one clear job
- No orphaned cards or duplicate titles
- Keyboard focus visible; usable ~375px wide
- Product vocabulary intact

## Anti-patterns

- Visual theme swap without changing hierarchy
- Adding a second sidebar, tab row, or settings drawer “for completeness”
- Numbered 01/02/03 markers unless the content is truly a sequence the user must order
- Rewriting RunSession / transport / STT while “redesigning” UI
- Expanding scope from one surface to the full app without an explicit ask

## Examples

**Good trigger:** “Restructure the Edit Workflow page so Steps read as one call script.”  
**Bad trigger:** “Make it prettier” with no surface — ask which surface first.

**Good outcome:** Edit header is identity + Run; Steps are a single vertical script; Inputs appear only when referenced.  
**Bad outcome:** New color palette on the same dense multi-card editor.
