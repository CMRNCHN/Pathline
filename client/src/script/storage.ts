import type { ScriptDocument } from "./types";
import { SCRIPT_VERSION } from "./types";
import { newIvrRule } from "./compile";
import { withSyncedRules } from "./sync";

export const CUSTOM_SCRIPTS_KEY = "promptpath-custom-scripts";
export const ACTIVE_SCRIPT_KEY = "promptpath-active-script";

export const BUNDLED_SCRIPT_FILES: string[] = ["template.json"];

export function newId(): string {
  return crypto.randomUUID();
}

export function newScript(partial?: Partial<ScriptDocument>): ScriptDocument {
  const base: ScriptDocument = {
    id: newId(),
    version: SCRIPT_VERSION,
    setup: {
      name: "",
      description: "",
      target: "",
      timeoutMs: 30000,
      speechPreferences: { autoListen: false },
      runtimeVariables: [],
    },
    ivrRules: [newIvrRule(1)],
    conversationFlow: [],
    ...partial,
  };
  return { ...base, ...withSyncedRules(base, base.ivrRules) };
}

export function loadCustomScripts(): ScriptDocument[] {
  try {
    const raw = localStorage.getItem(CUSTOM_SCRIPTS_KEY);
    if (raw) return JSON.parse(raw) as ScriptDocument[];
  } catch {
    /* ignore */
  }
  return [];
}

export function saveCustomScripts(scripts: ScriptDocument[]): void {
  localStorage.setItem(CUSTOM_SCRIPTS_KEY, JSON.stringify(scripts));
}

export function loadActiveScriptId(): string {
  return localStorage.getItem(ACTIVE_SCRIPT_KEY) ?? "";
}

export function saveActiveScriptId(id: string): void {
  localStorage.setItem(ACTIVE_SCRIPT_KEY, id);
}

export function duplicateScript(source: ScriptDocument, name?: string): ScriptDocument {
  return {
    ...structuredClone(source),
    id: newId(),
    setup: {
      ...source.setup,
      name: name ?? `${source.setup.name} (copy)`,
    },
  };
}

export function scriptDisplayName(script: ScriptDocument): string {
  return script.setup.name || "Untitled";
}
