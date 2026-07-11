import type { PathDocument, RunLogEntry } from "../script/types";
import type { Call, CallEvent, CallEventType, Path, PathStep } from "./types";

const DEFAULT_STEPS: PathStep[] = [
  "GREETING",
  "AUTHENTICATION",
  "COLLECTING_MEMBER_ID",
  "FINAL_RESPONSE",
];

export function pathFromScript(script: PathDocument): Path {
  const ruleSteps = script.steps
    .filter((r) => r.rule !== "End call")
    .map((_, i) => DEFAULT_STEPS[Math.min(i, DEFAULT_STEPS.length - 1)]);

  return {
    id: script.id,
    intent: "MEDICARE_VERIFICATION",
    definedSteps: ruleSteps.length ? ruleSteps : DEFAULT_STEPS,
  };
}

export function callFromSession(
  callId: string,
  sourceId: string,
  pathId: string,
  events: CallEvent[]
): Call {
  return { callId, sourceId, pathId, events };
}

function logKindToEventType(kind: RunLogEntry["kind"]): CallEventType {
  switch (kind) {
    case "trigger":
      return "PROMPT";
    case "extract":
    case "validate":
      return "API_REQUEST";
    case "end":
      return "VERIFICATION_COMPLETE";
    case "pass":
      return "INPUT";
    default:
      return "INPUT";
  }
}

export function runLogToCallEvents(log: RunLogEntry[], path: Path): CallEvent[] {
  return log.map((entry, index) => ({
    id: `run-${index}`,
    timestamp: entry.at,
    type: logKindToEventType(entry.kind),
    step: path.definedSteps[Math.min(index, path.definedSteps.length - 1)],
  }));
}

export function newCallEvent(
  type: CallEventType,
  step: PathStep,
  timestamp = new Date().toISOString()
): CallEvent {
  return {
    id: crypto.randomUUID(),
    timestamp,
    type,
    step,
  };
}
