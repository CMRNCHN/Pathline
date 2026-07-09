import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Play } from "lucide-react";
import {
  mintToken,
  placeCallLocally,
  submitEncryptedStatus,
  exportStatus,
  deleteStatus,
  revokeToken,
} from "../api";
import { encryptStatusPayload, generateSessionId, clearLocalKeys } from "../crypto";
import type { LocalSession } from "../types";
import type { KnownScript } from "../script/types";
import { extractOutputRules, extractVariableNames } from "../script/compile";
import {
  getOrCreateUserId,
  loadRunConfig,
  readPreferences,
  recordCompletedRun,
  saveRunConfig,
} from "../persistence";
import {
  hashCollected,
  initialRunState,
  processPhrase,
  type RunState,
} from "../script/runEngine";
import { getActiveScript, mergeScripts } from "../script/selectors";
import { scriptDisplayName } from "../script/storage";
import { useScriptStore } from "../store/ScriptStore";
import { isSpeechRecognitionAvailable, startContinuousRecognition } from "../localStt";
import { PageLayout } from "../components/ui/PageHeader";
import { RunStepBar } from "../components/ui/RunStepBar";

type Step = "consent" | "configure" | "active";

interface ActiveRun {
  script: KnownScript;
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
      eyebrow="Execution"
      title={script ? scriptDisplayName(script) : "Run"}
      subtitle="Run Configuration injects runtime variables. Audio stays on your device."
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
  const [userId, setUserId] = useState<string | null>(null);
  const [prefsAutoListen, setPrefsAutoListen] = useState(false);

  const [targetNumber, setTargetNumber] = useState("");
  const [variables, setVariables] = useState<Record<string, string>>({});
  const configLoadedFor = useRef<string>("");

  useEffect(() => {
    void getOrCreateUserId().then(setUserId);
    void readPreferences().then((prefs) => setPrefsAutoListen(prefs.autoListen));
  }, []);

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
    if (!script?.id) return;
    let cancelled = false;
    configLoadedFor.current = "";
    (async () => {
      const saved = await loadRunConfig(script.id);
      if (cancelled) return;
      setTargetNumber(saved?.target || script.setup.target || "");
      setVariables(saved?.variables ?? {});
      configLoadedFor.current = script.id;
    })();
    return () => {
      cancelled = true;
    };
  }, [script?.id, script?.setup.target]);

  useEffect(() => {
    if (!script?.id || configLoadedFor.current !== script.id) return;
    const timer = window.setTimeout(() => {
      void saveRunConfig(script.id, targetNumber, variables);
    }, 400);
    return () => window.clearTimeout(timer);
  }, [script?.id, targetNumber, variables]);

  const missingVariables = variableNames.filter((name) => !variables[name]?.trim());

  const handleConsent = async () => {
    if (!userId) return;
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
    if (!script) return;
    setLoading(true);
    setError(null);
    try {
      const sessionId = generateSessionId();
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
      placeCallLocally(targetNumber);
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

      const completed: LocalSession = { ...session, status: "completed", collected };
      setSession(completed);
      await recordCompletedRun(completed, activeRun?.variables ?? variables);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit status");
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
          PromptPath v1 uses a client-mediated architecture. Your device places the call,
          holds your secrets, and processes audio locally. The server only receives encrypted status blobs.
        </p>

        <div className="consent-terms">
          <ul>
            <li>Your secrets and target number stay on this device — never sent to our servers</li>
            <li>Speech recognition runs locally when available</li>
            <li>Only encrypted status is reported to PromptPath</li>
            <li>Session data is auto-purged; you can revoke and delete anytime</li>
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
          <p className="hint">No scripts yet. Create one from the Scripts library.</p>
        </div>
      );
    }

    return wrap(
      <>
        <form className="call-form" onSubmit={handleStart}>
          <div className="mode-badge">{scriptDisplayName(script)}</div>

          <p className="hint privacy-note">
            Run Configuration — runtime variables stay on your device.
          </p>

          <div className="form-group">
            <label htmlFor="script">Script</label>
            <select id="script" value={script.id} onChange={(e) => setActiveId(e.target.value)}>
              {scripts.map((s) => (
                <option key={s.id} value={s.id}>{scriptDisplayName(s)}</option>
              ))}
            </select>
            {script.setup.description && <p className="field-hint">{script.setup.description}</p>}
          </div>

          {variableNames.length > 0 && (
            <div className="secrets-section">
              <h3>Runtime variables</h3>
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
              <h3>Results</h3>
              <p className="field-hint">Collected outputs — populated during the call from rule output fields.</p>
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
            {loading ? "Starting…" : "Start check"}
          </button>
        </form>

        {error && <div className="error-banner">{error}</div>}
      </>
    );
  }

  if (!session || !activeRun) return null;

  return wrap(
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
        <MatcherPanel
          script={activeRun.script}
          variables={activeRun.variables}
          defaultAutoListen={prefsAutoListen || activeRun.script.setup.speechPreferences.autoListen}
          onStatusCaptured={handleComplete}
        />
      )}

      {session.status === "completed" && session.collected && (
        <div className="transcript-preview">
          <h4>Run output</h4>
          <pre>{JSON.stringify(session.collected, null, 2)}</pre>
          <p className="hint">Only a hash of this payload was included in the encrypted status sent to the server.</p>
        </div>
      )}

      <div className="session-actions">
        {session.status === "completed" && (
          <button className="btn btn-secondary" onClick={handleExport}>
            Export encrypted status
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
  defaultAutoListen,
  onStatusCaptured,
}: {
  script: KnownScript;
  variables: Record<string, string>;
  defaultAutoListen: boolean;
  onStatusCaptured: (collected: Record<string, string>, transcriptHash: string) => void;
}) {
  const [run, setRun] = useState<RunState>(initialRunState);
  const [ivrText, setIvrText] = useState("");
  const [autoListen, setAutoListen] = useState(defaultAutoListen);
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
          <h5>Run output</h5>
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
