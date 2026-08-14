import type { Account } from "../persistence/accountsStore";
import { accountInputNames } from "../persistence/accountsStore";
import type { PathDocument } from "./types";
import { isPlaceholderRule, isStepValid } from "./ruleIntent";

export type PathReadiness = "ready" | "draft" | "needs-setup";

export const READINESS_LABEL: Record<PathReadiness, string> = {
  ready: "Ready",
  draft: "Draft",
  "needs-setup": "Needs setup",
};

const INPUT_REF = /\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}/g;

function referencedInputs(workflow: PathDocument): string[] {
  const names = new Set<string>();
  for (const step of workflow.steps) {
    for (const match of step.then.matchAll(INPUT_REF)) names.add(match[1]);
  }
  return [...names];
}

/** Paths whose required setup.inputs are satisfied by the account (plain or vault-bound). */
export function pathsAvailableForAccount(
  account: Account,
  paths: PathDocument[]
): PathDocument[] {
  const available = new Set(accountInputNames(account));
  return paths.filter((path) => {
    const required = path.setup.inputs.filter(Boolean);
    if (required.length === 0) return getPathReadiness(path) === "ready";
    return required.every((name) => available.has(name));
  });
}

/** A Ready Workflow has complete setup, valid executable Steps, Inputs, and an end path. */
export function getPathReadiness(path: PathDocument): PathReadiness {
  const hasContent =
    Boolean(path.setup.name.trim()) ||
    Boolean(path.setup.target.trim()) ||
    path.steps.some((step) => !isPlaceholderRule(step));

  if (!hasContent) return "draft";
  if (getWorkflowSetupIssues(path).length > 0) return "needs-setup";
  return "ready";
}

export function getWorkflowSetupIssues(workflow: PathDocument): string[] {
  const issues: string[] = [];
  const realSteps = workflow.steps.filter((step) => !isPlaceholderRule(step));

  if (!workflow.setup.target.trim()) issues.push("Add a phone number to call");
  if (realSteps.length === 0) {
    issues.push("Add at least one Step");
    return issues;
  }

  realSteps.forEach((step, index) => {
    if (!isStepValid(step)) issues.push(`Fix Step ${index + 1} (${step.label || "untitled"})`);
  });

  const configuredInputs = new Set(workflow.setup.inputs);
  const missingInputs = referencedInputs(workflow).filter((name) => !configuredInputs.has(name));
  if (missingInputs.length > 0) {
    issues.push(`Synchronize missing Inputs: ${missingInputs.join(", ")}`);
  }

  if (!realSteps.some((step) => step.rule === "End call" && isStepValid(step))) {
    issues.push("Add an End call Step");
  }

  return issues;
}
