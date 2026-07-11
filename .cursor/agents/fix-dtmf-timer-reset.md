---
name: fix-dtmf-timer-reset
description: Fixes Bugbot finding on DtmfGuide — DTMF auto-advance timer resets every render because digits array is in useEffect deps. Use proactively when DtmfGuide timing is flaky or Bugbot reports timer reset on PR #10.
---

You fix the **DTMF timer resets every render** bug in `DtmfGuide.tsx`.

## Bug summary

**Severity:** Medium  
**File:** `client/src/components/DtmfGuide.tsx` (~line 21–26)

The multi-digit auto-advance `useEffect` lists `digits` in its dependency array, but `digits` is a **new array reference on every render** because it comes from `splitDtmfSequence(sequence)` called inline in the component body. This causes the effect to re-run every render, clearing and restarting the timer — the step guide never advances reliably.

## Current code pattern (problematic)

```tsx
const digits = splitDtmfSequence(sequence);

useEffect(() => {
  if (!isMulti || index >= digits.length - 1) return;
  const delay = dtmfStepDelayMs(digits[index], digits[index + 1]);
  const timer = window.setTimeout(() => setIndex((i) => i + 1), delay);
  return () => window.clearTimeout(timer);
}, [digits, index, isMulti]);
```

## Fix approach

1. **Stabilize digits** — memoize on `sequence`:
   ```tsx
   const digits = useMemo(() => splitDtmfSequence(sequence), [sequence]);
   ```
2. **Or** depend on `sequence` instead of `digits` inside the effect and compute digits there
3. Ensure `isMulti` is derived from stable `digits.length` or memoized
4. Verify timer advances through multi-digit sequences (e.g. `123456#`) without resetting on unrelated re-renders
5. Manual "Next key" button should still work alongside auto-advance

## Workflow

1. Read `client/src/components/DtmfGuide.tsx` and `client/src/script/dtmf.ts`
2. Apply minimal fix (prefer `useMemo` for digits)
3. `cd client && npm run build`
4. Commit on `cursor/rule-creation-wizard-7a69` with clear message
5. Push and update PR #10

## Do not

- Change RunPage or run engine unless required
- Remove auto-advance feature
- Introduce unnecessary refs if useMemo suffices

## Verification

- Multi-digit sequence auto-advances index after delay
- Re-rendering parent (e.g. typing in IVR textarea) does not reset timer
- Single-digit sequences unchanged
