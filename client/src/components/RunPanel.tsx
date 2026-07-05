import { useCallback, useEffect, useState } from "react";
import type { KnownScript } from "../script/types";
import {
  hashCollected,
  initialRunState,
  processPhrase,
  type RunState,
} from "../script/runEngine";
import { isSpeechRecognitionAvailable, startContinuousRecognition } from "../localStt";

interface RunPanelProps {
  script: KnownScript;
  secrets: Record<string, string>;
  onStatusCaptured: (collected: Record<string, string>, transcriptHash: string) => void;
}

export function RunPanel({ script, secrets, onStatusCaptured }: RunPanelProps) {
  const [run, setRun] = useState<RunState>(initialRunState);
  const [ivrText, setIvrText] = useState("");
  const [autoListen, setAutoListen] = useState(false);
  const [listenError, setListenError] = useState<string | null>(null);

  const applyPhrase = useCallback(
    (text: string) => {
      setRun((prev) => {
        const result = processPhrase(text, script.rules, secrets, prev);
        if (result.shouldComplete) {
          const { collected } = result.state;
          void hashCollected(collected).then((hash) => onStatusCaptured(collected, hash));
        }
        return result.state;
      });
    },
    [script.rules, secrets, onStatusCaptured]
  );

  useEffect(() => {
    if (!autoListen || run.completed) return;

    setListenError(null);
    const stop = startContinuousRecognition(
      (phrase) => applyPhrase(phrase),
      (msg) => setListenError(msg)
    );

    if (!stop) {
      setAutoListen(false);
      setListenError("Web Speech API unavailable in this browser");
      return;
    }

    return stop;
  }, [autoListen, run.completed, applyPhrase]);

  const handleManualMatch = () => {
    if (!ivrText.trim()) return;
    applyPhrase(ivrText.trim());
    setIvrText("");
  };

  const dismissDtmf = () => {
    setRun((prev) => ({ ...prev, pendingDtmf: undefined, pendingTrigger: undefined }));
  };

  return (
    <div className="navigator-panel run-panel">
      <div className="run-panel-header">
        <h4>{script.name}</h4>
        {isSpeechRecognitionAvailable() && !run.completed && (
          <button
            type="button"
            className={`btn btn-sm ${autoListen ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setAutoListen((v) => !v)}
          >
            {autoListen ? "● Listening" : "Auto-listen"}
          </button>
        )}
      </div>

      <p className="hint">
        {autoListen
          ? "Listening locally — IVR phrases auto-match against your script."
          : "Paste what the IVR said, or enable auto-listen."}
      </p>

      {listenError && <p className="field-hint warn">{listenError}</p>}

      {run.pendingDtmf && (
        <div className="dtmf-action-card">
          <span className="dtmf-action-label">Send on your phone</span>
          <code className="dtmf-action-value">{run.pendingDtmf}</code>
          {run.pendingTrigger && (
            <span className="dtmf-action-trigger">Heard: {run.pendingTrigger}</span>
          )}
          <button type="button" className="btn btn-sm btn-secondary" onClick={dismissDtmf}>
            Sent ✓
          </button>
        </div>
      )}

      {!run.completed && (
        <>
          <div className="form-group">
            <label htmlFor="ivr-phrase">What the IVR said</label>
            <textarea
              id="ivr-phrase"
              rows={2}
              value={ivrText}
              onChange={(e) => setIvrText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleManualMatch();
                }
              }}
              placeholder='e.g. "please enter your account number"'
            />
          </div>
          <button
            className="btn btn-primary btn-full"
            onClick={handleManualMatch}
            disabled={!ivrText.trim()}
          >
            Match
          </button>
        </>
      )}

      {Object.keys(run.collected).length > 0 && (
        <div className="collected-json">
          <h5>Collected status</h5>
          <pre>{JSON.stringify(run.collected, null, 2)}</pre>
        </div>
      )}

      {run.log.length > 0 && (
        <div className="dtmf-log">
          <ul>
            {run.log.map((entry, i) => (
              <li key={i} className={`mono log-${entry.kind}`}>{entry.message}</li>
            ))}
          </ul>
        </div>
      )}

      {run.completed && (
        <p className="hint success-hint">Run complete — encrypted status submitted.</p>
      )}
    </div>
  );
}
