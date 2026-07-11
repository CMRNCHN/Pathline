import type { PathDocument } from "../script/types";
import type { LocalCall } from "../types";

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

export interface PersistedRun extends LocalCall {
  variables?: Record<string, string>;
  completedAt?: string;
}

export interface PersistenceSnapshot {
  version: typeof PERSISTENCE_VERSION;
  userId: string;
  activeScriptId: string;
  preferences: AppPreferences;
  customScripts: PathDocument[];
  runConfigs: RunConfig[];
  runHistory: PersistedRun[];
}
