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

export function filterScripts(
  scripts: ScriptDocument[],
  tag: string | null
): ScriptDocument[] {
  if (!tag) return scripts;
  const needle = tag.toLowerCase();
  return scripts.filter((s) => s.tags.some((t) => t.toLowerCase() === needle));
}

export function deriveTags(scripts: ScriptDocument[]): string[] {
  const tags = new Set<string>();
  for (const script of scripts) {
    for (const tag of script.tags) tags.add(tag);
  }
  return [...tags].sort();
}
