export type CallEventType =
  | "PROMPT"
  | "INPUT"
  | "API_REQUEST"
  | "TRANSFER"
  | "VERIFICATION_COMPLETE"
  | "FAILED"
  | "ABANDONED";

export type PathStep =
  | "GREETING"
  | "AUTHENTICATION"
  | "COLLECTING_MEMBER_ID"
  | "FINAL_RESPONSE";

export type StatusPhase = "ACTIVE" | "COMPLETED";

export type CallOutcome =
  | "VERIFICATION_COMPLETE"
  | "TRANSFERRED"
  | "FAILED"
  | "ABANDONED";

export interface Path {
  id: string;
  intent: "MEDICARE_VERIFICATION";
  definedSteps: PathStep[];
}

/** Infrastructure metadata — not part of LiveStatus projection. */
export interface CallSource {
  id: string;
  targetEndpoint: string;
  connectionProtocol: "SIP" | "WEBRTC";
}

export interface CallEvent {
  id: string;
  timestamp: string;
  type: CallEventType;
  step: PathStep;
}

/** Immutable event ledger for a single call. */
export interface Call {
  callId: string;
  sourceId: string;
  pathId: string;
  events: CallEvent[];
}

/** Read-only projection: where is this call and what happened? */
export interface LiveStatus {
  callId: string;
  pathId: string;
  phase: StatusPhase;
  progress: PathStep[];
  activeStep: PathStep | null;
  events: CallEvent[];
  finalOutcome: CallOutcome | null;
}
