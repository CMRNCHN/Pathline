import type { ScriptDocument } from "./types";
import { newConversationStep } from "./compile";

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

export const BUNDLED_SCRIPT_FILES: string[] = [];

export function newId(): string {
  return crypto.randomUUID();
}

export function newScript(partial?: Partial<ScriptDocument>): ScriptDocument {
  return {
    id: newId(),
    name: "",
    description: "",
    target: "",
    timeoutMs: 30000,
    tags: [],
    setupComplete: false,
    secrets: [],
    conversation: [newConversationStep("send_keys")],
    results: [],
    ...partial,
  };
}

export function loadCustomScripts(): ScriptDocument[] {
  try {
    const raw = readLocalStorageItem(CUSTOM_SCRIPTS_KEY, LEGACY_CUSTOM_SCRIPTS_KEY);
    if (raw) {
      if (!localStorage.getItem(CUSTOM_SCRIPTS_KEY) && localStorage.getItem(LEGACY_CUSTOM_SCRIPTS_KEY)) {
        migrateLocalStorageKey(CUSTOM_SCRIPTS_KEY, LEGACY_CUSTOM_SCRIPTS_KEY, raw);
      }
      return JSON.parse(raw) as ScriptDocument[];
    }
  } catch {
    /* ignore */
  }
  return [];
}

export function saveCustomScripts(scripts: ScriptDocument[]): void {
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

export function duplicateScript(source: ScriptDocument, name?: string): ScriptDocument {
  return {
    ...structuredClone(source),
    id: newId(),
    name: name ?? `${source.name} (copy)`,
    setupComplete: source.setupComplete,
  };
}

export const DEFAULT_TAGS = ["Utility", "Insurance", "Bank", "Government", "Other"];

export function scriptMatchesTag(script: ScriptDocument, tag: string | null): boolean {
  if (!tag) return true;
  return script.tags.some((t) => t.toLowerCase() === tag.toLowerCase());
}

export function inferTags(_script: ScriptDocument): string[] {
  return [];
}
