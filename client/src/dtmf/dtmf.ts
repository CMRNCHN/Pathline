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

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export async function hashDtmfSequence(sequence: string): Promise<string> {
  const data = new TextEncoder().encode(sequence);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Sends a DTMF sequence with inter-digit timing. Transport-agnostic — no SIP/UI knowledge. */
export async function sendDtmfSequence(
  send: (digit: string, durationMs: number) => Promise<void>,
  sequence: string,
  digitDurationMs = 150
): Promise<void> {
  const digits = splitDtmfSequence(sequence);
  for (let i = 0; i < digits.length; i++) {
    await send(digits[i], digitDurationMs);
    const next = digits[i + 1];
    if (next) await sleep(dtmfStepDelayMs(digits[i], next));
  }
}
