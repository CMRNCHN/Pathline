import { describe, expect, it } from "vitest";
import {
  buildStepFromInlineDraft,
  inlineDraftFromStep,
  validateInlineStepDraft,
} from "./ruleIntent";

describe("inline Step conversion", () => {
  it("round-trips every executable action", () => {
    const drafts = [
      { when: "enter pin", action: "press-keys" as const, value: "{{pin}}#", output: "", waitSeconds: 3 },
      { when: "say name", action: "speak" as const, value: "Cameron", output: "", waitSeconds: 3 },
      { when: "your balance", action: "save-response" as const, value: "", output: "balance", waitSeconds: 3 },
      { when: "please wait", action: "keep-listening" as const, value: "", output: "", waitSeconds: 3 },
      { when: "", action: "wait" as const, value: "", output: "", waitSeconds: 5 },
      { when: "", action: "end-call" as const, value: "", output: "", waitSeconds: 3 },
    ];

    for (const draft of drafts) {
      const step = buildStepFromInlineDraft(draft, []);
      expect(validateInlineStepDraft(inlineDraftFromStep(step)).valid).toBe(true);
    }
  });

  it("rejects invalid keypad and capture values", () => {
    expect(
      validateInlineStepDraft({
        when: "pin",
        action: "press-keys",
        value: "12A",
        output: "",
        waitSeconds: 3,
      }).valid
    ).toBe(false);
    expect(
      validateInlineStepDraft({
        when: "balance",
        action: "save-response",
        value: "",
        output: "not valid",
        waitSeconds: 3,
      }).valid
    ).toBe(false);
  });
});
