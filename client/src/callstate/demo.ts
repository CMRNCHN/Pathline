import type { Call, CallEvent } from "./types";
import { projectLiveStatus } from "./project";

export const DEMO_PATH = {
  id: "medicare-verification",
  intent: "Medicare verification",
  definedSteps: ["GREETING", "AUTHENTICATION", "COLLECTING_MEMBER_ID", "FINAL_RESPONSE"],
};

export const DEMO_CALL_ID = "demo-call-001";
export const DEMO_SOURCE_ID = "local-sip-client";

const ts = (h: number, m: number, s: number) =>
  new Date(2026, 0, 15, h, m, s).toISOString();

export const DEMO_ACTIVE_EVENTS: CallEvent[] = [
  { id: "e1", timestamp: ts(10, 42, 1), type: "CALL_STARTED", metadata: {} },
  { id: "e2", timestamp: ts(10, 42, 4), type: "PHRASE_MATCHED", metadata: { step: "GREETING" } },
  { id: "e3", timestamp: ts(10, 42, 5), type: "STEP_COMPLETED", metadata: { step: "AUTHENTICATION" } },
];

export const DEMO_COMPLETED_EVENTS: CallEvent[] = [
  ...DEMO_ACTIVE_EVENTS,
  { id: "e4", timestamp: ts(10, 42, 8), type: "STEP_COMPLETED", metadata: { step: "FINAL_RESPONSE" } },
  {
    id: "e5",
    timestamp: ts(10, 42, 12),
    type: "CALL_ENDED",
    metadata: { step: "FINAL_RESPONSE", outcome: "COMPLETED" },
  },
];

export const DEMO_ACTIVE_CALL: Call = {
  callId: DEMO_CALL_ID,
  sourceId: DEMO_SOURCE_ID,
  pathId: DEMO_PATH.id,
  events: DEMO_ACTIVE_EVENTS,
};

export const DEMO_COMPLETED_CALL: Call = {
  callId: DEMO_CALL_ID,
  sourceId: DEMO_SOURCE_ID,
  pathId: DEMO_PATH.id,
  events: DEMO_COMPLETED_EVENTS,
};

export const DEMO_ACTIVE_LIVE_STATUS = projectLiveStatus(DEMO_ACTIVE_CALL, DEMO_PATH);
export const DEMO_COMPLETED_LIVE_STATUS = projectLiveStatus(DEMO_COMPLETED_CALL, DEMO_PATH);
