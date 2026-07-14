import type { PathDocument } from "./types";
import { SCRIPT_VERSION } from "./types";
import { withSyncedRules } from "./sync";

export const CUSTOM_SCRIPTS_KEY = "pathline-custom-scripts";
export const ACTIVE_SCRIPT_KEY = "pathline-active-script";
const LEGACY_CUSTOM_SCRIPTS_KEY = "promptpath-custom-scripts"; // legacy PromptPath
const LEGACY_ACTIVE_SCRIPT_KEY = "promptpath-active-script"; // legacy PromptPath

function readLocalStorageItem(key: string, legacyKey: string): string | null {
  return localStorage.getItem(key) ?? localStorage.getItem(legacyKey);
}

function migrateLocalStorageKey(key: string, legacyKey: string, value: string): void {
  localStorage.setItem(key, value);
  localStorage.removeItem(legacyKey);
}

export const BUNDLED_SCRIPT_FILES: string[] = ["template.json"];

export function newId(): string {
  return crypto.randomUUID();
}

export function newScript(partial?: Partial<PathDocument>): PathDocument {
  const base: PathDocument = {
    id: newId(),
    version: SCRIPT_VERSION,
    setup: {
      name: "",
      description: "",
      target: "",
      timeoutMs: 30000,
      speechPreferences: { autoListen: false },
      inputs: [],
    },
    steps: [],
    conversationFlow: [],
    ...partial,
  };
  return { ...base, ...withSyncedRules(base, base.steps) };
}

export function loadCustomScripts(): PathDocument[] {
  try {
    const raw = readLocalStorageItem(CUSTOM_SCRIPTS_KEY, LEGACY_CUSTOM_SCRIPTS_KEY);
    if (raw) {
      if (!localStorage.getItem(CUSTOM_SCRIPTS_KEY) && localStorage.getItem(LEGACY_CUSTOM_SCRIPTS_KEY)) {
        migrateLocalStorageKey(CUSTOM_SCRIPTS_KEY, LEGACY_CUSTOM_SCRIPTS_KEY, raw);
      }
      return JSON.parse(raw) as PathDocument[];
    }
  } catch {
    /* ignore */
  }
  return [];
}

export function saveCustomScripts(scripts: PathDocument[]): void {
  localStorage.setItem(CUSTOM_SCRIPTS_KEY, JSON.stringify(scripts));
}

export function loadActiveScriptId(): string {
  const value = readLocalStorageItem(ACTIVE_SCRIPT_KEY, LEGACY_ACTIVE_SCRIPT_KEY);
  if (value && !localStorage.getItem(ACTIVE_SCRIPT_KEY) && localStorage.getItem(LEGACY_ACTIVE_SCRIPT_KEY)) {
    migrateLocalStorageKey(ACTIVE_SCRIPT_KEY, LEGACY_ACTIVE_SCRIPT_KEY, value);
  }
  return value ?? "";
}

export function saveActiveScriptId(id: string): void {
  localStorage.setItem(ACTIVE_SCRIPT_KEY, id);
}

export function duplicateScript(source: PathDocument, name?: string): PathDocument {
  return {
    ...structuredClone(source),
    id: newId(),
    setup: {
      ...source.setup,
      name: name ?? `${source.setup.name} (copy)`,
    },
  };
}

export function scriptDisplayName(script: PathDocument): string {
  return script.setup.name || "Untitled";
}
