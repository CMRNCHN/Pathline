import { normalizeScript } from "../script/compile";
import type { PathDocument } from "../script/types";
import {
  ACTIVE_SCRIPT_KEY,
  CUSTOM_SCRIPTS_KEY,
} from "../script/storage";
import type { LocalSession } from "../types";
import {
  appendRunHistory,
  clearAllStores,
  readActiveScriptId,
  readAllScripts,
  readPreferences,
  readRunConfig,
  readRunHistory,
  readAllRunConfigs,
  readUserId,
  readVersion,
  writeActiveScriptId,
  writeAllScripts,
  writePreferences,
  writeRunConfig,
  writeUserId,
  writeVersion,
} from "./db";
import type { AppPreferences, PersistedRun, RunConfig } from "./types";
import { PERSISTENCE_VERSION as VERSION } from "./types";

export type { AppPreferences, PersistedRun, RunConfig };

const LEGACY_AUTO_LISTEN_KEY = "pp-auto-listen";

function generateUserId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function readLegacyScripts(): PathDocument[] {
  try {
    const raw = localStorage.getItem(CUSTOM_SCRIPTS_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as PathDocument[];
  } catch {
    return [];
  }
}

function readLegacyActiveId(): string {
  return localStorage.getItem(ACTIVE_SCRIPT_KEY) ?? "";
}

function readLegacyAutoListen(): boolean {
  return localStorage.getItem(LEGACY_AUTO_LISTEN_KEY) === "1";
}

function clearLegacyLocalStorage(): void {
  localStorage.removeItem(CUSTOM_SCRIPTS_KEY);
  localStorage.removeItem(ACTIVE_SCRIPT_KEY);
  localStorage.removeItem(LEGACY_AUTO_LISTEN_KEY);
}

async function migrateLegacyLocalStorageIfNeeded(): Promise<void> {
  const version = await readVersion();
  if (version >= VERSION) return;

  const legacyScripts = readLegacyScripts();
  const existing = await readAllScripts();
  const scripts =
    existing.length > 0
      ? existing
      : legacyScripts.map((script) => normalizeScript(script));

  if (scripts.length > 0) {
    await writeAllScripts(scripts);
  }

  const activeId = (await readActiveScriptId()) || readLegacyActiveId();
  if (activeId) {
    await writeActiveScriptId(activeId);
  }

  const prefs = await readPreferences();
  if (!prefs.autoListen && readLegacyAutoListen()) {
    await writePreferences({ autoListen: true });
  }

  if (!(await readUserId())) {
    await writeUserId(generateUserId());
  }

  await writeVersion(VERSION);
  clearLegacyLocalStorage();
}

export async function initPersistence(): Promise<{
  customScripts: PathDocument[];
  activeScriptId: string;
  preferences: AppPreferences;
  userId: string;
}> {
  await migrateLegacyLocalStorageIfNeeded();

  const customScripts = (await readAllScripts()).map((script) => normalizeScript(script));
  const activeScriptId = await readActiveScriptId();
  const preferences = await readPreferences();
  const userId = (await readUserId()) ?? generateUserId();

  if (!(await readUserId())) {
    await writeUserId(userId);
  }

  if ((await readVersion()) < VERSION) {
    await writeVersion(VERSION);
  }

  return { customScripts, activeScriptId, preferences, userId };
}

export async function saveCustomScripts(scripts: PathDocument[]): Promise<void> {
  await writeAllScripts(scripts);
}

export async function saveActiveScriptId(id: string): Promise<void> {
  await writeActiveScriptId(id);
}

export async function savePreferences(preferences: AppPreferences): Promise<void> {
  await writePreferences(preferences);
}

export { readPreferences } from "./db";

export async function getOrCreateUserId(): Promise<string> {
  const existing = await readUserId();
  if (existing) return existing;
  const userId = generateUserId();
  await writeUserId(userId);
  return userId;
}

export async function loadRunConfig(scriptId: string): Promise<RunConfig | undefined> {
  return readRunConfig(scriptId);
}

export async function saveRunConfig(
  scriptId: string,
  target: string,
  variables: Record<string, string>
): Promise<void> {
  await writeRunConfig({
    scriptId,
    target,
    variables,
    updatedAt: new Date().toISOString(),
  });
}

export async function recordCompletedRun(
  session: LocalSession,
  variables: Record<string, string>
): Promise<void> {
  const run: PersistedRun = {
    ...session,
    variables,
    completedAt: new Date().toISOString(),
  };
  await appendRunHistory(run);
}

export async function listRunHistory(): Promise<PersistedRun[]> {
  return readRunHistory();
}

export async function clearAllPersistence(): Promise<void> {
  await clearAllStores();
  clearLegacyLocalStorage();
}

export async function persistenceStats(): Promise<{
  scriptCount: number;
  runConfigCount: number;
  runHistoryCount: number;
  storage: "IndexedDB";
}> {
  const scripts = await readAllScripts();
  const configs = await readAllRunConfigs();
  const history = await readRunHistory();
  return {
    scriptCount: scripts.length,
    runConfigCount: configs.length,
    runHistoryCount: history.length,
    storage: "IndexedDB",
  };
}
