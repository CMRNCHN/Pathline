import type { CallEvent, Path, Source } from "./types";
import { projectCallState } from "./project";

export const MEDICARE_PATH: Path = {
  id: "medicare-verification",
  intent: "MEDICARE VERIFICATION",
  definedSteps: ["GREETING", "AUTHENTICATION", "COLLECTING_MEMBER_ID", "FINAL_RESPONSE"],
};

export const DEMO_SOURCE: Source = {
  id: "local-client",
  targetEndpoint: "client-mediated",
  connectionProtocol: "SIP",
};

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

export const DEMO_ACTIVE_CALLSTATE = projectCallState(
  DEMO_ACTIVE_EVENTS,
  MEDICARE_PATH,
  DEMO_SOURCE.id
);

export const DEMO_COMPLETED_CALLSTATE = projectCallState(
  DEMO_COMPLETED_EVENTS,
  MEDICARE_PATH,
  DEMO_SOURCE.id
);
