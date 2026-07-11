import type { PathDocument } from "./types";
import { isPlaceholderRule } from "./ruleIntent";

export type PathReadiness = "ready" | "draft" | "needs-setup";

export const READINESS_LABEL: Record<PathReadiness, string> = {
  ready: "Ready",
  draft: "Draft",
  "needs-setup": "Needs setup",
};

/** Is this Path runnable as-is: has a name, a target, and at least one real Step. */
export function getPathReadiness(path: PathDocument): PathReadiness {
  const name = path.setup.name.trim();
  const target = path.setup.target.trim();
  const realSteps = path.steps.filter((r) => !isPlaceholderRule(r));

  if (!name && !target && realSteps.length === 0) return "draft";
  if (!target || realSteps.length === 0) return "needs-setup";
  return "ready";
}
