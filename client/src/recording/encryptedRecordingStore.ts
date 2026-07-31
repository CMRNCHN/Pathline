import { sealVaultSecret, unsealVaultSecret } from "@/crypto";

const INDEX_KEY = "pathline.encrypted-recordings";
const DEFAULT_RETENTION_MS = 60 * 60 * 1000;

export interface EncryptedRecordingEntry {
  id: string;
  sessionId: string;
  createdAt: string;
  expiresAt: string;
  sampleRate: number;
  ciphertext: string;
  nonce: string;
  byteLength: number;
}

interface RecordingIndex {
  entries: EncryptedRecordingEntry[];
}

function readIndex(): RecordingIndex {
  try {
    const raw = localStorage.getItem(INDEX_KEY);
    if (!raw) return { entries: [] };
    const parsed = JSON.parse(raw) as RecordingIndex;
    return parsed?.entries ? parsed : { entries: [] };
  } catch {
    return { entries: [] };
  }
}

function writeIndex(index: RecordingIndex): void {
  localStorage.setItem(INDEX_KEY, JSON.stringify(index));
}

export function purgeExpiredRecordings(now = Date.now()): void {
  const index = readIndex();
  const kept = index.entries.filter((entry) => Date.parse(entry.expiresAt) > now);
  writeIndex({ entries: kept });
}

export async function appendEncryptedRecordingChunk(
  sessionId: string,
  pcm: Float32Array,
  sampleRate: number,
  retentionMs = DEFAULT_RETENTION_MS
): Promise<void> {
  purgeExpiredRecordings();
  const sealed = await sealVaultSecret(
    JSON.stringify({ pcm: Array.from(pcm), sampleRate })
  );
  const entry: EncryptedRecordingEntry = {
    id: crypto.randomUUID(),
    sessionId,
    createdAt: new Date().toISOString(),
    expiresAt: new Date(Date.now() + retentionMs).toISOString(),
    sampleRate,
    ciphertext: sealed.ciphertext,
    nonce: sealed.nonce,
    byteLength: pcm.byteLength,
  };
  const index = readIndex();
  index.entries.push(entry);
  writeIndex(index);
}

export async function readEncryptedRecording(
  entry: EncryptedRecordingEntry
): Promise<{ pcm: Float32Array; sampleRate: number } | null> {
  const plaintext = await unsealVaultSecret(entry.ciphertext, entry.nonce);
  if (!plaintext) return null;
  const parsed = JSON.parse(plaintext) as { pcm: number[]; sampleRate: number };
  return { pcm: Float32Array.from(parsed.pcm), sampleRate: parsed.sampleRate };
}

export function deleteRecordingsForSession(sessionId: string): void {
  const index = readIndex();
  writeIndex({ entries: index.entries.filter((e) => e.sessionId !== sessionId) });
}
