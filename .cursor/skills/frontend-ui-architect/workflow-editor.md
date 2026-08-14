# Workflow editor — research reference

Use with [SKILL.md](SKILL.md). This documents **known friction** in the current Edit Workflow surface so audits start from evidence, not a blank page.

## Owning files

| File | Role |
|------|------|
| [`EditForm.tsx`](../../../client/src/pages/edit/EditForm.tsx) | Page layout: header, setup fields, Steps list, Inputs section |
| [`InlineStepRow.tsx`](../../../client/src/pages/edit/InlineStepRow.tsx) | Editable step: sentence UI + per-step Save |
| [`RuleCard.tsx`](../../../client/src/pages/edit/RuleCard.tsx) | Read-only step display |
| [`SectionBlock.tsx`](../../../client/src/components/ui/SectionBlock.tsx) | Numbered sections (01 Steps, 02 Inputs) |
| [`ruleIntent.ts`](../../../client/src/script/ruleIntent.ts) | Actions, validation, open capture (blank cue phrase) |

## Mental model (target)

The editor should feel like **authoring a call script**, not filling out four separate forms:

1. **Identity** — name + readiness
2. **Dial setup** — number, timeout, description (secondary)
3. **Script** — ordered Steps the IVR will drive
4. **Run inputs** — derived from Steps, not manually maintained

## Current friction (as of 2026-07)

| Issue | Where | Impact |
|-------|-------|--------|
| Step = prose sentence in a Card | `InlineStepRow` flex-wrap | Wraps badly; hard to scan; action-specific fields hide in the sentence |
| Per-step **Save Step** | `InlineStepRow` footer | Feels like a form wizard, not a living script; extra clicks |
| Heavy header | `EditForm` `script-header-*` | Name + 3 setup fields + Run + 3 overflow actions compete above Steps |
| Decorative section numbers | `SectionBlock` `01` / `02` | Implies process order but Steps are the real sequence |
| Dual step presentations | `InlineStepRow` vs `RuleCard` | Edit and read-only modes look unrelated |
| Inputs section disconnected | `EditForm` block 02 | Users don't see why Inputs appear; tied to `{{var}}` in Steps |
| Action-specific UX in one row | `InlineStepRow` | Save response / End call / Wait need different field layouts, not one sentence |
| Validation under sentence | `InlineStepRow` | Errors easy to miss; Save disabled without explaining which field |

## Step actions (must stay supported)

From `ruleIntent.ts`:

- Press keys, Speak, Save response, Keep listening, Wait, End call
- Save response and End call: **cue phrase optional** (blank = next reply / hang up after prior Steps)

UI must make optional-phrase actions obvious without requiring dummy text.

## Recommended direction (default for briefs)

Unless the user chooses otherwise, recommend:

```
┌─────────────────────────────────────────────┐
│ [Workflow name]              [Ready] [Run ▶] │
│ Phone · Timeout · Description (collapsed)   │
├─────────────────────────────────────────────┤
│ Call script                                  │
│ ┌─ Step 1 ────────────────────────────────┐ │
│ │ Listen for: [________]                   │ │
│ │ Then: [Press keys ▼]  Value: [____]      │ │
│ └─────────────────────────────────────────┘ │
│ ┌─ Step 2 ─ Save response ────────────────┐ │
│ │ Listen for: (optional)                   │ │
│ │ Save as: [card_status]                   │ │
│ └─────────────────────────────────────────┘ │
│ + Add Step                                   │
├─────────────────────────────────────────────┤
│ Run inputs (from Steps)                      │
│ card_status · account_pin                    │
└─────────────────────────────────────────────┘
```

Structural moves (typical P0/P1):

- **Structured fields** per step, not a single "When … is heard," sentence
- **Auto-save** on blur or debounced patch; remove Save Step unless editing is explicitly dirty
- **Collapse setup** behind "Dial settings" after first fill
- **Timeline** or left rail for step order; move up/down into drag or rail
- **Action templates** swap field groups (keys vs save-as vs wait seconds)

## Component map (implementation hint)

| Region | Prefer | File |
|--------|--------|------|
| Editor shell | `PageLayout` or slim custom header | `EditForm.tsx` |
| Setup cluster | `Collapsible` or `Sheet` | new `WorkflowSetupFields.tsx` or section in `EditForm` |
| Step list | vertical stack, light dividers not full Cards | `EditForm.tsx` |
| Step row | labeled fields + `Select` from shadcn | refactor `InlineStepRow.tsx` |
| Read-only | same layout, disabled inputs | merge toward one component with `readOnly` |
| Inputs footer | `Badge` list or compact table | `EditForm.tsx` |

## Out of scope for UI architect

- Changing `Step` JSON schema or `conversationFlow` sync
- RunSession, SIP, STT, API
- Removing actions the runtime supports
