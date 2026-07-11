import type { TokenResponse, CallStateIngestResponse, HealthResponse, SessionLinkResponse } from "./types";

const API_URL = import.meta.env.VITE_API_URL || "/api";

export async function fetchHealth(): Promise<HealthResponse> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 5000);
  try {
    const res = await fetch(`${API_URL}/health`, { signal: controller.signal });
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function mintToken(
  userId: string,
  consent: { accepted: boolean; timestamp: string; terms_version: string }
): Promise<TokenResponse> {
  const res = await fetch(`${API_URL}/v1/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      call_mode: "client_mediated",
      consent,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Auth failed: ${res.statusText}`);
  }
  return res.json();
}

export async function linkConsentSession(
  token: string,
  sessionId: string
): Promise<SessionLinkResponse> {
  const res = await fetch(`${API_URL}/v1/consent/session`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Consent link failed: ${res.statusText}`);
  }
  return res.json();
}

export async function submitEncryptedCallState(
  token: string,
  sessionId: string,
  encryptedPayload: string,
  payloadNonce: string
): Promise<CallStateIngestResponse> {
  const res = await fetch(`${API_URL}/v1/callstate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      session_id: sessionId,
      encrypted_payload: encryptedPayload,
      payload_nonce: payloadNonce,
    }),
  });
  if (!res.ok) throw new Error(`Callstate submit failed: ${res.statusText}`);
  return res.json();
}

export async function exportCallState(token: string, sessionId: string) {
  const res = await fetch(`${API_URL}/v1/callstate/${sessionId}/export`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Export failed: ${res.statusText}`);
  return res.json();
}

export async function deleteCallState(token: string, sessionId: string): Promise<void> {
  const res = await fetch(`${API_URL}/v1/callstate/${sessionId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Delete failed: ${res.statusText}`);
}

export async function revokeToken(token: string): Promise<void> {
  await fetch(`${API_URL}/v1/revoke`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** Open native dialer — target number never sent to PromptPath servers. */
export function placeCallLocally(targetNumber: string): void {
  window.location.href = `tel:${encodeURIComponent(targetNumber)}`;
}
