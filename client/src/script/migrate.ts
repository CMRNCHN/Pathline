import type { FlowStep, IvrRule, ScriptDocument, ScriptSetup } from "./types";
import { SCRIPT_VERSION } from "./types";
import { newId } from "./storage";

/** v1 shape — used only for one-time migration. */
interface V1ConversationStep {
  id?: string;
  listenFor?: string;
  action?: string;
  keys?: string;
  resultKey?: string;
  value?: string;
}

interface V1StatusRule {
  trigger?: string;
  response?: string;
  key?: string;
  status?: string;
  dtmf?: string;
  endCall?: boolean;
}

interface V1Document {
  id?: string;
  name?: string;
  description?: string;
  target?: string;
  timeoutMs?: number;
  secrets?: unknown;
  conversation?: V1ConversationStep[];
  results?: { id?: string; key?: string; description?: string }[];
  rules?: V1StatusRule[];
}

function slugLabel(prefix: string, index: number): string {
  return `${prefix}_${index}`;
}

function toResponseRef(keys: string, index: number): string {
  if (!keys.trim()) return `{{dtmf_${index}}}`;
  const doubled = keys.replace(/\{(\w+)\}/g, "{{$1}}");
  if (doubled.includes("{{")) return doubled;
  return `{{dtmf_${index}}}`;
}

function ensureExtractRule(
  ivrRules: IvrRule[],
  field: string,
  trigger: string
): { ivrRules: IvrRule[]; label: string } {
  const existing = ivrRules.find((r) => r.output === field);
  if (existing) return { ivrRules, label: existing.label };

  const label = field || slugLabel("capture", ivrRules.length + 1);
  const rule: IvrRule = {
    id: newId(),
    label,
    trigger,
    response: "",
    rule: "Capture value after detect",
    output: field || label,
  };
  return { ivrRules: [...ivrRules, rule], label };
}

function migrateLegacyRulesToFlow(rules: V1StatusRule[]): {
  ivrRules: IvrRule[];
  conversationFlow: FlowStep[];
} {
  let ivrRules: IvrRule[] = [];
  const conversationFlow: FlowStep[] = [];
  let ruleIndex = 0;

  for (const rule of rules) {
    const isSend = Boolean(rule.trigger?.trim() || rule.dtmf?.trim());
    if (isSend) {
      ruleIndex += 1;
      const label = slugLabel("rule", ruleIndex);
      ivrRules.push({
        id: newId(),
        label,
        response: toResponseRef(rule.dtmf ?? "", ruleIndex),
        trigger: rule.trigger ?? "",
        rule: "Inject DTMF after detect",
        output: "",
      });
      conversationFlow.push({
        id: newId(),
        detect: rule.trigger ?? "",
        action: "trigger",
        triggerLabel: label,
      });
    } else if (rule.response?.trim()) {
      const field = rule.key?.trim() || slugLabel("field", ruleIndex + 1);
      const ensured = ensureExtractRule(ivrRules, field, rule.response);
      ivrRules = ensured.ivrRules;
      conversationFlow.push({
        id: newId(),
        detect: rule.response,
        action: "extract",
        triggerLabel: ensured.label,
      });
      if (rule.endCall) {
        conversationFlow.push({ id: newId(), detect: rule.response, action: "end" });
      }
    } else if (rule.endCall) {
      conversationFlow.push({ id: newId(), detect: "", action: "end" });
    }
  }

  return { ivrRules, conversationFlow };
}

export function migrateV1ToV2(raw: unknown): ScriptDocument {
  const o = raw as V1Document;

  const setup: ScriptSetup = {
    name: o.name ?? "",
    description: o.description ?? "",
    target: o.target ?? "",
    timeoutMs: o.timeoutMs ?? 30000,
    speechPreferences: { autoListen: false },
    runtimeVariables: [],
  };

  let ivrRules: IvrRule[] = [];
  let conversationFlow: FlowStep[] = [];

  const conversation = o.conversation ?? [];
  if (conversation.length === 0 && o.rules?.length) {
    const migrated = migrateLegacyRulesToFlow(o.rules);
    ivrRules = migrated.ivrRules;
    conversationFlow = migrated.conversationFlow;
  } else {
    let ruleIndex = 0;
    for (const step of conversation) {
      if (step.action === "send_keys") {
        ruleIndex += 1;
        const label = slugLabel("rule", ruleIndex);
        ivrRules.push({
          id: newId(),
          label,
          response: toResponseRef(step.keys ?? "", ruleIndex),
          trigger: step.listenFor ?? "",
          rule: "Inject DTMF after detect",
          output: "",
        });
        conversationFlow.push({
          id: step.id ?? newId(),
          detect: step.listenFor ?? "",
          action: "trigger",
          triggerLabel: label,
        });
      } else if (step.action === "save_value") {
        const field = step.resultKey?.trim() || slugLabel("field", ruleIndex + 1);
        const ensured = ensureExtractRule(ivrRules, field, step.listenFor ?? "");
        ivrRules = ensured.ivrRules;
        conversationFlow.push({
          id: step.id ?? newId(),
          detect: step.listenFor ?? "",
          action: "extract",
          triggerLabel: ensured.label,
        });
      } else if (step.action === "hang_up") {
        conversationFlow.push({
          id: step.id ?? newId(),
          detect: step.listenFor ?? "",
          action: "end",
        });
      } else if (step.action === "wait" || step.listenFor?.trim()) {
        conversationFlow.push({
          id: step.id ?? newId(),
          detect: step.listenFor ?? "",
          action: "pass",
        });
      }
    }
  }

  for (const r of o.results ?? []) {
    if (r.key?.trim()) {
      const ensured = ensureExtractRule(ivrRules, r.key, "");
      ivrRules = ensured.ivrRules;
    }
  }

  const runtimeVariables = new Set<string>();
  for (const rule of ivrRules) {
    for (const m of rule.response.matchAll(/\{\{(\w+)\}\}/g)) {
      runtimeVariables.add(m[1]);
    }
  }
  setup.runtimeVariables = [...runtimeVariables].sort();

  return {
    id: o.id ?? newId(),
    version: SCRIPT_VERSION,
    setup,
    ivrRules,
    conversationFlow,
  };
}
