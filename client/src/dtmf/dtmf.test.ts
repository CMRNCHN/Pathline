import { describe, expect, it, vi } from "vitest";
import {
  DTMF_WAIT_PAUSE_MS,
  countDtmfDigits,
  sendDtmfSequence,
  splitDtmfSequence,
} from "./dtmf";

describe("DTMF sequencing", () => {
  it("preserves ivr-tester w pauses while stripping unsupported characters", () => {
    expect(splitDtmfSequence("12wA#W*")).toEqual(["1", "2", "w", "#", "w", "*"]);
    expect(countDtmfDigits("12w#W*")).toBe(4);
  });

  it("waits for w pauses without sending them to the transport", async () => {
    vi.useFakeTimers();
    const sent: string[] = [];
    const run = sendDtmfSequence(async (digit) => {
      sent.push(digit);
    }, "1w2");

    await vi.runOnlyPendingTimersAsync();
    await vi.advanceTimersByTimeAsync(DTMF_WAIT_PAUSE_MS);
    await vi.runOnlyPendingTimersAsync();
    await run;

    expect(sent).toEqual(["1", "2"]);
    vi.useRealTimers();
  });
});
