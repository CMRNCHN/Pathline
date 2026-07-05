/**
 * Client-side encryption utilities.
 * Secrets and status payloads are encrypted on-device before any server contact.
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

async function getOrCreateStatusKey(): Promise<CryptoKey> {
  const stored = sessionStorage.getItem("pp_status_key");
  if (stored) {
    const raw = fromBase64(stored);
    return crypto.subtle.importKey("raw", raw as BufferSource, { name: "AES-GCM" }, false, ["encrypt"]);
  }
  const key = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt", "decrypt"]);
  const raw = await crypto.subtle.exportKey("raw", key);
  sessionStorage.setItem("pp_status_key", toBase64(raw));
  return key;
}

export async function encryptStatusPayload(
  payload: Record<string, unknown>
): Promise<{ ciphertext: string; nonce: string }> {
  const key = await getOrCreateStatusKey();
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
  sessionStorage.removeItem("pp_status_key");
}
