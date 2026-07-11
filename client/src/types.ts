export interface TokenResponse {
  access_token: string;
  expires_in: number;
}

export interface StatusIngestResponse {
  hashed_session_id: string;
  received_at: string;
  expires_at: string;
}

export interface LocalSession {
  sessionId: string;
  scriptId: string;
  scriptName: string;
  targetNumber: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  collected?: Record<string, string>;
  startedAt: string;
}

export interface EncryptedStatusPayload {
  status: string;
  transcript_hash?: string;
  completed_at?: string;
}
