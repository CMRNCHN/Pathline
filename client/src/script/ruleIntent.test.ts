import { describe, expect, it } from "vitest";
import {
  buildStepFromInlineDraft,
  inlineDraftFromStep,
  validateInlineStepDraft,
} from "./ruleIntent";
import { withSyncedRules } from "./compile";
import type { PathDocument } from "./types";
import { END_NOW_DETECT, NEXT_UTTERANCE_DETECT } from "../engine/runEngine";

describe("inline Step conversion", () => {
  it("round-trips every executable action", () => {
    const drafts = [
      { when: "enter pin", action: "press-keys" as const, value: "{{pin}}#", output: "", waitSeconds: 3 },
      { when: "say name", action: "speak" as const, value: "Cameron", output: "", waitSeconds: 3 },
      { when: "your balance", action: "save-response" as const, value: "", output: "balance", waitSeconds: 3 },
      { when: "", action: "save-response" as const, value: "", output: "card_status", waitSeconds: 3 },
      { when: "please wait", action: "keep-listening" as const, value: "", output: "", waitSeconds: 3 },
      { when: "", action: "wait" as const, value: "", output: "", waitSeconds: 3 },
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

  it("syncs open capture and open end without a cue phrase", () => {
    const base: PathDocument = {
      id: "open-capture",
      version: 2,
      setup: {
        name: "Open capture",
        description: "",
        target: "1000",
        timeoutMs: 10_000,
        speechPreferences: { autoListen: true },
        inputs: [],
      },
      steps: [],
      conversationFlow: [],
    };
    const keys = buildStepFromInlineDraft(
      { when: "zip code", action: "press-keys", value: "98335", output: "", waitSeconds: 3 },
      []
    );
    const capture = buildStepFromInlineDraft(
      { when: "", action: "save-response", value: "", output: "card_status", waitSeconds: 3 },
      [keys.label]
    );
    const end = buildStepFromInlineDraft(
      { when: "", action: "end-call", value: "", output: "", waitSeconds: 3 },
      [keys.label, capture.label]
    );
    const synced = withSyncedRules(base, [keys, capture, end]);
    expect(synced.conversationFlow.map((step) => step.detect)).toEqual([
      "zip code",
      NEXT_UTTERANCE_DETECT,
      END_NOW_DETECT,
    ]);
  });
});
