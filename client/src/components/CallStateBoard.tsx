import type { CallState, Path } from "../callstate";
import { formatCallStateText } from "../callstate";

interface CallStateBoardProps {
  callState: CallState;
  path: Path;
  label?: string;
}

export function CallStateBoard({ callState, path, label = "Callstate" }: CallStateBoardProps) {
  const text = formatCallStateText(callState, path);

  return (
    <section className="callstate-board" aria-label={label}>
      <div className="callstate-board-head">
        <span className="callstate-board-title">{label}</span>
        <span className="callstate-board-phase">{callState.phase}</span>
      </div>
      <pre className="callstate-text">{text}</pre>
    </section>
  );
}
