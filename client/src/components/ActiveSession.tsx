import type { LocalSession } from "../types";
import type { KnownScript } from "../script/types";
import { RunPanel } from "./RunPanel";

interface ActiveSessionProps {
  session: LocalSession;
  script: KnownScript;
  secrets: Record<string, string>;
  onComplete: (collected: Record<string, string>, transcriptHash: string) => void;
  onRevoke: () => void;
  onExport: () => void;
  loading: boolean;
}

export function ActiveSession({
  session,
  script,
  secrets,
  onComplete,
  onRevoke,
  onExport,
  loading,
}: ActiveSessionProps) {
  return (
    <div className="session-status">
      <h3>Active run (local)</h3>
      <dl>
        <dt>Status</dt>
        <dd><span className={`status-badge status-${session.status}`}>{session.status}</span></dd>
        <dt>Script</dt>
        <dd>{session.scriptName}</dd>
        <dt>Session ID</dt>
        <dd className="mono">{session.sessionId.slice(0, 8)}…</dd>
        <dt>Target</dt>
        <dd className="mono local-only">Stored on device only</dd>
      </dl>

      {session.status === "in_progress" && (
        <RunPanel script={script} secrets={secrets} onStatusCaptured={onComplete} />
      )}

      {session.status === "completed" && session.collected && (
        <div className="transcript-preview">
          <h4>Collected status</h4>
          <pre>{JSON.stringify(session.collected, null, 2)}</pre>
          <p className="hint">Only a hash of this payload was included in the encrypted status sent to the server.</p>
        </div>
      )}

      <div className="session-actions">
        {session.status === "completed" && (
          <button className="btn btn-secondary" onClick={onExport}>
            Export encrypted status
          </button>
        )}
        <button className="btn btn-danger" onClick={onRevoke} disabled={loading}>
          Revoke & delete all
        </button>
      </div>
    </div>
  );
}
