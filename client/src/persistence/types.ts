import type { ScriptDocument } from "../script/types";
import type { LocalSession } from "../types";

export const PERSISTENCE_VERSION = 1 as const;

export interface AppPreferences {
  autoListen: boolean;
}

export interface RunConfig {
  scriptId: string;
  target: string;
  variables: Record<string, string>;
  updatedAt: string;
}

export interface PersistedRun extends LocalSession {
  variables?: Record<string, string>;
  completedAt?: string;
}

export interface PersistenceSnapshot {
  version: typeof PERSISTENCE_VERSION;
  userId: string;
  activeScriptId: string;
  preferences: AppPreferences;
  customScripts: ScriptDocument[];
  runConfigs: RunConfig[];
  runHistory: PersistedRun[];
}
