import type { PathDocument } from "./types";
import { isPlaceholderRule } from "./ruleIntent";

export type PathReadiness = "ready" | "draft" | "needs-setup";

export const READINESS_LABEL: Record<PathReadiness, string> = {
  ready: "Ready",
  draft: "Draft",
  "needs-setup": "Needs setup",
};

/** Is this Workflow runnable as-is: has a phone number and at least one real Step. */
export function getPathReadiness(path: PathDocument): PathReadiness {
  const name = path.setup.name.trim();
  const target = path.setup.target.trim();
  const realSteps = path.steps.filter((r) => !isPlaceholderRule(r));

  if (!name && !target && realSteps.length === 0) return "draft";
  if (!target || realSteps.length === 0) return "needs-setup";
  return "ready";
}

export function getWorkflowSetupIssues(workflow: PathDocument): string[] {
  const issues: string[] = [];
  if (!workflow.setup.target.trim()) issues.push("Add a phone number to call");
  if (!workflow.steps.some((step) => !isPlaceholderRule(step))) issues.push("Add at least one Step");
  return issues;
}
