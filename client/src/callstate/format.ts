import type { LiveStatus } from "./types";

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

function progressLine(step: string, progress: string[], active: string | null): string {
  const reached = progress.includes(step);
  const marker = !reached
    ? STEP_MARKERS.pending
    : step === active
      ? STEP_MARKERS.active
      : STEP_MARKERS.done;
  return `${marker} ${step}`;
}

/** Plain-text renderer — UI/CLI layer only; not part of LiveStatus. */
export function formatLiveStatusText(
  liveStatus: LiveStatus,
  path: { intent: string; definedSteps: string[] }
): string {
  const lines: string[] = ["CALL", path.intent, ""];

  if (liveStatus.phase === "ACTIVE" && liveStatus.activeStep) {
    lines.push("CURRENT STATE", `${STEP_MARKERS.active} ${liveStatus.activeStep}`, "");
  } else if (liveStatus.phase === "COMPLETED" && liveStatus.finalOutcome) {
    lines.push("CALL STATE", `${STEP_MARKERS.done} ${liveStatus.finalOutcome}`, "");
  }

  lines.push("CALL PROGRESS");
  for (const step of path.definedSteps) {
    lines.push(progressLine(step, liveStatus.progress, liveStatus.activeStep));
  }

  lines.push("", "EVENT TIMELINE");
  for (const event of liveStatus.events) {
    lines.push(`${formatTime(event.timestamp)}  ${event.type}`);
  }

  return lines.join("\n");
}
