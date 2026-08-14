import type { CallEvent } from "../callstate";

export type RunOutcome = "completed" | "failed" | "abandoned";
export type UploadState = "pending" | "uploaded" | "failed" | "not-requested";

/** A single past Run of a Workflow — stored on-device only. */
export interface RunRecord {
  runId: string;
  pathId: string;
  pathName: string;
  outcome: RunOutcome;
  startedAt: string;
  completedAt: string;
  captured: Record<string, string>;
  ledgerEvents?: CallEvent[];
  ledgerHead?: string;
  uploadState?: UploadState;
  uploadError?: string;
  pendingUpload?: {
    ciphertext: string;
    nonce: string;
    idempotencyKey: string;
  };
}

const HISTORY_KEY = "pathline-run-history";
const MAX_RECORDS = 100;

const listeners = new Set<() => void>();
let cache: RunRecord[] = [];
let initialized = false;
let initializePromise: Promise<void> | null = null;

interface SecureHistoryBridge {
  load(): Promise<string>;
  save(json: string): Promise<void>;
  clear(): Promise<void>;
}

declare global {
  interface Window {
    __pathlineSecureHistory?: SecureHistoryBridge;
  }
}

function emit(): void {
  for (const listener of listeners) listener();
}

export function subscribeRunHistory(listener: () => void): () => void {
  listeners.add(listener);
  void initializeRunHistory();
  return () => listeners.delete(listener);
}

export function loadRunHistory(): RunRecord[] {
  void initializeRunHistory();
  return [...cache];
}

function readLegacyHistory(): RunRecord[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]") as RunRecord[];
  } catch {
    return [];
  }
}

export function initializeRunHistory(): Promise<void> {
  if (initialized) return Promise.resolve();
  if (initializePromise) return initializePromise;
  initializePromise = (async () => {
    const secure = window.__pathlineSecureHistory;
    if (secure) {
      let stored: RunRecord[] = [];
      try {
        const raw = await secure.load();
        stored = JSON.parse(raw) as RunRecord[];
        if (!Array.isArray(stored)) stored = [];
      } catch {
        stored = [];
      }
      const legacy = readLegacyHistory();
      cache = stored.length > 0 ? stored : legacy;
      if (legacy.length > 0 && stored.length === 0) await secure.save(JSON.stringify(cache));
      localStorage.removeItem(HISTORY_KEY);
    } else {
      // Browser authoring/manual fallback retains the legacy store. Production
      // automated Runs require the native secure bridge and fail closed below.
      cache = readLegacyHistory();
    }
    initialized = true;
    emit();
  })();
  return initializePromise;
}

async function save(records: RunRecord[]): Promise<void> {
  await initializeRunHistory();
  cache = records.slice(0, MAX_RECORDS);
  const secure = window.__pathlineSecureHistory;
  if (secure) {
    await secure.save(JSON.stringify(cache));
  } else {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(cache));
  }
  emit();
}

export async function recordRun(record: RunRecord): Promise<void> {
  await initializeRunHistory();
  const existing = loadRunHistory().filter((r) => r.runId !== record.runId);
  await save([record, ...existing]);
}

export async function updateRunUpload(
  runId: string,
  uploadState: UploadState,
  uploadError?: string
): Promise<void> {
  await initializeRunHistory();
  await save(
    cache.map((record) =>
      record.runId === runId
        ? {
            ...record,
            uploadState,
            uploadError,
            pendingUpload: uploadState === "uploaded" ? undefined : record.pendingUpload,
          }
        : record
    )
  );
}

export async function deleteRun(runId: string): Promise<void> {
  await initializeRunHistory();
  await save(cache.filter((r) => r.runId !== runId));
}

export async function clearRunHistory(): Promise<void> {
  await initializeRunHistory();
  cache = [];
  if (window.__pathlineSecureHistory) await window.__pathlineSecureHistory.clear();
  localStorage.removeItem(HISTORY_KEY);
  emit();
}
