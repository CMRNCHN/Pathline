import type { LiveStatus, Path } from "../callstate";
import { formatLiveStatusText } from "../callstate";

interface CallStateBoardProps {
  liveStatus: LiveStatus;
  path: Path;
  label?: string;
}

/** Renders a LiveStatus projection as plain text — no projection logic here. */
export function CallStateBoard({ liveStatus, path, label = "Callstate" }: CallStateBoardProps) {
  const text = formatLiveStatusText(liveStatus, path);

  return (
    <section className="callstate-board" aria-label={label}>
      <div className="callstate-board-head">
        <span className="callstate-board-title">{label}</span>
        <span className="callstate-board-phase">{liveStatus.phase}</span>
      </div>
      <pre className="callstate-text">{text}</pre>
    </section>
  );
}
