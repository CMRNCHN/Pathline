import type { TokenResponse, CallStateIngestResponse, HealthResponse, SessionLinkResponse } from "./types";

declare global {
  interface Window {
    __pathlineApiBase?: string;
  }
}

function isAbsoluteHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

/**
 * Resolve the thin API origin.
 *
 * Prefer the desktop-injected absolute origin. Never use Vite's browser-dev
 * proxy path (`/api`) inside Tauri — that fetch hits the asset server, returns
 * HTML, and WebKit throws "The string did not match the expected pattern."
 */
export function apiUrl(): string {
  const injected = window.__pathlineApiBase?.trim();
  if (injected) return injected.replace(/\/+$/, "");

  const fromEnv = (import.meta.env.VITE_API_URL as string | undefined)?.trim();
  const inTauri = "__TAURI_INTERNALS__" in window;

  if (inTauri) {
    if (fromEnv && isAbsoluteHttpUrl(fromEnv)) return fromEnv.replace(/\/+$/, "");
    // Local desktop builds talk to the uvicorn sidecar started by desktop-dev /
    // launch-desktop. Production packages should inject PATHLINE_API_URL instead.
    return "http://127.0.0.1:8000";
  }

  if (fromEnv) return fromEnv.replace(/\/+$/, "");
  return "/api";
}

/** WebKit turns failed JSON.parse into "The string did not match the expected pattern." */
async function readResponseBody(res: Response): Promise<{ text: string; json: unknown | null }> {
  const text = await res.text();
  if (!text) return { text: "", json: null };
  try {
    return { text, json: JSON.parse(text) as unknown };
  } catch {
    return { text, json: null };
  }
}

function detailFromBody(json: unknown | null, fallback: string): string {
  if (json && typeof json === "object" && "detail" in json) {
    const detail = (json as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) return JSON.stringify(detail);
  }
  return fallback;
}

function httpErrorMessage(res: Response, json: unknown | null, text: string, fallback: string): string {
  const fromDetail = detailFromBody(json, "");
  if (fromDetail) return fromDetail;
  const trimmed = text.trim();
  if (trimmed && !trimmed.startsWith("<")) return trimmed.slice(0, 240);
  return `${fallback}: ${res.status} ${res.statusText || "error"}`;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 5000);
  try {
    const res = await fetch(`${apiUrl()}/health`, { signal: controller.signal });
    const { json, text } = await readResponseBody(res);
    if (!res.ok) {
      throw new Error(httpErrorMessage(res, json, text, "Health check failed"));
    }
    if (!json || typeof json !== "object") {
      throw new Error("Health check returned a non-JSON response. Is the Pathline API running?");
    }
    return json as HealthResponse;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function mintToken(
  userId: string,
  consent: { accepted: boolean; timestamp: string; terms_version: string }
): Promise<TokenResponse> {
  const res = await fetch(`${apiUrl()}/v1/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      call_mode: "client_mediated",
      consent,
    }),
  });
  const { json, text } = await readResponseBody(res);
  if (!res.ok) {
    throw new Error(httpErrorMessage(res, json, text, "Auth failed"));
  }
  if (!json || typeof json !== "object") {
    throw new Error("Auth succeeded but returned non-JSON. Check the Pathline API and database schema.");
  }
  return json as TokenResponse;
}

export async function linkConsentSession(
  token: string,
  sessionId: string
): Promise<SessionLinkResponse> {
  const res = await fetch(`${apiUrl()}/v1/consent/session`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ session_id: sessionId }),
  });
  const { json, text } = await readResponseBody(res);
  if (!res.ok) {
    throw new Error(httpErrorMessage(res, json, text, "Consent link failed"));
  }
  if (!json || typeof json !== "object") {
    throw new Error("Consent link returned non-JSON. Check the Pathline API.");
  }
  return json as SessionLinkResponse;
}

export async function submitEncryptedCallState(
  token: string,
  sessionId: string,
  encryptedPayload: string,
  payloadNonce: string,
  idempotencyKey: string
): Promise<CallStateIngestResponse> {
  const res = await fetch(`${apiUrl()}/v1/callstate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify({
      session_id: sessionId,
      encrypted_payload: encryptedPayload,
      payload_nonce: payloadNonce,
    }),
  });
  const { json, text } = await readResponseBody(res);
  if (!res.ok) {
    throw new Error(httpErrorMessage(res, json, text, "Callstate submit failed"));
  }
  if (!json || typeof json !== "object") {
    throw new Error("Callstate submit returned non-JSON. Check the Pathline API.");
  }
  return json as CallStateIngestResponse;
}

export async function exportCallState(token: string, sessionId: string) {
  const res = await fetch(`${apiUrl()}/v1/callstate/${sessionId}/export`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const { json, text } = await readResponseBody(res);
  if (!res.ok) {
    throw new Error(httpErrorMessage(res, json, text, "Export failed"));
  }
  if (!json || typeof json !== "object") {
    throw new Error("Export returned non-JSON. Check the Pathline API.");
  }
  return json;
}

export async function deleteCallState(token: string, sessionId: string): Promise<void> {
  const res = await fetch(`${apiUrl()}/v1/callstate/${sessionId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const { json, text } = await readResponseBody(res);
    throw new Error(httpErrorMessage(res, json, text, "Delete failed"));
  }
}

export async function revokeToken(token: string): Promise<void> {
  await fetch(`${apiUrl()}/v1/revoke`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** Open native dialer — target number never sent to Pathline servers. */
export function placeCallLocally(targetNumber: string): void {
  window.location.href = `tel:${encodeURIComponent(targetNumber)}`;
}
