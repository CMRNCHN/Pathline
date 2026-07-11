/**
 * Client-side encryption utilities.
 * Secrets and callstate payloads are encrypted on-device before any server contact.
 */

function toBase64(buffer: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)));
}

function fromBase64(b64: string): Uint8Array {
  return Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
}

export interface EncryptedBlob {
  ciphertext: string;
  nonce: string;
  key_id: string;
}

const CALLSTATE_KEY = "pp_callstate_key";
const LEGACY_STATUS_KEY = "pp_status_key";

async function getOrCreateCallStateKey(): Promise<CryptoKey> {
  const stored = sessionStorage.getItem(CALLSTATE_KEY) ?? sessionStorage.getItem(LEGACY_STATUS_KEY);
  if (stored) {
    const raw = fromBase64(stored);
    return crypto.subtle.importKey("raw", raw as BufferSource, { name: "AES-GCM" }, false, ["encrypt"]);
  }
  const key = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt", "decrypt"]);
  const raw = await crypto.subtle.exportKey("raw", key);
  sessionStorage.setItem(CALLSTATE_KEY, toBase64(raw));
  sessionStorage.removeItem(LEGACY_STATUS_KEY);
  return key;
}

export async function encryptCallStatePayload(
  payload: Record<string, unknown>
): Promise<{ ciphertext: string; nonce: string }> {
  const key = await getOrCreateCallStateKey();
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const plaintext = new TextEncoder().encode(JSON.stringify(payload));
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, plaintext);
  return { ciphertext: toBase64(ciphertext), nonce: toBase64(iv.buffer) };
}

export async function encryptSecrets(
  secrets: Record<string, string>,
  keyId = "client-local"
): Promise<EncryptedBlob> {
  const key = await crypto.subtle.generateKey(
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt"]
  );
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const plaintext = new TextEncoder().encode(JSON.stringify(secrets));
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, plaintext);
  return { ciphertext: toBase64(ciphertext), nonce: toBase64(iv.buffer), key_id: keyId };
}

export function generateUserId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function generateSessionId(): string {
  return crypto.randomUUID();
}

export function clearLocalKeys(): void {
  sessionStorage.removeItem(CALLSTATE_KEY);
  sessionStorage.removeItem(LEGACY_STATUS_KEY);
}
