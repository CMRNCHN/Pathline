import type { ScriptDocument } from "./types";

export function mergeScripts(
  bundledScripts: ScriptDocument[],
  customScripts: ScriptDocument[]
): ScriptDocument[] {
  return bundledScripts.concat(customScripts);
}

export function getActiveScript(
  bundledScripts: ScriptDocument[],
  customScripts: ScriptDocument[],
  activeId: string
): ScriptDocument | undefined {
  return bundledScripts.find((s) => s.id === activeId)
    ?? customScripts.find((s) => s.id === activeId);
}

export function isBundledScript(bundledScripts: ScriptDocument[], id: string): boolean {
  return bundledScripts.some((s) => s.id === id);
}
