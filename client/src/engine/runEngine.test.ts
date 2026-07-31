import { describe, expect, it } from "vitest";
import type { PathDocument } from "../script/types";
import {
  END_NOW_DETECT,
  completeWaitStep,
  getPendingFlowStep,
  initialRunState,
  NEXT_UTTERANCE_DETECT,
  processPhrase,
  stepTimeoutMs,
  timeoutPendingStep,
  waitMsFromDetect,
} from "./runEngine";

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

  it("saves the next reply for open capture and ends when the following Step is open end", () => {
    const path: PathDocument = {
      id: "card-status",
      version: 2,
      setup: {
        name: "Card Status",
        description: "",
        target: "8009505114",
        timeoutMs: 10_000,
        speechPreferences: { autoListen: true },
        inputs: [],
      },
      steps: [
        {
          id: "zip",
          label: "zip",
          when: "zip code",
          then: "98335",
          output: "",
          rule: "Inject DTMF after detect",
        },
        {
          id: "capture",
          label: "capture_card_status",
          when: "",
          then: "",
          output: "card_status",
          rule: "Capture value after detect",
        },
        {
          id: "end",
          label: "end_call",
          when: "",
          then: "",
          output: "",
          rule: "End call",
        },
      ],
      conversationFlow: [
        { id: "flow-zip", detect: "zip code", action: "trigger", triggerLabel: "zip" },
        {
          id: "flow-capture",
          detect: NEXT_UTTERANCE_DETECT,
          action: "extract",
          triggerLabel: "capture_card_status",
        },
        { id: "flow-end", detect: END_NOW_DETECT, action: "end" },
      ],
    };

    const afterZip = processPhrase("please enter zip code", path, {}, initialRunState(), {
      automated: true,
    });
    expect(afterZip.dtmfAction?.sequence).toBe("98335");
    expect(afterZip.state.collected.card_status).toBeUndefined();
    expect(afterZip.shouldComplete).toBe(false);

    const beforePriors = processPhrase("your card is active", path, {}, initialRunState(), {
      automated: true,
    });
    expect(beforePriors.state.collected.card_status).toBeUndefined();
    expect(beforePriors.matched).toBe(false);

    const captured = processPhrase("your card is active", path, {}, afterZip.state, {
      automated: true,
    });
    expect(captured.state.collected.card_status).toBe("your card is active");
    expect(captured.shouldComplete).toBe(true);
    expect(captured.state.completed).toBe(true);
    expect(captured.state.matchedFlowIds).toContain("flow-end");
  });

  it("completes after one pipe-OR determination, then open end", () => {
    // Card-status style: mutually exclusive IVR outcomes belong in ONE Step
    // (pipe-OR), not sibling Steps — open end requires every prior id matched.
    const path: PathDocument = {
      id: "card-status-or",
      version: 2,
      setup: {
        name: "Card Status OR",
        description: "",
        target: "1000",
        timeoutMs: 10_000,
        speechPreferences: { autoListen: true },
        inputs: [],
      },
      steps: [
        {
          id: "status",
          label: "card_status",
          when: "zip code|you gave me|secret word",
          then: "",
          output: "card_status",
          rule: "Capture value after detect",
        },
        {
          id: "end",
          label: "end_call",
          when: "",
          then: "",
          output: "",
          rule: "End call",
        },
      ],
      conversationFlow: [
        {
          id: "flow-status",
          detect: "zip code|you gave me|secret word",
          action: "extract",
          triggerLabel: "card_status",
        },
        { id: "flow-end", detect: END_NOW_DETECT, action: "end" },
      ],
    };

    const hit = processPhrase("please enter your zip code", path, {}, initialRunState(), {
      automated: true,
    });
    expect(hit.state.collected.card_status).toBe("please enter your zip code");
    expect(hit.shouldComplete).toBe(true);
    expect(hit.state.completed).toBe(true);
    expect(hit.state.matchedFlowIds).toContain("flow-end");
  });

  it("blocks open end when sibling determination Steps stay unmatched", () => {
    const path: PathDocument = {
      id: "card-status-siblings",
      version: 2,
      setup: {
        name: "Card Status siblings",
        description: "",
        target: "1000",
        timeoutMs: 10_000,
        speechPreferences: { autoListen: true },
        inputs: [],
      },
      steps: [
        {
          id: "active",
          label: "card_active",
          when: "zip code",
          then: "",
          output: "card_active",
          rule: "Capture value after detect",
        },
        {
          id: "dead",
          label: "card_dead",
          when: "you gave me",
          then: "",
          output: "card_dead",
          rule: "Capture value after detect",
        },
        {
          id: "end",
          label: "end_call",
          when: "",
          then: "",
          output: "",
          rule: "End call",
        },
      ],
      conversationFlow: [
        {
          id: "flow-active",
          detect: "zip code",
          action: "extract",
          triggerLabel: "card_active",
        },
        {
          id: "flow-dead",
          detect: "you gave me",
          action: "extract",
          triggerLabel: "card_dead",
        },
        { id: "flow-end", detect: END_NOW_DETECT, action: "end" },
      ],
    };

    const afterActive = processPhrase("enter zip code", path, {}, initialRunState(), {
      automated: true,
    });
    expect(afterActive.state.collected.card_active).toBe("enter zip code");
    expect(afterActive.shouldComplete).toBe(false);

    // Open end must not fire: sibling determination Step is still unmatched.
    const afterNoise = processPhrase("thanks for calling", path, {}, afterActive.state, {
      automated: true,
    });
    expect(afterNoise.state.completed).toBe(false);
    expect(afterNoise.shouldComplete).toBe(false);
    expect(afterNoise.state.matchedFlowIds).toEqual(["flow-active"]);
  });

  it("completes synced wait steps only after priors are done", () => {
    const path: PathDocument = {
      id: "wait-flow",
      version: 2,
      setup: {
        name: "Wait flow",
        description: "",
        target: "1000",
        timeoutMs: 10_000,
        speechPreferences: { autoListen: true },
        inputs: [],
      },
      steps: [
        {
          id: "menu",
          label: "menu",
          when: "main menu",
          then: "1",
          output: "",
          rule: "Inject DTMF after detect",
        },
        {
          id: "wait",
          label: "wait_2s",
          when: "",
          then: "",
          output: "",
          rule: "Wait for IVR response",
          waitSeconds: 2,
        },
      ],
      conversationFlow: [
        { id: "flow-menu", detect: "main menu", action: "trigger", triggerLabel: "menu" },
        { id: "flow-wait", detect: "__wait_2__", action: "pass" },
      ],
    };

    expect(waitMsFromDetect("__wait_2__")).toBe(2_000);
    expect(completeWaitStep(path, initialRunState(), "flow-wait").matched).toBe(false);

    const afterMenu = processPhrase("main menu", path, {}, initialRunState(), {
      automated: true,
    });
    expect(getPendingFlowStep(path, afterMenu.state)?.id).toBe("flow-wait");

    const waited = completeWaitStep(path, afterMenu.state, "flow-wait");
    expect(waited.matched).toBe(true);
    expect(waited.state.matchedFlowIds).toEqual(["flow-menu", "flow-wait"]);
    expect(waited.state.log.at(-1)?.message).toContain("Waited 2");
  });

  it("surfaces per-step timeout outcomes", () => {
    const path: PathDocument = {
      id: "timeout-flow",
      version: 2,
      setup: {
        name: "Timeout flow",
        description: "",
        target: "1000",
        timeoutMs: 30_000,
        speechPreferences: { autoListen: true },
        inputs: [],
      },
      steps: [
        {
          id: "pin",
          label: "pin_entry",
          when: "enter pin",
          then: "1234#",
          output: "",
          rule: "Inject DTMF after detect",
          timeoutMs: 4_000,
        },
      ],
      conversationFlow: [
        {
          id: "flow-pin",
          detect: "enter pin",
          action: "trigger",
          triggerLabel: "pin_entry",
          timeoutMs: 4_000,
        },
      ],
    };

    const pending = getPendingFlowStep(path, initialRunState());
    expect(pending?.id).toBe("flow-pin");
    expect(stepTimeoutMs(path, pending!)).toBe(4_000);

    const timedOut = timeoutPendingStep(path, initialRunState(), "flow-pin");
    expect(timedOut.timedOutStep).toEqual({ step: "pin_entry", timeoutMs: 4_000 });
    expect(timedOut.state.log.at(-1)?.message).toContain("Timed out waiting");
    expect(timedOut.state.completed).toBe(false);
  });
});
