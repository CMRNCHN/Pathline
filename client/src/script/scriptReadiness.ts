import type { ScriptDocument } from "./types";

export type ScriptReadiness = "ready" | "draft" | "needs-setup";

const VAR_REF = /\{\{(\w+)\}\}/g;

function referencedVariables(script: ScriptDocument): string[] {
  const names = new Set<string>();
  for (const rule of script.ivrRules) {
    for (const match of rule.response.matchAll(VAR_REF)) {
      names.add(match[1]);
    }
  }
  return [...names];
}

/** Whether a template is runnable as-is (target, steps, and run values declared). */
export function getScriptReadiness(script: ScriptDocument): ScriptReadiness {
  const name = script.setup.name.trim();
  const target = script.setup.target.trim();
  const steps = script.ivrRules.length;

  if (!name && !target && steps === 0) return "draft";

  const declared = new Set(script.setup.runtimeVariables.filter(Boolean));
  const missingVars = referencedVariables(script).filter((v) => !declared.has(v));

  const actionableSteps = script.ivrRules.filter((r) => r.rule !== "End call");
  const incompleteStep = actionableSteps.some(
    (r) => !r.label.trim() || (r.rule !== "End call" && !r.trigger.trim() && r.rule.includes("detect"))
  );

  if (!target || steps === 0 || missingVars.length > 0 || incompleteStep) {
    return "needs-setup";
  }

  return "ready";
}

export const READINESS_LABEL: Record<ScriptReadiness, string> = {
  ready: "Ready",
  draft: "Draft",
  "needs-setup": "Needs setup",
};
