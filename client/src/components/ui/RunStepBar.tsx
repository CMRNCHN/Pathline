type RunStep = "consent" | "configure" | "active";

const STEPS: { id: RunStep; label: string }[] = [
  { id: "consent", label: "Consent" },
  { id: "configure", label: "Run configuration" },
  { id: "active", label: "Active run" },
];

export function RunStepBar({ current }: { current: RunStep }) {
  const currentIdx = STEPS.findIndex((s) => s.id === current);

  return (
    <nav className="run-step-bar" aria-label="Run progress">
      {STEPS.map((step, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;
        return (
          <div
            key={step.id}
            className={`run-step${active ? " run-step-active" : ""}${done ? " run-step-done" : ""}`}
          >
            <span className="run-step-dot">{done ? "✓" : i + 1}</span>
            <span className="run-step-label">{step.label}</span>
            {i < STEPS.length - 1 && <span className="run-step-line" aria-hidden />}
          </div>
        );
      })}
    </nav>
  );
}
