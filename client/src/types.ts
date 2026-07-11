import type { CallEvent } from "./callstate";

export interface TokenResponse {
  access_token: string;
  expires_in: number;
}

export interface CallStateIngestResponse {
  hashed_session_id: string;
  received_at: string;
  expires_at: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  mode: string;
}

export interface LocalCall {
  sessionId: string;
  scriptId: string;
  scriptName: string;
  targetNumber: string;
  phase: "pending" | "active" | "completed" | "failed";
  collected?: Record<string, string>;
  callEvents?: CallEvent[];
  startedAt: string;
}

export interface EncryptedCallStatePayload {
  phase: string;
  transcript_hash?: string;
  completed_at?: string;
}
