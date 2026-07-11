import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Play } from "lucide-react";
import {
  mintToken,
  placeCallLocally,
  linkConsentSession,
  submitEncryptedStatus,
  exportStatus,
  deleteStatus,
  revokeToken,
} from "../api";
import { encryptStatusPayload, generateUserId, generateSessionId, clearLocalKeys } from "../crypto";
import type { LocalSession } from "../types";
import type { Path } from "../script/types";
import { extractOutputRules, extractVariableNames } from "../script/compile";
import {
  hashCollected,
  initialRunState,
  processPhrase,
  type RunState,
} from "../script/runEngine";
import { getActiveScript, mergeScripts } from "../script/selectors";
import { scriptDisplayName } from "../script/storage";
import { recordRun } from "../history/runHistory";
import { useScriptStore } from "../store/ScriptStore";
import { isSpeechRecognitionAvailable, startContinuousRecognition } from "../localStt";
import { PageLayout } from "../components/ui/PageHeader";
import { RunStepBar } from "../components/ui/RunStepBar";
import { DtmfGuide } from "../components/DtmfGuide";

type Step = "consent" | "configure" | "active";

interface ActiveRun {
  script: Path;
  variables: Record<string, string>;
}

interface RunPageProps {
  scriptId: string;
}

export function RunPage({ scriptId }: RunPageProps) {
  const { bundledScripts, customScripts, activeId, setActiveId, loading: loadingScripts, error: scriptError } =
    useScriptStore();

  useEffect(() => {
    setActiveId(scriptId);
  }, [scriptId, setActiveId]);

  const script = getActiveScript(bundledScripts, customScripts, scriptId);

  return (
    <PageLayout
      eyebrow="Run"
      title={script ? scriptDisplayName(script) : "Run"}
      subtitle="Inputs stay on your device. Call audio is processed locally."
      action={
        <span className="run-badge">
          <Play size={14} />
          Client-mediated
        </span>
      }
    >
      <RunFlow
        key={`${scriptId}-${activeId}`}
        loadingScripts={loadingScripts}
        scriptError={scriptError}
      />
    </PageLayout>
  );
}

