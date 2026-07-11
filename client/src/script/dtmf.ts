/** Pause between DTMF digits so IVRs register each tone (ms). */
export const DTMF_INTER_DIGIT_MS = 550;

/** Extra pause after # or * — many IVRs need a beat before the next action. */
export const DTMF_POST_SPECIAL_MS = 200;

export function splitDtmfSequence(sequence: string): string[] {
  return [...sequence].filter((ch) => /[0-9#*]/.test(ch));
}

export function dtmfStepDelayMs(digit: string, nextDigit?: string): number {
  let delay = DTMF_INTER_DIGIT_MS;
  if (digit === "#" || digit === "*") delay += DTMF_POST_SPECIAL_MS;
  if (nextDigit === "#" || nextDigit === "*") delay += DTMF_POST_SPECIAL_MS / 2;
  return delay;
}
