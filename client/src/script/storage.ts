import type { ScriptDocument } from "./types";
import { newConversationStep } from "./compile";

export const CUSTOM_SCRIPTS_KEY = "promptpath-custom-scripts";
export const ACTIVE_SCRIPT_KEY = "promptpath-active-script";

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
