export const SCRIPT_VERSION = 2 as const;

export type FlowAction = "trigger" | "extract" | "validate" | "end" | "pass";

export interface ScriptSetup {
  name: string;
  description: string;
  target: string;
  timeoutMs: number;
  speechPreferences: {
    autoListen: boolean;
  };
  /** Names only — values are filled at Run Configuration. */
  runtimeVariables: string[];
}

export const IVR_EXECUTION_RULES = [
  "Inject DTMF after detect",
  "Inject speech after detect",
  "Wait for IVR response",
  "Capture value after detect",
] as const;

export interface IvrRule {
  id: string;
  label: string;
  /** Expected IVR prompt / phrase that activates this rule. */
  trigger: string;
  /** Response action — typically a {{variable}} reference for DTMF/speech. */
  response: string;
  rule: string;
  /** Run output field name when this rule captures data. */
  output: string;
}

export interface FlowStep {
  id: string;
  detect: string;
  action: FlowAction;
  /** IVR rule label — Trigger fires response; Extract stores detected speech to rule.output. */
  triggerLabel?: string;
}

export interface ScriptDocument {
  id: string;
  version: typeof SCRIPT_VERSION;
  setup: ScriptSetup;
  ivrRules: IvrRule[];
  conversationFlow: FlowStep[];
}

/** Runtime values for a single run — never stored in the template. */
export interface RunConfiguration {
  target: string;
  variables: Record<string, string>;
  runtimeOptions: {
    autoListen: boolean;
  };
}

/** Output produced when a run completes — schema lives here, not in the template. */
export interface ExportPackage {
  sessionId: string;
  scriptId: string;
  scriptName: string;
  extractedData: Record<string, string>;
  activity: RunLogEntry[];
  completedAt: string;
}

export interface RunLogEntry {
  at: string;
  message: string;
  kind: "trigger" | "extract" | "validate" | "pass" | "end" | "unknown" | "info";
}

export interface RunState {
  collected: Record<string, string>;
  log: RunLogEntry[];
  lastPhrase?: string;
  pendingDtmf?: string;
  pendingTrigger?: string;
  completed: boolean;
}

export type KnownScript = ScriptDocument;
