import { useEffect, useState } from "react";
import { dtmfStepDelayMs, splitDtmfSequence } from "../script/dtmf";

interface DtmfGuideProps {
  sequence: string;
  trigger?: string;
  onComplete: () => void;
}

export function DtmfGuide({ sequence, trigger, onComplete }: DtmfGuideProps) {
  const digits = splitDtmfSequence(sequence);
  const [index, setIndex] = useState(0);
  const isMulti = digits.length > 1;
  const current = digits[index] ?? "";
  const done = isMulti && index >= digits.length - 1;

  useEffect(() => {
    setIndex(0);
  }, [sequence]);

  useEffect(() => {
    if (!isMulti || index >= digits.length - 1) return;
    const delay = dtmfStepDelayMs(digits[index], digits[index + 1]);
    const timer = window.setTimeout(() => setIndex((i) => i + 1), delay);
    return () => window.clearTimeout(timer);
  }, [digits, index, isMulti]);

  if (!digits.length) return null;

  if (!isMulti) {
    return (
      <div className="dtmf-action-card">
        <span className="dtmf-action-label">Send on your phone</span>
        <code className="dtmf-action-value">{sequence}</code>
        {trigger && <span className="dtmf-action-trigger">Heard: {trigger}</span>}
        <button type="button" className="btn btn-sm btn-secondary" onClick={onComplete}>
          Sent ✓
        </button>
      </div>
    );
  }

  return (
    <div className="dtmf-action-card dtmf-guide">
      <span className="dtmf-action-label">Send on your phone — one key at a time</span>
      {trigger && <span className="dtmf-action-trigger">Heard: {trigger}</span>}

      <div className="dtmf-guide-current" aria-live="polite">
        <span className="dtmf-guide-now-label">Press now</span>
        <code className="dtmf-guide-digit">{current}</code>
        <span className="dtmf-guide-progress">
          {index + 1} of {digits.length}
        </span>
      </div>

      <div className="dtmf-guide-track" aria-label="Full DTMF sequence">
        {digits.map((digit, i) => (
          <span
            key={`${digit}-${i}`}
            className={`dtmf-guide-chip${i < index ? " sent" : ""}${i === index ? " active" : ""}`}
          >
            {digit}
          </span>
        ))}
      </div>

      <p className="field-hint">
        Wait for each highlight before pressing the next key (~{Math.round(dtmfStepDelayMs(current) / 100) / 10}s between tones).
      </p>

      <div className="dtmf-guide-actions">
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          onClick={() => setIndex((i) => Math.min(i + 1, digits.length - 1))}
          disabled={done}
        >
          Next key →
        </button>
        <button type="button" className="btn btn-sm btn-primary" onClick={onComplete}>
          {done ? "Sent ✓" : "Done sending"}
        </button>
      </div>
    </div>
  );
}
