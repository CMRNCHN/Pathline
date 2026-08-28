import {
  callFromSession,
  projectLiveStatus,
  stepFromMetadata,
  type CallEvent,
  type LiveStatus,
} from "../callstate";

export interface StatusDiff {
  addedSteps: string[];
  removedSteps: string[];
  activeStepChanged: boolean;
  phaseChanged: boolean;
  lastEventType?: string;
}

export function eventsThroughOffset(events: CallEvent[], offset: number): CallEvent[] {
  if (events.length === 0) return [];
  const clamped = Math.min(Math.max(offset, 0), events.length - 1);
  return events.slice(0, clamped + 1);
}

/** Deterministic LiveStatus at ledger offset `n` (inclusive). */
export function statusAtOffset(
  runId: string,
  pathId: string,
  definedSteps: string[],
  events: CallEvent[],
  offset: number
): LiveStatus {
  const prefix = eventsThroughOffset(events, offset);
  return projectLiveStatus(callFromSession(runId, "local-client", pathId, prefix), {
    definedSteps,
  });
}

export function diffStatus(before: LiveStatus, after: LiveStatus): StatusDiff {
  const beforeSet = new Set(before.progress);
  const afterSet = new Set(after.progress);
  const addedSteps = after.progress.filter((step) => !beforeSet.has(step));
  const removedSteps = before.progress.filter((step) => !afterSet.has(step));
  const last = after.events[after.events.length - 1];
  return {
    addedSteps,
    removedSteps,
    activeStepChanged: before.activeStep !== after.activeStep,
    phaseChanged: before.phase !== after.phase,
    lastEventType: last?.type,
  };
}

export function stepAtEvent(event: CallEvent | undefined): string | null {
  return event ? stepFromMetadata(event.metadata) : null;
}
