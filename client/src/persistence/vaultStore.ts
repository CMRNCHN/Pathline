import { sealVaultSecret, unsealVaultSecret } from "../crypto";

/** Input Vault entries — sealed secret values on this device. */

export interface InputVaultEntry {
  key: string;
  label: string;
  updatedAt: string;
  ciphertext: string;
  nonce: string;
}

const STORAGE_KEY = "pathline-input-vault";

function readAll(): InputVaultEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as InputVaultEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(entries: InputVaultEntry[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

export function listVaultEntries(): InputVaultEntry[] {
  return readAll().sort((a, b) => a.label.localeCompare(b.label));
}

export function getVaultEntry(key: string): InputVaultEntry | undefined {
  return readAll().find((e) => e.key === key);
}

export async function upsertVaultEntry(
  key: string,
  label: string,
  plaintext: string
): Promise<InputVaultEntry> {
  const sealed = await sealVaultSecret(plaintext);
  const entry: InputVaultEntry = {
    key,
    label,
    updatedAt: new Date().toISOString(),
    ciphertext: sealed.ciphertext,
    nonce: sealed.nonce,
  };
  const all = readAll().filter((e) => e.key !== key);
  all.push(entry);
  writeAll(all);
  return entry;
}

export function deleteVaultEntry(key: string): void {
  writeAll(readAll().filter((e) => e.key !== key));
}

export async function revealVaultSecret(key: string): Promise<string | null> {
  const entry = getVaultEntry(key);
  if (!entry) return null;
  return unsealVaultSecret(entry.ciphertext, entry.nonce);
}

export function clearVaultEntries(): void {
  localStorage.removeItem(STORAGE_KEY);
}
