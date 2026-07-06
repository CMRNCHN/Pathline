import type { EditorSection } from "./types";

export function nextSectionAfterBasics(): EditorSection {
  return "secrets";
}

export function initialSectionForScript(setupComplete: boolean): EditorSection {
  return setupComplete ? "conversation" : "basics";
}

export function shouldShowBasicsSection(
  section: EditorSection,
  setupComplete: boolean
): boolean {
  return section === "basics" || !setupComplete;
}
