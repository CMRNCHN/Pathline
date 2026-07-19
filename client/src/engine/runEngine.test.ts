import { describe, expect, it } from "vitest";
import type { PathDocument } from "../script/types";
import { initialRunState, processPhrase } from "./runEngine";

const document: PathDocument = {
  id: "dispatch-test",
  version: 2,
  setup: {
    name: "Dispatch test",
    description: "",
    target: "",
    timeoutMs: 30_000,
    speechPreferences: { autoListen: false },
    inputs: ["pin"],
  },
  steps: [
    {
      id: "keys",
      label: "keys",
      when: "enter pin",
      then: "{{pin}}#",
      output: "",
      rule: "Inject DTMF after detect",
    },
    {
      id: "speech",
      label: "speech",
      when: "say name",
      then: "Cameron",
      output: "",
      rule: "Inject speech after detect",
    },
  ],
  conversationFlow: [
    { id: "flow-keys", detect: "enter pin", action: "trigger", triggerLabel: "keys" },
    { id: "flow-speech", detect: "say name", action: "trigger", triggerLabel: "speech" },
  ],
};

describe("runtime action dispatch", () => {
  it("dispatches keypad and speech through distinct actions", () => {
    const keypad = processPhrase("please enter pin", document, { pin: "1234" }, initialRunState(), {
      automated: true,
    });
    const speech = processPhrase("say name", document, {}, initialRunState(), { automated: true });

    expect(keypad.dtmfAction?.sequence).toBe("1234#");
    expect(keypad.speechAction).toBeUndefined();
    expect(speech.speechAction?.text).toBe("Cameron");
    expect(speech.dtmfAction).toBeUndefined();
  });
});
