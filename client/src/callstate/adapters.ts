import type { PathDocument, RunLogEntry } from "../script/types";
import type { Call, CallEvent, CallEventType } from "./types";

export function pathFromScript(script: PathDocument) {
  const steps = script.steps
    .filter((r) => r.rule !== "End call")
    .map((r) => r.label || r.when.slice(0, 32));

  return {
    id: script.id,
    intent: script.setup.name || script.id,
    definedSteps: steps.length ? steps : ["start"],
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
      return "PROMPT_DETECTED";
    case "extract":
    case "validate":
      return "STEP_COMPLETED";
    case "end":
      return "CALL_ENDED";
    default:
      return "PHRASE_MATCHED";
  }
}

/** Maps legacy run logs to observation events (no secret content). */
export function runLogToCallEvents(log: RunLogEntry[], path: { definedSteps: string[] }): CallEvent[] {
  return log.map((entry, index) => ({
    id: `run-${index}`,
    timestamp: entry.at,
    type: logKindToEventType(entry.kind),
    metadata: {
      step: path.definedSteps[Math.min(index, path.definedSteps.length - 1)],
      kind: entry.kind,
    },
  }));
}

export function newCallEvent(
  type: CallEventType,
  metadata: Record<string, unknown> = {},
  timestamp = new Date().toISOString()
): CallEvent {
  return {
    id: crypto.randomUUID(),
    timestamp,
    type,
    metadata,
  };
}
