import { describe, expect, it } from "vitest";
import { EventLedger, eventChainHash, type CallEvent } from "../callstate";
import type { RunRecord } from "../history/runHistory";
import { detectAnomalies } from "./anomalies";
import { diffStatus, statusAtOffset } from "./cursor";
import { buildEvidencePack } from "./evidence";
import { inspectRun } from "./inspect";
import { verifyLedger } from "./verifyLedger";
import { buildStoreZip } from "./zip";

async function eventsFor(
  callId: string,
  items: { type: CallEvent["type"]; metadata?: Record<string, unknown> }[]
): Promise<CallEvent[]> {
  const ledger = new EventLedger(callId);
  for (const item of items) {
    await ledger.append(item);
  }
  return ledger.getEvents();
}

function recordFor(events: CallEvent[], extra: Partial<RunRecord> = {}): RunRecord {
  return {
    runId: extra.runId ?? "run-1",
    pathId: extra.pathId ?? "path-1",
    pathName: extra.pathName ?? "Lab path",
    outcome: extra.outcome ?? "completed",
    startedAt: extra.startedAt ?? "2026-01-01T00:00:00.000Z",
    completedAt: extra.completedAt ?? "2026-01-01T00:01:00.000Z",
    captured: extra.captured ?? {},
    ledgerEvents: events,
    definedSteps: extra.definedSteps ?? ["main_menu", "pin_entry"],
  };
}

describe("verifyLedger", () => {
  it("accepts a freshly appended chain", async () => {
    const events = await eventsFor("run-1", [
      { type: "CALL_STARTED", metadata: { transport: "simulator" } },
      { type: "PROMPT_DETECTED", metadata: { phraseLength: 12 } },
      { type: "PHRASE_MATCHED", metadata: { step: "main_menu", phraseLength: 12 } },
      { type: "DTMF_SENT", metadata: { step: "main_menu", digits: 1, hash: "abc" } },
      { type: "CALL_ENDED", metadata: { outcome: "COMPLETED" } },
    ]);
    const result = await verifyLedger("run-1", events);
    expect(result.ok).toBe(true);
    expect(result.eventCount).toBe(5);
    expect(typeof eventChainHash(events[3].metadata)).toBe("string");
    expect(events[3].metadata?.hash).toBe("abc");
  });

  it("detects a tampered chain hash", async () => {
    const events = await eventsFor("run-1", [
      { type: "CALL_STARTED" },
      { type: "CALL_ENDED", metadata: { outcome: "FAILED" } },
    ]);
    const tampered = events.map((event, index) =>
      index === 1
        ? { ...event, metadata: { ...event.metadata, chainHash: "0".repeat(64) } }
        : event
    );
    const result = await verifyLedger("run-1", tampered);
    expect(result.ok).toBe(false);
    expect(result.breakIndex).toBe(1);
  });
});

describe("statusAtOffset", () => {
  it("projects only events through the cursor", async () => {
    const events = await eventsFor("run-1", [
      { type: "CALL_STARTED" },
      { type: "PHRASE_MATCHED", metadata: { step: "main_menu" } },
      { type: "STEP_COMPLETED", metadata: { step: "main_menu" } },
      { type: "CALL_ENDED", metadata: { outcome: "COMPLETED" } },
    ]);
    const early = statusAtOffset("run-1", "path-1", ["main_menu", "pin_entry"], events, 0);
    expect(early.progress).toEqual([]);
    expect(early.phase).toBe("ACTIVE");

    const afterStep = statusAtOffset("run-1", "path-1", ["main_menu", "pin_entry"], events, 2);
    expect(afterStep.progress).toEqual(["main_menu"]);
    expect(afterStep.phase).toBe("ACTIVE");

    const end = statusAtOffset("run-1", "path-1", ["main_menu", "pin_entry"], events, 3);
    expect(end.phase).toBe("COMPLETED");
    const delta = diffStatus(afterStep, end);
    expect(delta.phaseChanged).toBe(true);
  });
});

