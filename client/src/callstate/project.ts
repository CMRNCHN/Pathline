import type { CallEvent, CallState, Path } from "./types";

export const projectCallState = (
  events: CallEvent[],
  path: Path,
  sourceId: string
): CallState => {
  const isCompleted = events.some(
    (e) => e.type === "VERIFICATION_COMPLETE" || e.type === "TRANSFER"
  );
  const progress = Array.from(new Set(events.map((e) => e.step)));

  return {
    sourceId,
    pathId: path.id,
    phase: isCompleted ? "COMPLETED" : "ACTIVE",
    progress,
    events,
    activeStep: isCompleted ? null : progress[progress.length - 1] || path.definedSteps[0],
    finalOutcome: isCompleted ? events[events.length - 1].type : null,
  };
};
