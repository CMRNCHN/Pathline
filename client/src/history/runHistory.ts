export type RunOutcome = "completed" | "failed" | "abandoned";

/** A single past Run of a Path — stored on-device only. */
export interface RunRecord {
  runId: string;
  pathId: string;
  pathName: string;
  outcome: RunOutcome;
  startedAt: string;
  completedAt: string;
  captured: Record<string, string>;
}

const HISTORY_KEY = "pathline-run-history";
const MAX_RECORDS = 100;

const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

export function subscribeRunHistory(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function loadRunHistory(): RunRecord[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (raw) return JSON.parse(raw) as RunRecord[];
  } catch {
    /* ignore */
  }
  return [];
}

function save(records: RunRecord[]): void {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(records.slice(0, MAX_RECORDS)));
  emit();
}

export function recordRun(record: RunRecord): void {
  const existing = loadRunHistory().filter((r) => r.runId !== record.runId);
  save([record, ...existing]);
}

export function deleteRun(runId: string): void {
  save(loadRunHistory().filter((r) => r.runId !== runId));
}

export function clearRunHistory(): void {
  save([]);
}
