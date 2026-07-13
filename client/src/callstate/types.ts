/** Observation-only call events. No secrets, transcripts, or audio. */
export type CallEventType =
  | "CALL_STARTED"
  | "PROMPT_DETECTED"
  | "PHRASE_MATCHED"
  | "DTMF_SENT"
  | "STEP_COMPLETED"
  | "CALL_ENDED";

export type CallOutcome = "COMPLETED" | "FAILED" | "ABANDONED";

export type StatusPhase = "ACTIVE" | "COMPLETED";

export interface Path {
  id: string;
  intent: string;
  definedSteps: string[];
}

export interface CallSource {
  id: string;
  targetEndpoint: string;
  connectionProtocol: "SIP" | "WEBRTC" | "NATIVE";
}

export interface CallEvent {
  id: string;
  timestamp: string;
  type: CallEventType;
  /** Non-sensitive metadata — e.g. step name, digit count, content hash. Never raw secrets. */
  metadata?: Record<string, unknown>;
}

export interface Call {
  callId: string;
  sourceId: string;
  pathId: string;
  events: CallEvent[];
}

export interface LiveStatus {
  callId: string;
  pathId: string;
  phase: StatusPhase;
  progress: string[];
  activeStep: string | null;
  events: CallEvent[];
  finalOutcome: CallOutcome | null;
}

/** @deprecated Use string step ids from Path metadata */
export type PathStep = string;
