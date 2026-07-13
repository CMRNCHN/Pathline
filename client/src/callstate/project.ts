import type { Call, CallOutcome, LiveStatus } from "./types";

const TERMINAL: CallOutcome[] = ["COMPLETED", "FAILED", "ABANDONED"];

function stepFromMetadata(metadata?: Record<string, unknown>): string | null {
  const step = metadata?.step;
  return typeof step === "string" ? step : null;
}

function outcomeFromMetadata(metadata?: Record<string, unknown>): CallOutcome | null {
  const outcome = metadata?.outcome;
  if (outcome === "COMPLETED" || outcome === "FAILED" || outcome === "ABANDONED") return outcome;
  return null;
}

/** Read-only projection from immutable event ledger. */
export const projectLiveStatus = (call: Call, path: { definedSteps: string[] }): LiveStatus => {
  const { events, callId, pathId } = call;

  const completedSteps = new Set<string>();
  for (const event of events) {
    const step = stepFromMetadata(event.metadata);
    if (step && (event.type === "STEP_COMPLETED" || event.type === "PHRASE_MATCHED" || event.type === "DTMF_SENT")) {
      completedSteps.add(step);
    }
  }

  const progress = path.definedSteps.filter((step) => completedSteps.has(step));
  const terminal = [...events].reverse().find((e) => e.type === "CALL_ENDED");
  const isCompleted = terminal !== undefined;
  const finalOutcome = terminal ? outcomeFromMetadata(terminal.metadata) : null;

  const lastStep = events.length
    ? stepFromMetadata(events[events.length - 1].metadata)
    : null;

  return {
    callId,
    pathId,
    phase: isCompleted ? "COMPLETED" : "ACTIVE",
    progress,
    events,
    activeStep: isCompleted ? null : lastStep ?? path.definedSteps[0] ?? null,
    finalOutcome,
  };
};

export function isTerminalOutcome(outcome: CallOutcome | null): boolean {
  return outcome !== null && TERMINAL.includes(outcome);
}
