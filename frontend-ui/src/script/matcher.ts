import type { StatusRule } from "./types";

export type MatchResult =
  | { type: "trigger"; rule: StatusRule; dtmf?: string }
  | { type: "status"; rule: StatusRule }
  | { type: "none" };

function matches(text: string, phrase: string): boolean {
  if (!phrase.trim()) return false;
  const hay = text.toLowerCase().replace(/\s+/g, " ").trim();
  return phrase
    .split("|")
    .map((p) => p.trim().toLowerCase())
    .filter(Boolean)
    .some((needle) => hay.includes(needle));
}

export function resolveDtmf(template: string, secrets: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => secrets[key] ?? `{${key}}`);
}

export function matchIvrPhrase(
  text: string,
  rules: StatusRule[],
  secrets: Record<string, string>
): MatchResult {
  for (const rule of rules) {
    if (rule.trigger && matches(text, rule.trigger)) {
      return {
        type: "trigger",
        rule,
        dtmf: rule.dtmf ? resolveDtmf(rule.dtmf, secrets) : undefined,
      };
    }
  }

  for (const rule of rules) {
    if (rule.response && matches(text, rule.response)) {
      return { type: "status", rule };
    }
  }

  return { type: "none" };
}
