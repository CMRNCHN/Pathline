import type { KnownScript, StatusRule } from "./types";

export const CUSTOM_SCRIPTS_KEY = "promptpath-custom-scripts";
export const ACTIVE_SCRIPT_KEY = "promptpath-active-script";

export const BUNDLED_SCRIPT_FILES = ["cc-balance.json", "utility-account.json"];

export function newId(): string {
  return crypto.randomUUID();
}

export function newSendRule(): StatusRule {
  return { trigger: "", response: "", key: "", status: "", dtmf: "" };
}

export function newCaptureRule(): StatusRule {
  return { trigger: "", response: "", key: "", status: "", endCall: true };
}

export function newScript(partial?: Partial<KnownScript>): KnownScript {
  return {
    id: newId(),
    name: "New script",
    description: "",
    target: "",
    secrets: [],
    rules: [newSendRule()],
    ...partial,
  };
}

export function isSendRule(rule: StatusRule): boolean {
  return Boolean(rule.trigger?.trim() || rule.dtmf?.trim());
}

export function loadCustomScripts(): KnownScript[] {
  try {
    const raw = localStorage.getItem(CUSTOM_SCRIPTS_KEY);
    if (raw) return JSON.parse(raw) as KnownScript[];
  } catch {
    /* ignore */
  }
  return [];
}

export function saveCustomScripts(scripts: KnownScript[]): void {
  localStorage.setItem(CUSTOM_SCRIPTS_KEY, JSON.stringify(scripts));
}

export function loadActiveScriptId(): string {
  return localStorage.getItem(ACTIVE_SCRIPT_KEY) ?? "";
}

export function saveActiveScriptId(id: string): void {
  localStorage.setItem(ACTIVE_SCRIPT_KEY, id);
}

export function deriveSecretKeys(script: KnownScript): string[] {
  const keys = new Set(script.secrets ?? []);
  for (const rule of script.rules) {
    if (rule.dtmf) {
      for (const match of rule.dtmf.matchAll(/\{(\w+)\}/g)) {
        keys.add(match[1]);
      }
    }
  }
  return [...keys].sort();
}

export function syncSecrets(script: KnownScript): KnownScript {
  return { ...script, secrets: deriveSecretKeys(script) };
}

export function duplicateScript(source: KnownScript, name?: string): KnownScript {
  return syncSecrets({
    ...structuredClone(source),
    id: newId(),
    name: name ?? `${source.name} (copy)`,
  });
}
