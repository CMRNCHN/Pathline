import type { FlowStep, IvrRule, ScriptDocument } from "./types";
import { newId } from "./storage";

const VAR_REF = /\{\{(\w+)\}\}/g;

function flowActionForRule(rule: IvrRule): FlowStep["action"] {
  if (rule.rule === "Validate collected outputs") return "validate";
  if (rule.rule === "End call") return "end";
  if (rule.rule === "Wait for IVR response") return "pass";
  if (rule.output.trim() || rule.rule === "Capture value after detect") return "extract";
  return "trigger";
}

export function syncRuntimeVariablesFromRules(rules: IvrRule[]): string[] {
  const names = new Set<string>();
  for (const rule of rules) {
    for (const m of rule.response.matchAll(VAR_REF)) {
      names.add(m[1]);
    }
  }
  return [...names].sort();
}

export function syncConversationFlowFromRules(
  rules: IvrRule[],
  existing: FlowStep[] = []
): FlowStep[] {
  const byLabel = new Map(
    existing
      .filter((step) => step.triggerLabel)
      .map((step) => [step.triggerLabel!, step])
  );

  return rules
    .filter(
      (rule) =>
        rule.label.trim() &&
        (rule.trigger.trim() || rule.rule === "Wait for IVR response" || rule.rule === "End call")
    )
    .map((rule) => {
      const prev = byLabel.get(rule.label);
      const action = flowActionForRule(rule);
      const detect =
        rule.trigger.trim() ||
        (rule.rule === "End call" ? "goodbye|thank you" : `__wait_${rule.waitSeconds ?? 0}__`);

      return {
        id: prev?.id ?? newId(),
        detect,
        action,
        triggerLabel: action === "trigger" || action === "extract" ? rule.label : undefined,
      };
    });
}

export function withSyncedRules(
  doc: ScriptDocument,
  ivrRules: IvrRule[]
): Pick<ScriptDocument, "ivrRules" | "conversationFlow" | "setup"> {
  return {
    ivrRules,
    conversationFlow: syncConversationFlowFromRules(ivrRules, doc.conversationFlow),
    setup: {
      ...doc.setup,
      runtimeVariables: syncRuntimeVariablesFromRules(ivrRules),
    },
  };
}
