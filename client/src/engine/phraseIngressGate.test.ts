import { describe, expect, it, vi } from "vitest";
import { PhraseIngressGate } from "./phraseIngressGate";
import type { PathDocument } from "@/script/types";

const path: PathDocument = {
  id: "test",
  version: 2,
  setup: {
    name: "Test",
    description: "",
    target: "",
    timeoutMs: 30_000,
    speechPreferences: { autoListen: true },
    inputs: [],
  },
  steps: [],
  conversationFlow: [{ id: "s1", detect: "enter pin", action: "trigger" }],
};

describe("PhraseIngressGate", () => {
  it("delays delivery after a matching phrase until silence elapses", async () => {
    vi.useFakeTimers();
    const delivered: string[] = [];

    const gate = new PhraseIngressGate(
      {
        silenceAfterPromptMs: 500,
        path,
        matchedFlowIds: () => [],
      },
      async (phrase) => {
        delivered.push(phrase);
      }
    );

    await gate.onPhrase("please enter pin now");
    expect(delivered).toEqual([]);
    await vi.advanceTimersByTimeAsync(500);
    expect(delivered).toEqual(["please enter pin now"]);
    gate.dispose();
    vi.useRealTimers();
  });
});
