export const SCRIPT_VERSION = 2 as const;

export type FlowAction = "trigger" | "extract" | "validate" | "end" | "pass";

export interface PathSetup {
  name: string;
  description: string;
  /** Optional path hint for where this template lives on the user's device. */
  localPath: string;
  target: string;
  timeoutMs: number;
  speechPreferences: {
    autoListen: boolean;
  };
  /** Input names referenced by respond Steps — derived from Steps on sync. */
  inputs: string[];
}

export const IVR_EXECUTION_RULES = [
  "Inject DTMF after detect",
  "Inject speech after detect",
  "Wait for IVR response",
  "Capture value after detect",
  "Validate collected outputs",
  "End call",
] as const;

/**
 * A single Step in a Path.
 * Field keys stay stable for on-disk/back-compat; Pathline terms map as:
 *   trigger  -> When (what starts the Step)
 *   rule     -> Then (the action performed)
 *   response -> Then value (Input reference or literal)
 *   output   -> captured result name
 */
export interface Step {
  id: string;
  label: string;
  /** When: expected IVR prompt / phrase that starts this Step. */
  when: string;
  /** Then value — typically a {{input}} reference for DTMF/speech. */
  then: string;
  /** Then action type. */
  rule: string;
  /** Captured result name when this Step captures data. */
  output: string;
  /** Pause duration for wait Steps (seconds). */
  waitSeconds?: number;
}

export interface FlowStep {
  id: string;
  detect: string;
  action: FlowAction;
  /** Step label — Trigger fires response; Extract stores detected speech to step.output. */
  triggerLabel?: string;
}

export interface PathDocument {
  id: string;
  version: typeof SCRIPT_VERSION;
  setup: PathSetup;
  steps: Step[];
  conversationFlow: FlowStep[];
}

/** Input values for a single Run — never stored with the Path. */
export interface RunConfiguration {
  target: string;
  variables: Record<string, string>;
  runtimeOptions: {
    autoListen: boolean;
  };
}

/** Result produced when a Run completes — schema lives on Steps, not the Path. */
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

export type Path = PathDocument;
