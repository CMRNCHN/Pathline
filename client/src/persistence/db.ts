import type { ScriptDocument } from "../script/types";
import type { AppPreferences, PersistedRun, PERSISTENCE_VERSION, RunConfig } from "./types";

const DB_NAME = "promptpath";
const DB_VERSION = 1;

const STORE_KV = "kv";
const STORE_SCRIPTS = "scripts";
const STORE_RUN_CONFIGS = "run_configs";
const STORE_RUN_HISTORY = "run_history";

type KvKey = "version" | "userId" | "activeScriptId" | "preferences";

let dbPromise: Promise<IDBDatabase> | null = null;

function openDb(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise;

  dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_KV)) db.createObjectStore(STORE_KV);
      if (!db.objectStoreNames.contains(STORE_SCRIPTS)) {
        db.createObjectStore(STORE_SCRIPTS, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(STORE_RUN_CONFIGS)) {
        db.createObjectStore(STORE_RUN_CONFIGS, { keyPath: "scriptId" });
      }
      if (!db.objectStoreNames.contains(STORE_RUN_HISTORY)) {
        db.createObjectStore(STORE_RUN_HISTORY, { keyPath: "sessionId" });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("IndexedDB open failed"));
  });

  return dbPromise;
}

function tx<T>(
  storeName: string,
  mode: IDBTransactionMode,
  run: (store: IDBObjectStore) => IDBRequest<T> | void
): Promise<T | void> {
  return openDb().then(
    (db) =>
      new Promise((resolve, reject) => {
        const transaction = db.transaction(storeName, mode);
        const store = transaction.objectStore(storeName);
        const request = run(store);
        transaction.oncomplete = () => resolve(request ? request.result : undefined);
        transaction.onerror = () => reject(transaction.error ?? new Error("IndexedDB transaction failed"));
      })
  );
}

function getAll<T>(storeName: string): Promise<T[]> {
  return openDb().then(
    (db) =>
      new Promise((resolve, reject) => {
        const transaction = db.transaction(storeName, "readonly");
        const store = transaction.objectStore(storeName);
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result as T[]);
        request.onerror = () => reject(request.error ?? new Error("IndexedDB read failed"));
      })
  );
}

async function getKv<T>(key: KvKey): Promise<T | undefined> {
  const value = await tx<T>(STORE_KV, "readonly", (store) => store.get(key));
  return value === undefined ? undefined : (value as T);
}

async function setKv(key: KvKey, value: unknown): Promise<void> {
  await tx(STORE_KV, "readwrite", (store) => store.put(value, key));
}

export async function readVersion(): Promise<number> {
  return (await getKv<number>("version")) ?? 0;
}

export async function writeVersion(version: typeof PERSISTENCE_VERSION): Promise<void> {
  await setKv("version", version);
}

export async function readUserId(): Promise<string | undefined> {
  return getKv<string>("userId");
}

export async function writeUserId(userId: string): Promise<void> {
  await setKv("userId", userId);
}

export async function readActiveScriptId(): Promise<string> {
  return (await getKv<string>("activeScriptId")) ?? "";
}

export async function writeActiveScriptId(id: string): Promise<void> {
  await setKv("activeScriptId", id);
}

export async function readPreferences(): Promise<AppPreferences> {
  return (await getKv<AppPreferences>("preferences")) ?? { autoListen: false };
}

export async function writePreferences(preferences: AppPreferences): Promise<void> {
  await setKv("preferences", preferences);
}

export async function readAllScripts(): Promise<ScriptDocument[]> {
  return getAll<ScriptDocument>(STORE_SCRIPTS);
}

export async function writeAllScripts(scripts: ScriptDocument[]): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(STORE_SCRIPTS, "readwrite");
    const store = transaction.objectStore(STORE_SCRIPTS);
    store.clear();
    for (const script of scripts) {
      store.put(script);
    }
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error ?? new Error("Failed to save scripts"));
  });
}

export async function readAllRunConfigs(): Promise<RunConfig[]> {
  return getAll<RunConfig>(STORE_RUN_CONFIGS);
}

export async function readRunConfig(scriptId: string): Promise<RunConfig | undefined> {
  const value = await tx<RunConfig>(STORE_RUN_CONFIGS, "readonly", (store) => store.get(scriptId));
  return value === undefined ? undefined : (value as RunConfig);
}

export async function writeRunConfig(config: RunConfig): Promise<void> {
  await tx(STORE_RUN_CONFIGS, "readwrite", (store) => store.put(config));
}

export async function readRunHistory(): Promise<PersistedRun[]> {
  const runs = await getAll<PersistedRun>(STORE_RUN_HISTORY);
  return runs.sort((a, b) => b.startedAt.localeCompare(a.startedAt));
}

export async function appendRunHistory(run: PersistedRun): Promise<void> {
  await tx(STORE_RUN_HISTORY, "readwrite", (store) => store.put(run));
}

export async function clearAllStores(): Promise<void> {
  const db = await openDb();
  const names = [STORE_KV, STORE_SCRIPTS, STORE_RUN_CONFIGS, STORE_RUN_HISTORY];
  await Promise.all(
    names.map(
      (name) =>
        new Promise<void>((resolve, reject) => {
          const transaction = db.transaction(name, "readwrite");
          transaction.objectStore(name).clear();
          transaction.oncomplete = () => resolve();
          transaction.onerror = () => reject(transaction.error);
        })
    )
  );
}
