import type { Call, CallEventType, CallOutcome, LiveStatus, Path } from "./types";

const TERMINAL_EVENT_TYPES: CallEventType[] = [
  "VERIFICATION_COMPLETE",
  "FAILED",
  "ABANDONED",
];

function outcomeFromTerminalEvent(type: CallEventType): CallOutcome {
  switch (type) {
    case "VERIFICATION_COMPLETE":
      return "VERIFICATION_COMPLETE";
    case "FAILED":
      return "FAILED";
    case "ABANDONED":
      return "ABANDONED";
    default:
      return "FAILED";
  }
}

export const projectLiveStatus = (call: Call, path: Path): LiveStatus => {
  const { events, callId, pathId } = call;

  const completedSteps = new Set(events.map((e) => e.step));
  const progress = path.definedSteps.filter((step) => completedSteps.has(step));

  const lastTerminal = [...events].reverse().find((e) => TERMINAL_EVENT_TYPES.includes(e.type));
  const isCompleted = lastTerminal !== undefined;

  return {
    callId,
    pathId,
    phase: isCompleted ? "COMPLETED" : "ACTIVE",
    progress,
    events,
    activeStep: isCompleted ? null : events[events.length - 1]?.step ?? path.definedSteps[0],
    finalOutcome: lastTerminal ? outcomeFromTerminalEvent(lastTerminal.type) : null,
  };
};
