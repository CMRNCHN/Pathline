import type { Call, CallEvent, Path } from "./types";
import { projectLiveStatus } from "./project";

export const MEDICARE_PATH: Path = {
  id: "medicare-verification",
  intent: "MEDICARE_VERIFICATION",
  definedSteps: ["GREETING", "AUTHENTICATION", "COLLECTING_MEMBER_ID", "FINAL_RESPONSE"],
};

export const DEMO_CALL_ID = "demo-call-001";
export const DEMO_SOURCE_ID = "local-sip-client";

const ts = (h: number, m: number, s: number) =>
  new Date(2026, 0, 15, h, m, s).toISOString();

export const DEMO_ACTIVE_EVENTS: CallEvent[] = [
  { id: "e1", timestamp: ts(10, 42, 1), type: "PROMPT", step: "GREETING" },
  { id: "e2", timestamp: ts(10, 42, 4), type: "INPUT", step: "AUTHENTICATION" },
  { id: "e3", timestamp: ts(10, 42, 5), type: "API_REQUEST", step: "COLLECTING_MEMBER_ID" },
];

export const DEMO_COMPLETED_EVENTS: CallEvent[] = [
  ...DEMO_ACTIVE_EVENTS,
  { id: "e4", timestamp: ts(10, 42, 8), type: "TRANSFER", step: "FINAL_RESPONSE" },
  { id: "e5", timestamp: ts(10, 42, 12), type: "VERIFICATION_COMPLETE", step: "FINAL_RESPONSE" },
];

export const DEMO_ACTIVE_CALL: Call = {
  callId: DEMO_CALL_ID,
  sourceId: DEMO_SOURCE_ID,
  pathId: MEDICARE_PATH.id,
  events: DEMO_ACTIVE_EVENTS,
};

export const DEMO_COMPLETED_CALL: Call = {
  callId: DEMO_CALL_ID,
  sourceId: DEMO_SOURCE_ID,
  pathId: MEDICARE_PATH.id,
  events: DEMO_COMPLETED_EVENTS,
};

export const DEMO_ACTIVE_LIVE_STATUS = projectLiveStatus(DEMO_ACTIVE_CALL, MEDICARE_PATH);
export const DEMO_COMPLETED_LIVE_STATUS = projectLiveStatus(DEMO_COMPLETED_CALL, MEDICARE_PATH);
