import { stepFromMetadata, type CallEvent } from "../callstate";
import type { RunRecord } from "../history/runHistory";
import { statusAtOffset } from "./cursor";
import type { ArtifactAvailability, ChronologyEntry, RunInspectionReport } from "./types";
import { verifyLedger } from "./verifyLedger";
import { detectAnomalies, generateNextSteps } from "./anomalies";

const ACTION_TYPES = new Set(["DTMF_SENT", "STEP_COMPLETED", "PHRASE_MATCHED"]);

function parseTime(iso: string): number {
  const value = Date.parse(iso);
  return Number.isNaN(value) ? 0 : value;
}

function buildChronology(events: CallEvent[]): ChronologyEntry[] {
  if (events.length === 0) return [];
  const origin = parseTime(events[0].timestamp);
  return events.map((event, seq) => {
    const tMs = Math.max(0, parseTime(event.timestamp) - origin);
    const prev = seq === 0 ? origin : parseTime(events[seq - 1].timestamp);
    const step = stepFromMetadata(event.metadata);
    return {
      seq,
      type: event.type,
      tMs,
      deltaMs: seq === 0 ? 0 : Math.max(0, parseTime(event.timestamp) - prev),
      eventId: event.id,
      ...(step ? { step } : {}),
    };
  });
}

function artifactAvailability(events: CallEvent[]): ArtifactAvailability[] {
  return [
    {
      artifact: "event_log",
      available: events.length > 0,
      detail: events.length > 0 ? `${events.length} events` : "No ledger events on this Run",
    },
    {
      artifact: "recording",
      available: false,
      detail: "Call audio is not retained; PCM is transcribed in memory and discarded",
    },
  ];
}

export async function inspectRun(record: RunRecord): Promise<RunInspectionReport> {
  const events = record.ledgerEvents ?? [];
  const definedSteps = record.definedSteps ?? [];
  const ledger = await verifyLedger(record.runId, events);
  const chronology = buildChronology(events);
  const origin = events[0] ? parseTime(events[0].timestamp) : 0;
  const lastTs = events.length ? parseTime(events[events.length - 1].timestamp) : origin;
  const gaps = chronology.map((entry) => entry.deltaMs);
  const largestGapMs = gaps.length ? Math.max(...gaps) : 0;

  const live = statusAtOffset(record.runId, record.pathId, definedSteps, events, events.length - 1);
  const reached = new Set(live.progress);
  const skippedSteps = definedSteps.filter((step) => !reached.has(step));

  const firstPrompt = events.find((event) => event.type === "PROMPT_DETECTED");
  const lastPrompt = [...events].reverse().find((event) => event.type === "PROMPT_DETECTED");
  const ended = [...events].reverse().find((event) => event.type === "CALL_ENDED");

  const notes: string[] = [];
  if (!ledger.ok) notes.push("ledger_integrity_break");
  if (events.length === 0) notes.push("empty_ledger");
  if (largestGapMs >= 30_000) notes.push("large_timeline_gap");

  const report: RunInspectionReport = {
    schemaVersion: "1.0",
    identity: {
      runId: record.runId,
      pathId: record.pathId,
      pathName: record.pathName,
      outcome: record.outcome,
    },
    artifactAvailability: artifactAvailability(events),
    summary: {
      eventCount: events.length,
      promptCount: events.filter((event) => event.type === "PROMPT_DETECTED").length,
      actionCount: events.filter((event) => ACTION_TYPES.has(event.type)).length,
      firstEventAt: events[0]?.timestamp,
      lastEventAt: events[events.length - 1]?.timestamp,
      durationMs: Math.max(0, lastTs - origin),
      largestGapMs,
      notes,
    },
    chronology,
    path: {
      definedSteps,
      progress: live.progress,
      skippedSteps,
      activeStep: live.activeStep,
      finalOutcome: live.finalOutcome,
    },
    correlation: {
      startToFirstPromptMs: firstPrompt ? Math.max(0, parseTime(firstPrompt.timestamp) - origin) : null,
      lastPromptToEndMs:
        lastPrompt && ended
          ? Math.max(0, parseTime(ended.timestamp) - parseTime(lastPrompt.timestamp))
          : null,
    },
    ledger,
    anomalies: [],
    nextSteps: [],
  };

  report.anomalies = detectAnomalies(report, events);
  report.nextSteps = generateNextSteps(report);
  return report;
}
