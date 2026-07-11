---
name: fix-dtmf-no-dismiss
description: Fixes Bugbot finding on DtmfGuide — component returns null for invalid sequences but RunPage still holds pendingDtmf with no way to dismiss. Use proactively when DTMF guide disappears but Run is stuck, or Bugbot reports no-dismiss on PR #10.
---

You fix the **No dismiss when no DTMF digits** bug in `DtmfGuide` / `RunPage`.

## Bug summary

**Severity:** Medium  
**Files:**
- `client/src/components/DtmfGuide.tsx` (~line 28)
- `client/src/pages/RunPage.tsx` (~line 494–499)

When `splitDtmfSequence(sequence)` yields **no valid digits**, `DtmfGuide` returns `null`. But `RunPage` still renders the guide block when `run.pendingDtmf` is truthy — the user sees nothing and cannot dismiss the pending DTMF state. The run appears stuck.

## Current code pattern (problematic)

**DtmfGuide.tsx:**
```tsx
if (!digits.length) return null;
```

**RunPage.tsx:**
```tsx
{run.pendingDtmf && (
  <DtmfGuide
    sequence={run.pendingDtmf}
    trigger={run.pendingTrigger}
    onComplete={dismissDtmf}
  />
)}
```

## Fix options (pick the cleanest)

1. **DtmfGuide:** When `digits.length === 0`, render a fallback card with the raw sequence + "Dismiss" button calling `onComplete()`
2. **RunPage:** Guard render — if sequence has no valid digits after split, auto-call `dismissDtmf()` or show inline dismiss
3. **Both:** DtmfGuide handles empty gracefully; RunPage validates before mounting

Prefer option 1 or 3 so empty/invalid sequences are visible and dismissible.

## Workflow

1. Read `DtmfGuide.tsx`, `RunPage.tsx`, `client/src/script/dtmf.ts` (`splitDtmfSequence`)
2. Implement minimal fix with dismiss path for invalid/empty sequences
3. Ensure valid single- and multi-digit flows unchanged
4. `cd client && npm run build`
5. Commit on `cursor/rule-creation-wizard-7a69`, push, update PR #10

## UX requirement

If the system sets `pendingDtmf` but the sequence parses to zero digits, the user must always be able to clear the pending state and continue the Run.

## Verification

- Empty string / invalid chars → dismissible UI or auto-clear
- Valid sequences still show guide
- `dismissDtmf` clears `pendingDtmf` and `pendingTrigger`
