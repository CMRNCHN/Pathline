import type { PathDocument, RunLogEntry } from "../script/types";
import type { Call, CallEvent, CallEventType } from "./types";

/** Observation-only Workflow snapshot stored with a Run. No When/Then secrets. */
export interface PathSnapshot {
  id: string;
  version: number;
  name: string;
  steps: { id: string; label: string; rule: string }[];
}

export function pathSnapshotFromScript(script: PathDocument): PathSnapshot {
  const steps = script.steps
    .filter((r) => r.rule !== "End call")
    .map((r) => ({
      id: r.id,
      label: r.label || r.when.slice(0, 32),
      rule: r.rule,
    }));
  return {
    id: script.id,
    version: script.version,
    name: script.setup.name || script.id,
    steps,
  };
}

export function definedStepsFromSnapshot(snapshot: PathSnapshot): string[] {
  const labels = snapshot.steps.map((step) => step.label).filter(Boolean);
  return labels.length ? labels : ["start"];
}

export function definedStepsForRecord(record: {
  definedSteps?: string[];
  pathSnapshot?: PathSnapshot;
}): string[] {
  if (record.pathSnapshot) return definedStepsFromSnapshot(record.pathSnapshot);
  if (record.definedSteps && record.definedSteps.length > 0) return record.definedSteps;
  return [];
}

export function pathFromScript(script: PathDocument) {
  const snapshot = pathSnapshotFromScript(script);
  return {
    id: snapshot.id,
    intent: snapshot.name,
    definedSteps: definedStepsFromSnapshot(snapshot),
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