describe("detectAnomalies", () => {
  it("flags skipped steps on a completed run", async () => {
    const events = await eventsFor("run-1", [
      { type: "CALL_STARTED" },
      { type: "PHRASE_MATCHED", metadata: { step: "main_menu" } },
      { type: "STEP_COMPLETED", metadata: { step: "main_menu" } },
      { type: "CALL_ENDED", metadata: { outcome: "COMPLETED" } },
    ]);
    const report = await inspectRun(recordFor(events, { outcome: "completed" }));
    expect(report.anomalies.map((anomaly) => anomaly.code)).toContain("STEP_SKIPPED");
  });

  it("flags a consecutive step loop", async () => {
    const events = await eventsFor("run-1", [
      { type: "STEP_COMPLETED", metadata: { step: "main_menu" } },
      { type: "STEP_COMPLETED", metadata: { step: "main_menu" } },
      { type: "STEP_COMPLETED", metadata: { step: "main_menu" } },
      { type: "CALL_ENDED", metadata: { outcome: "FAILED" } },
    ]);
    const report = await inspectRun(recordFor(events, { outcome: "failed" }));
    expect(report.anomalies.map((anomaly) => anomaly.code)).toContain("UNEXPECTED_LOOP");
  });

  it("flags a prompt with no following action", async () => {
    const events = await eventsFor("run-1", [
      { type: "CALL_STARTED" },
      { type: "PROMPT_DETECTED", metadata: { phraseLength: 8 } },
      { type: "CALL_ENDED", metadata: { outcome: "FAILED" } },
    ]);
    const report = await inspectRun(recordFor(events, { outcome: "failed" }));
    expect(report.anomalies.map((anomaly) => anomaly.code)).toContain("PROMPT_WITHOUT_ACTION");
  });

  it("flags a missing CALL_ENDED as stalled", () => {
    const events: CallEvent[] = [
      {
        id: "e1",
        timestamp: "2026-01-01T00:00:00.000Z",
        type: "CALL_STARTED",
        metadata: { chainHash: "x", prevHash: "" },
      },
    ];
    const anomalies = detectAnomalies(
      {
        schemaVersion: "1.0",
        identity: { runId: "run-1", pathId: "p", pathName: "p", outcome: "failed" },
        artifactAvailability: [],
        summary: {
          eventCount: 1,
          promptCount: 0,
          actionCount: 0,
          durationMs: 0,
          largestGapMs: 0,
          notes: [],
        },
        chronology: [],
        path: { definedSteps: [], progress: [], skippedSteps: [], activeStep: null, finalOutcome: null },
        correlation: { startToFirstPromptMs: null, lastPromptToEndMs: null },
        ledger: { ok: true, eventCount: 1 },
        anomalies: [],
        nextSteps: [],
      },
      events
    );
    expect(anomalies.map((anomaly) => anomaly.code)).toContain("STALLED_RUN");
  });

  it("flags non-monotonic timestamps", async () => {
    const events = await eventsFor("run-1", [{ type: "CALL_STARTED" }, { type: "CALL_ENDED" }]);
    events[1] = { ...events[1], timestamp: "2000-01-01T00:00:00.000Z" };
    const report = await inspectRun(recordFor(events, { outcome: "failed" }));
    expect(report.anomalies.map((anomaly) => anomaly.code)).toContain("NON_MONOTONIC_TIMELINE");
  });
});

describe("evidence pack", () => {
  it("writes a store zip with integrity hashes", async () => {
    const events = await eventsFor("run-1", [
      { type: "CALL_STARTED" },
      { type: "CALL_ENDED", metadata: { outcome: "COMPLETED" } },
    ]);
    const report = await inspectRun(recordFor(events));
    const pack = await buildEvidencePack(recordFor(events, { captured: { balance: "ok" } }), report);
    expect(pack.filename).toMatch(/pathline-evidence-run-1\.zip/);
    expect(pack.bytes[0]).toBe(0x50);
    expect(pack.bytes[1]).toBe(0x4b);
    expect(pack.files.map((file) => file.name)).toEqual([
      "run.json",
      "ledger.json",
      "inspection.json",
      "integrity.json",
    ]);
    expect(pack.files.every((file) => file.sha256.length === 64)).toBe(true);
  });

  it("round-trips zip local headers", () => {
    const bytes = buildStoreZip([{ name: "hello.txt", bytes: new TextEncoder().encode("hi") }]);
    expect(String.fromCharCode(bytes[0], bytes[1])).toBe("PK");
  });
});