function RunFlow({
  loadingScripts,
  scriptError,
}: {
  loadingScripts: boolean;
  scriptError: string | null;
}) {
  const { bundledScripts, customScripts, activeId, setActiveId } = useScriptStore();

  const [step, setStep] = useState<Step>("consent");
  const [consentChecked, setConsentChecked] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [session, setSession] = useState<LocalSession | null>(null);
  const [activeRun, setActiveRun] = useState<ActiveRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userId] = useState(() => generateUserId());

  const [targetNumber, setTargetNumber] = useState("");
  const [variables, setVariables] = useState<Record<string, string>>({});

  const scripts = mergeScripts(bundledScripts, customScripts);
  const script = getActiveScript(bundledScripts, customScripts, activeId) ?? scripts[0];

  const variableNames = useMemo(() => {
    if (!script) return [];
    return extractVariableNames(script);
  }, [script]);

  const outputFields = useMemo(() => {
    if (!script) return [];
    return extractOutputRules(script).map((r) => r.output);
  }, [script]);

  useEffect(() => {
    if (script?.setup.target) setTargetNumber(script.setup.target);
    else setTargetNumber("");
  }, [script?.id, script?.setup.target]);

  const missingVariables = variableNames.filter((name) => !variables[name]?.trim());

  const handleConsent = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await mintToken(userId, {
        accepted: true,
        timestamp: new Date().toISOString(),
        terms_version: "1.0",
      });
      setToken(resp.access_token);
      setStep("configure");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to authenticate");
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!script || !token) return;
    setLoading(true);
    setError(null);
    try {
      const sessionId = generateSessionId();
      await linkConsentSession(token, sessionId);
      setActiveRun({ script, variables });
      setSession({
        sessionId,
        scriptId: script.id,
        scriptName: scriptDisplayName(script),
        targetNumber,
        status: "in_progress",
        startedAt: new Date().toISOString(),
      });
      setStep("active");
      if (targetNumber.trim()) {
        placeCallLocally(targetNumber);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async (collected: Record<string, string>, transcriptHash: string) => {
    if (!token || !session) return;
    setLoading(true);
    setError(null);
    try {
      const encrypted = await encryptStatusPayload({
        status: "completed",
        fields: collected,
        transcript_hash: transcriptHash,
        completed_at: new Date().toISOString(),
      });

      await submitEncryptedStatus(token, session.sessionId, encrypted.ciphertext, encrypted.nonce);

      recordRun({
        runId: session.sessionId,
        pathId: session.scriptId,
        pathName: session.scriptName,
        outcome: "completed",
        startedAt: session.startedAt,
        completedAt: new Date().toISOString(),
        captured: collected,
      });

      setSession({ ...session, status: "completed", collected });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit Status");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!token || !session) return;
    try {
      const data = await exportStatus(token, session.sessionId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `promptpath-export-${session.sessionId.slice(0, 8)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  };

  const handleRevoke = async () => {
    if (token && session) {
      await deleteStatus(token, session.sessionId);
      await revokeToken(token);
    }
    clearLocalKeys();
    setToken(null);
    setSession(null);
    setActiveRun(null);
    setStep("consent");
    setConsentChecked(false);
  };

  const wrap = (body: ReactNode) => (
    <div className="run-panel-wrap">
      <RunStepBar current={step} />
      {body}
    </div>
  );

  if (step === "consent") {
    return wrap(
      <div className="consent-panel">
        <h2>Consent & Authorization</h2>
        <p className="consent-intro">
          Pathline is client-mediated. Your device places the call, holds your Inputs and Secrets,
          and processes audio locally. The server only receives encrypted Status blobs.
        </p>

        <div className="consent-terms">
          <ul>
            <li>Your Secrets and target number stay on this device — never sent to our servers</li>
            <li>Speech recognition runs locally when available</li>
            <li>Only encrypted Status is reported to Pathline</li>
            <li>Run data is auto-purged; you can revoke and delete anytime</li>
            <li>Carriers still see calling/called numbers, times, and duration</li>
            <li>You confirm lawful usage and authorization for third-party IVR interactions</li>
          </ul>
        </div>

        <label className="consent-checkbox">
          <input
            type="checkbox"
            checked={consentChecked}
            onChange={(e) => setConsentChecked(e.target.checked)}
          />
          <span>I have read and accept these terms (v1.0)</span>
        </label>

        <div className="consent-actions">
          <button className="btn btn-secondary" onClick={() => setError("Consent declined — cannot proceed")}>
            Decline
          </button>
          <button className="btn btn-primary" disabled={!consentChecked || loading} onClick={handleConsent}>
            Accept & Continue
          </button>
        </div>

        {error && <div className="error-banner">{error}</div>}
      </div>
    );
  }

  if (step === "configure") {
    if (loadingScripts) {
      return wrap(<p className="hint">Loading scripts…</p>);
    }

    if (scriptError) {
      return wrap(<div className="error-banner">{scriptError}</div>);
    }

    if (!script) {
      return wrap(
        <div className="call-form">
          <p className="hint">No Paths yet. Create one from Paths.</p>
        </div>
      );
    }

    return wrap(
      <>
        <form className="call-form" onSubmit={handleStart}>
          <div className="mode-badge">{scriptDisplayName(script)}</div>

          <p className="hint privacy-note">Inputs stay on your device.</p>

          <div className="form-group">
            <label htmlFor="script">Path</label>
            <select id="script" value={script.id} onChange={(e) => setActiveId(e.target.value)}>
              {scripts.map((s) => (
                <option key={s.id} value={s.id}>{scriptDisplayName(s)}</option>
              ))}
            </select>
            {script.setup.description && <p className="field-hint">{script.setup.description}</p>}
          </div>

          {variableNames.length > 0 && (
            <div className="secrets-section">
              <h3>Inputs</h3>
              {variableNames.map((name) => (
                <div key={name} className="form-group">
                  <label htmlFor={`var-${name}`}>{name}</label>
                  <input
                    id={`var-${name}`}
                    type="password"
                    value={variables[name] ?? ""}
                    onChange={(e) => setVariables((prev) => ({ ...prev, [name]: e.target.value }))}
                    placeholder={name}
                    autoComplete="off"
                    required
                  />
                </div>
              ))}
            </div>
          )}

          {outputFields.length > 0 && (
            <div className="run-outputs-preview">
              <h3>Captures</h3>
              <p className="field-hint">What this Path saves during the call — reviewable later in History.</p>
              <div className="output-chip-row">
                {outputFields.map((field) => (
                  <span key={field} className="output-chip mono">{field}</span>
                ))}
              </div>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="target">Target number — local only</label>
            <input
              id="target"
              type="tel"
              value={targetNumber}
              onChange={(e) => setTargetNumber(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={loading || missingVariables.length > 0}
          >
            {loading ? "Starting…" : "Run"}
          </button>
        </form>

        {error && <div className="error-banner">{error}</div>}
      </>
    );
  }

  if (!session || !activeRun) return null;

  return wrap(
    <div className="session-status">
      <h3>Status</h3>
      <dl>
        <dt>State</dt>
        <dd><span className={`status-badge status-${session.status}`}>{session.status === "in_progress" ? "active" : session.status}</span></dd>
        <dt>Path</dt>
        <dd>{session.scriptName}</dd>
        <dt>Run ID</dt>
        <dd className="mono">{session.sessionId.slice(0, 8)}…</dd>
        <dt>Target</dt>
        <dd className="mono local-only">Stored on device only</dd>
      </dl>

      {session.status === "in_progress" && (
        <MatcherPanel
          script={activeRun.script}
          variables={activeRun.variables}
          onStatusCaptured={handleComplete}
        />
      )}

      {session.status === "completed" && session.collected && (
        <div className="transcript-preview">
          <h4>Captured</h4>
          <pre>{JSON.stringify(session.collected, null, 2)}</pre>
          <p className="hint">Saved to History on this device. Only a hash of this payload was sent to the server.</p>
        </div>
      )}

      <div className="session-actions">
        {session.status === "completed" && (
          <button className="btn btn-secondary" onClick={handleExport}>
            Export
          </button>
        )}
        <button className="btn btn-danger" onClick={handleRevoke} disabled={loading}>
          Revoke & delete all
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}

function MatcherPanel({
  script,
  variables,
  onStatusCaptured,
}: {
  script: Path;
  variables: Record<string, string>;
  onStatusCaptured: (collected: Record<string, string>, transcriptHash: string) => void;
}) {
  const [run, setRun] = useState<RunState>(initialRunState);
  const [ivrText, setIvrText] = useState("");
  const [autoListen, setAutoListen] = useState(script.setup.speechPreferences.autoListen);
  const [listenError, setListenError] = useState<string | null>(null);
  const debounceRef = useRef<number | undefined>(undefined);

  const applyPhraseNow = useCallback(
    (text: string) => {
      setRun((prev) => {
        const result = processPhrase(text, script, variables, prev);
        if (result.shouldComplete) {
          const { collected } = result.state;
          void hashCollected(collected).then((hash) => onStatusCaptured(collected, hash));
        }
        return result.state;
      });
    },
    [script, variables, onStatusCaptured]
  );

  const applyPhraseDebounced = useCallback(
    (text: string) => {
      window.clearTimeout(debounceRef.current);
      debounceRef.current = window.setTimeout(() => applyPhraseNow(text), 150);
    },
    [applyPhraseNow]
  );

  useEffect(() => {
    if (!autoListen || run.completed) return;

    setListenError(null);
    const stop = startContinuousRecognition(
      (phrase) => applyPhraseDebounced(phrase),
      (msg) => setListenError(msg)
    );

    if (!stop) {
      setAutoListen(false);
      setListenError("Web Speech API unavailable in this browser");
      return;
    }

    return stop;
  }, [autoListen, run.completed, applyPhraseDebounced]);

  const handleManualMatch = () => {
    if (!ivrText.trim()) return;
    applyPhraseNow(ivrText.trim());
    setIvrText("");
  };

  const dismissDtmf = () => {
    setRun((prev) => ({ ...prev, pendingDtmf: undefined, pendingTrigger: undefined }));
  };

  return (
    <div className="navigator-panel run-panel">
      <div className="run-panel-header">
        <h4>{scriptDisplayName(script)}</h4>
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
          : "Paste what you hear, or enable auto-listen."}
      </p>

      {listenError && <p className="field-hint warn">{listenError}</p>}

      {run.pendingDtmf && (
        <DtmfGuide
          sequence={run.pendingDtmf}
          trigger={run.pendingTrigger}
          onComplete={dismissDtmf}
        />
      )}

      {!run.completed && (
        <>
          <div className="form-group">
            <label htmlFor="ivr-phrase">Listen</label>
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
          <h5>Captured</h5>
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
