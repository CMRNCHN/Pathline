import type { PathDocument } from "./types";
import { scriptDisplayName } from "./storage";

/** Strip trailing `(copy)` / `(copy N)` so duplicates collapse into one family. */
export function workflowFamilyKey(workflow: PathDocument): string {
  const name = scriptDisplayName(workflow).trim();
  const stripped = name.replace(/(\s*\(copy(?:\s+\d+)?\))+$/i, "").trim();
  return stripped || "Untitled";
}

export interface WorkflowFamily {
  key: string;
  latest: PathDocument;
  revisions: PathDocument[];
}

/** Group workflows by family key; newest id last → latest is last in each group. */
export function groupWorkflowFamilies(workflows: PathDocument[]): WorkflowFamily[] {
  const map = new Map<string, PathDocument[]>();
  for (const workflow of workflows) {
    const key = workflowFamilyKey(workflow);
    const list = map.get(key) ?? [];
    list.push(workflow);
    map.set(key, list);
  }
  return [...map.entries()]
    .map(([key, revisions]) => ({
      key,
      revisions,
      latest: revisions[revisions.length - 1],
    }))
    .sort((a, b) => a.key.localeCompare(b.key));
}
