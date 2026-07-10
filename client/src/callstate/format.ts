import type { CallState, Path, PathStep } from "./types";

const STEP_MARKERS = {
  done: "✓",
  active: "●",
  pending: "○",
} as const;

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString("en-GB", { hour12: false });
}

function progressLine(step: PathStep, state: PathStep[], active: PathStep | null): string {
  const reached = state.includes(step);
  const marker = !reached
    ? STEP_MARKERS.pending
    : step === active
      ? STEP_MARKERS.active
      : STEP_MARKERS.done;
  return `${marker} ${step}`;
}

export function formatCallStateText(callState: CallState, path: Path): string {
  const lines: string[] = ["CALL", path.intent.toUpperCase(), ""];

  if (callState.phase === "ACTIVE" && callState.activeStep) {
    lines.push("CURRENT STATE", `${STEP_MARKERS.active} ${callState.activeStep}`, "");
  } else if (callState.phase === "COMPLETED") {
    const outcome = callState.finalOutcome ?? "VERIFICATION_COMPLETE";
    lines.push("CALL STATE", `${STEP_MARKERS.done} ${outcome}`, "");
  }

  lines.push("CALL PROGRESS");
  for (const step of path.definedSteps) {
    lines.push(progressLine(step, callState.progress, callState.activeStep));
  }

  lines.push("", "EVENT TIMELINE");
  for (const event of callState.events) {
    lines.push(`${formatTime(event.timestamp)}  ${event.type}`);
  }

  return lines.join("\n");
}
