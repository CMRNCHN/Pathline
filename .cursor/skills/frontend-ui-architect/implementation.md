# Implementation handoff

Only after the user approves a **UI Architecture Brief** from [SKILL.md](SKILL.md).

## Rules

1. Implement **P0 first**, then stop for review unless the user asked for the full phase list.
2. Touch only files named in the brief's component map.
3. Reuse shadcn: `Button`, `Input`, `Select`, `Card`, `Badge`, `Collapsible`, `Sheet` — add via project convention if missing.
4. Do not change `ruleIntent` validation semantics unless the brief explicitly includes it.
5. Run `cd client && npm run build && npm test` before finishing.

## Edit Workflow ownership (typical)

| May edit | Avoid without reason |
|----------|----------------------|
| `client/src/pages/edit/EditForm.tsx` | `RunPage.tsx`, transport, API |
| `client/src/pages/edit/InlineStepRow.tsx` | `runEngine.ts`, `sync.ts` |
| `client/src/pages/edit/RuleCard.tsx` | |
| `client/src/styles.css` (editor-* classes only) | Global token rebrand |

Prefer merging `RuleCard` + `InlineStepRow` into one `WorkflowStepRow` with a `readOnly` prop if the brief says so.

## Commit message shape

```
Restructure Workflow editor steps as a call script.

Replace per-step sentence cards with labeled fields and collapsed dial setup.
```
