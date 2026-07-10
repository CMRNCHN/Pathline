export type CallEventType =
  | "PROMPT"
  | "INPUT"
  | "API_REQUEST"
  | "TRANSFER"
  | "VERIFICATION_COMPLETE";

export type PathStep =
  | "GREETING"
  | "AUTHENTICATION"
  | "COLLECTING_MEMBER_ID"
  | "FINAL_RESPONSE";

export type CallStatePhase = "ACTIVE" | "COMPLETED";

export interface Path {
  id: string;
  intent: string;
  definedSteps: PathStep[];
}

export interface Source {
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

export interface CallState {
  sourceId: string;
  pathId: string;
  phase: CallStatePhase;
  progress: PathStep[];
  events: CallEvent[];
  activeStep: PathStep | null;
  finalOutcome: string | null;
}
