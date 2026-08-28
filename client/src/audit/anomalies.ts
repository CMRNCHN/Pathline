import type { CallEvent } from "../callstate";
import type { Anomaly, NextStep, Reference, RunInspectionReport } from "./types";

const LOOP_THRESHOLD = 3;

function eventRef(eventId: string | undefined, eventIndex: number, label: string): Reference {
  return { kind: "event", label, eventId, eventIndex };
}

function lastReachedIndex(events: CallEvent[]): number {
  for (let index = events.length - 1; index >= 0; index--) {
    const type = events[index].type;
    if (type === "STEP_COMPLETED" || type === "PHRASE_MATCHED" || type === "DTMF_SENT") {
      return index;
    }
  }
  return events.length ? events.length - 1 : -1;
}

function fieldRef(fieldPath: string, label: string): Reference {
  return { kind: "report_field", label, fieldPath };
}

export function detectAnomalies(report: RunInspectionReport, events: CallEvent[]): Anomaly[] {
  const anomalies: Anomaly[] = [];

  if (events.length === 0) {
    anomalies.push({
      code: "EMPTY_LEDGER",
      severity: "warn",
      explanation: "This Run has no audit events. Inspection can only show captured fields.",
      references: [fieldRef("summary.eventCount", "event count")],
    });
  }

  if (!report.ledger.ok) {
    anomalies.push({
      code: "LEDGER_INTEGRITY_BREAK",
      severity: "error",
      explanation: report.ledger.reason
        ? `Ledger chain failed verification (${report.ledger.reason}).`
        : "Ledger chain failed verification.",
      references: [
        fieldRef("ledger.breakIndex", "break index"),
        ...(report.ledger.breakIndex !== undefined
          ? [
              eventRef(
                events[report.ledger.breakIndex]?.id,
                report.ledger.breakIndex,
                "first bad event"
              ),
            ]
          : []),
      ],
    });
  }

  for (let index = 1; index < events.length; index++) {
    const prev = Date.parse(events[index - 1].timestamp);
    const current = Date.parse(events[index].timestamp);
    if (Number.isNaN(prev) || Number.isNaN(current) || current < prev) {
      anomalies.push({
        code: "NON_MONOTONIC_TIMELINE",
        severity: "error",
        explanation: "Event timestamps go backwards. The ledger may have been edited or clock-skewed.",
        references: [eventRef(events[index].id, index, "non-monotonic event")],
      });
      break;
    }
  }

  if (report.path.definedSteps.length > 0 && report.path.skippedSteps.length > 0) {
    const completed = report.identity.outcome === "completed";
    const lastReached = lastReachedIndex(events);
    anomalies.push({
      code: "STEP_SKIPPED",
      severity: completed ? "warn" : "info",
      explanation: completed
        ? `Completed Run skipped ${report.path.skippedSteps.length} defined step(s): ${report.path.skippedSteps.join(", ")}.`
        : `Defined step(s) were not reached: ${report.path.skippedSteps.join(", ")}.`,
      references: [
        fieldRef("path.skippedSteps", "skipped steps"),
        ...(lastReached >= 0
          ? [eventRef(events[lastReached]?.id, lastReached, "last reached event")]
          : []),
      ],
    });
  }

  let consecutive = 0;
  let lastStep: string | null = null;
  let loopStart = 0;
  for (let index = 0; index < events.length; index++) {
    const event = events[index];
    if (event.type !== "STEP_COMPLETED") continue;
    const step = typeof event.metadata?.step === "string" ? event.metadata.step : null;
    if (!step) continue;
    if (step === lastStep) {
      consecutive += 1;
    } else {
      lastStep = step;
      consecutive = 1;
      loopStart = index;
    }
    if (consecutive >= LOOP_THRESHOLD) {
      anomalies.push({
        code: "UNEXPECTED_LOOP",
        severity: "warn",
        explanation: `Step "${step}" completed ${consecutive} times in a row without Path progress.`,
        references: [eventRef(events[loopStart]?.id, loopStart, "loop start")],
      });
      break;
    }
  }

  const lastPromptIndex = events.map((event) => event.type).lastIndexOf("PROMPT_DETECTED");
  if (lastPromptIndex >= 0) {
    const after = events.slice(lastPromptIndex + 1);
    const acted = after.some(
      (event) =>
        event.type === "DTMF_SENT" ||
        event.type === "STEP_COMPLETED" ||
        event.type === "PHRASE_MATCHED"
    );
    if (!acted) {
      anomalies.push({
        code: "PROMPT_WITHOUT_ACTION",
        severity: "warn",
        explanation: "A prompt was heard after the last Path action. The Run ended without a matching step.",
        references: [eventRef(events[lastPromptIndex]?.id, lastPromptIndex, "last prompt")],
      });
    }
  }

  const hasEnded = events.some((event) => event.type === "CALL_ENDED");
  if (!hasEnded && events.length > 0) {
    anomalies.push({
      code: "STALLED_RUN",
      severity: "warn",
      explanation: "The ledger has no CALL_ENDED event.",
      references: [eventRef(events[events.length - 1]?.id, events.length - 1, "last event")],
    });
  }

  return anomalies;
}

export function generateNextSteps(report: RunInspectionReport): NextStep[] {
  const steps: NextStep[] = [];
  for (const anomaly of report.anomalies) {
    const cites = anomaly.references;
    if (cites.length === 0) continue;
    if (anomaly.code === "LEDGER_INTEGRITY_BREAK") {
      steps.push({
        action: "Inspect the first event that fails the hash chain",
        rationale: anomaly.explanation,
        cites,
      });
    } else if (anomaly.code === "STEP_SKIPPED") {
      steps.push({
        action: "Compare skipped steps to the Workflow definition",
        rationale: anomaly.explanation,
        cites,
      });
    } else if (anomaly.code === "UNEXPECTED_LOOP") {
      steps.push({
        action: "Review repeated keypad steps for an IVR menu loop",
        rationale: anomaly.explanation,
        cites,
      });
    } else {
      steps.push({
        action: `Review ${anomaly.code.replaceAll("_", " ").toLowerCase()}`,
        rationale: anomaly.explanation,
        cites,
      });
    }
  }
  return steps;
}
