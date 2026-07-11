import type { PathDocument } from "./types";
import { SCRIPT_VERSION } from "./types";
import { withSyncedRules } from "./sync";

export const CUSTOM_SCRIPTS_KEY = "promptpath-custom-scripts";
export const ACTIVE_SCRIPT_KEY = "promptpath-active-script";

export const BUNDLED_SCRIPT_FILES: string[] = ["template.json", "lab-account-status.json"];

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
      localPath: "",
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
    const raw = localStorage.getItem(CUSTOM_SCRIPTS_KEY);
    if (raw) return JSON.parse(raw) as PathDocument[];
  } catch {
    /* ignore */
  }
  return [];
}

export function saveCustomScripts(scripts: PathDocument[]): void {
  localStorage.setItem(CUSTOM_SCRIPTS_KEY, JSON.stringify(scripts));
}

export function loadActiveScriptId(): string {
  return localStorage.getItem(ACTIVE_SCRIPT_KEY) ?? "";
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
