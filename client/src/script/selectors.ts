import type { PathDocument } from "./types";

export function mergeScripts(
  bundledScripts: PathDocument[],
  customScripts: PathDocument[]
): PathDocument[] {
  return bundledScripts.concat(customScripts);
}

export function getActiveScript(
  bundledScripts: PathDocument[],
  customScripts: PathDocument[],
  activeId: string
): PathDocument | undefined {
  return bundledScripts.find((s) => s.id === activeId)
    ?? customScripts.find((s) => s.id === activeId);
}

export function isBundledScript(bundledScripts: PathDocument[], id: string): boolean {
  return bundledScripts.some((s) => s.id === id);
}
