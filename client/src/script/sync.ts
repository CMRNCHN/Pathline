import type { FlowStep, Step, PathDocument } from "./types";
import { newId } from "./storage";

const VAR_REF = /\{\{(\w+)\}\}/g;

function flowActionForRule(step: Step): FlowStep["action"] {
  if (step.rule === "Validate collected outputs") return "validate";
  if (step.rule === "End call") return "end";
  if (step.rule === "Wait for IVR response") return "pass";
  if (step.output.trim() || step.rule === "Capture value after detect") return "extract";
  return "trigger";
}

export function syncInputsFromSteps(steps: Step[]): string[] {
  const names = new Set<string>();
  for (const step of steps) {
    for (const m of step.then.matchAll(VAR_REF)) {
      names.add(m[1]);
    }
  }
  return [...names].sort();
}

export function syncConversationFlowFromRules(
  steps: Step[],
  existing: FlowStep[] = []
): FlowStep[] {
  const byLabel = new Map(
    existing
      .filter((step) => step.triggerLabel)
      .map((step) => [step.triggerLabel!, step])
  );

  return steps
    .filter(
      (step) =>
        step.label.trim() &&
        (step.when.trim() ||
          step.rule === "Wait for IVR response" ||
          step.rule === "End call" ||
          step.rule === "Capture value after detect")
    )
    .map((step) => {
      const prev = byLabel.get(step.label);
      const action = flowActionForRule(step);
      let detect = step.when.trim();
      if (!detect) {
        if (step.rule === "Capture value after detect") detect = "__next_utterance__";
        else if (step.rule === "End call") detect = "__end_now__";
        else detect = `__wait_${step.waitSeconds ?? 0}__`;
      }

      return {
        id: prev?.id ?? newId(),
        detect,
        action,
        triggerLabel: action === "trigger" || action === "extract" ? step.label : undefined,
      };
    });
}

export function withSyncedRules(
  doc: PathDocument,
  steps: Step[]
): Pick<PathDocument, "steps" | "conversationFlow" | "setup"> {
  return {
    steps,
    conversationFlow: syncConversationFlowFromRules(steps, doc.conversationFlow),
    setup: {
      ...doc.setup,
      inputs: syncInputsFromSteps(steps),
    },
  };
}
