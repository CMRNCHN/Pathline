import type { ScriptDocument } from "./types";
import { newConversationStep } from "./compile";

export const CUSTOM_SCRIPTS_KEY = "promptpath-custom-scripts";
export const ACTIVE_SCRIPT_KEY = "promptpath-active-script";

export const BUNDLED_SCRIPT_FILES = ["cc-balance.json", "utility-account.json"];

export function newId(): string {
  return crypto.randomUUID();
}

export function newScript(partial?: Partial<ScriptDocument>): ScriptDocument {
  return {
    id: newId(),
    name: "New script",
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

export const DEFAULT_TAGS = ["Credit Card", "Utility", "Insurance", "Bank", "Government"];

export function scriptMatchesTag(script: ScriptDocument, tag: string | null): boolean {
  if (!tag) return true;
  return script.tags.some((t) => t.toLowerCase() === tag.toLowerCase());
}

export function inferTags(script: ScriptDocument): string[] {
  if (script.tags.length) return script.tags;
  const name = script.name.toLowerCase();
  if (name.includes("credit") || name.includes("card")) return ["Credit Card"];
  if (name.includes("utility")) return ["Utility"];
  return ["Credit Card"];
}
