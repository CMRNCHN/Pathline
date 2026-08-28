export type AnomalySeverity = "info" | "warn" | "error";

export type AnomalyCode =
  | "LEDGER_INTEGRITY_BREAK"
  | "NON_MONOTONIC_TIMELINE"
  | "EMPTY_LEDGER"
  | "STEP_SKIPPED"
  | "UNEXPECTED_LOOP"
  | "PROMPT_WITHOUT_ACTION"
  | "STALLED_RUN";

export type ReferenceKind = "event" | "report_field" | "artifact" | "timestamp";

export interface Reference {
  kind: ReferenceKind;
  label: string;
  eventId?: string;
  eventIndex?: number;
  fieldPath?: string;
  tMs?: number;
}

export interface Anomaly {
  code: AnomalyCode;
  severity: AnomalySeverity;
  explanation: string;
  references: Reference[];
}

export interface NextStep {
  action: string;
  rationale: string;
  cites: Reference[];
}

export interface ChronologyEntry {
  seq: number;
  type: string;
  tMs: number;
  deltaMs: number;
  eventId: string;
  step?: string;
}

export interface ArtifactAvailability {
  artifact: string;
  available: boolean;
  detail: string;
}

export interface LedgerVerification {
  ok: boolean;
  eventCount: number;
  breakIndex?: number;
  expectedHash?: string;
  actualHash?: string;
  reason?: string;
}

export interface RunInspectionReport {
  schemaVersion: "1.0";
  identity: {
    runId: string;
    pathId: string;
    pathName: string;
    outcome: string;
  };
  artifactAvailability: ArtifactAvailability[];
  summary: {
    eventCount: number;
    promptCount: number;
    actionCount: number;
    firstEventAt?: string;
    lastEventAt?: string;
    durationMs: number;
    largestGapMs: number;
    notes: string[];
  };
  chronology: ChronologyEntry[];
  path: {
    definedSteps: string[];
    progress: string[];
    skippedSteps: string[];
    activeStep: string | null;
    finalOutcome: string | null;
  };
  correlation: {
    startToFirstPromptMs: number | null;
    lastPromptToEndMs: number | null;
  };
  ledger: LedgerVerification;
  anomalies: Anomaly[];
  nextSteps: NextStep[];
}
