import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Play } from "lucide-react";
import {
  mintToken,
  placeCallLocally,
  submitEncryptedStatus,
  exportStatus,
  deleteStatus,
  revokeToken,
} from "../api";
import { encryptStatusPayload, generateUserId, generateSessionId, clearLocalKeys } from "../crypto";
import type { LocalSession } from "../types";
import type { KnownScript } from "../script/types";
import { compileToRules, requiredSecretNames } from "../script/compile";
import {
  hashCollected,
  initialRunState,
  processPhrase,
  type RunState,
} from "../script/runEngine";
import { getActiveScript, mergeScripts } from "../script/selectors";
import { useScriptStore } from "../store/ScriptStore";
import { isSpeechRecognitionAvailable, startContinuousRecognition } from "../localStt";
import { PageLayout } from "../components/ui/PageHeader";

type Step = "consent" | "configure" | "active";

interface ActiveRun {
  script: KnownScript;
  secrets: Record<string, string>;
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
      title={script?.name || "Run Template"}
      subtitle="Execute this script locally. Secrets and audio stay on your device."
      action={
        <div className="flex items-center gap-2 text-xs text-muted bg-white border border-[#0a0a0b14] px-3 py-1.5 rounded-md">
          <Play className="w-3.5 h-3.5 text-accent" />
          Client-mediated run
        </div>
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
  const [secrets, setSecrets] = useState<Record<string, string>>({});

  const scripts = mergeScripts(bundledScripts, customScripts);
  const script = getActiveScript(bundledScripts, customScripts, activeId) ?? scripts[0];

  const secretFields = useMemo(() => {
    if (!script) return [];
    const names = requiredSecretNames(script);
    const byName = new Map(script.secrets.map((s) => [s.name, s]));
    return names.map((name) => byName.get(name) ?? {
      id: name,
      name,
      description: `Value for ${name}`,
      example: "",
      required: true,
    });
  }, [script]);

  useEffect(() => {
    if (script?.target) setTargetNumber(script.target);
    else setTargetNumber("");
  }, [script?.id, script?.target]);

  const missingSecrets = secretFields.filter((s) => s.required && !secrets[s.name]?.trim());

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
    if (!script) return;
    setLoading(true);
    setError(null);
    try {
      const sessionId = generateSessionId();
      setActiveRun({ script, secrets });
      setSession({
        sessionId,
        scriptId: script.id,
        scriptName: script.name,
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

      setSession({ ...session, status: "completed", collected });
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

  if (step === "consent") {
    return (
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
      return <p className="hint">Loading scripts…</p>;
    }

    if (scriptError) {
      return <div className="error-banner">{scriptError}</div>;
    }

    if (!script) {
      return (
        <div className="call-form">
          <p className="hint">No scripts yet. Create one on the <strong>Scripts</strong> tab.</p>
        </div>
      );
    }

    return (
      <>
        <form className="call-form" onSubmit={handleStart}>
          <div className="mode-badge">{script.name || "Untitled script"}</div>

          <p className="hint privacy-note">
            This script needs a few values from you. They stay on your device.
          </p>

          <div className="form-group">
            <label htmlFor="script">Script</label>
            <select id="script" value={script.id} onChange={(e) => setActiveId(e.target.value)}>
              {scripts.map((s) => (
                <option key={s.id} value={s.id}>{s.name || "Untitled"}</option>
              ))}
            </select>
            {script.description && <p className="field-hint">{script.description}</p>}
          </div>

          {secretFields.length > 0 && (
            <div className="secrets-section">
              <h3>This script needs</h3>
              {secretFields.map((field) => (
                <div key={field.name} className="form-group">
                  <label htmlFor={`secret-${field.name}`}>
                    {field.description || field.name}
                  </label>
                  <input
                    id={`secret-${field.name}`}
                    type="password"
                    value={secrets[field.name] ?? ""}
                    onChange={(e) => setSecrets((prev) => ({ ...prev, [field.name]: e.target.value }))}
                    placeholder={field.example || field.name}
                    autoComplete="off"
                    required={field.required}
                  />
                </div>
              ))}
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
            disabled={loading || missingSecrets.length > 0}
          >
            {loading ? "Starting…" : "Start check"}
          </button>
        </form>

        {error && <div className="error-banner">{error}</div>}
      </>
    );
  }

  if (!session || !activeRun) return null;

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
        <MatcherPanel
          script={activeRun.script}
          secrets={activeRun.secrets}
          onStatusCaptured={handleComplete}
        />
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
  secrets,
  onStatusCaptured,
}: {
  script: KnownScript;
  secrets: Record<string, string>;
  onStatusCaptured: (collected: Record<string, string>, transcriptHash: string) => void;
}) {
  const rules = useMemo(() => compileToRules(script), [script]);
  const [run, setRun] = useState<RunState>(initialRunState);
  const [ivrText, setIvrText] = useState("");
  const [autoListen, setAutoListen] = useState(false);
  const [listenError, setListenError] = useState<string | null>(null);
  const debounceRef = useRef<number | undefined>(undefined);

  const applyPhraseNow = useCallback(
    (text: string) => {
      setRun((prev) => {
        const result = processPhrase(text, rules, secrets, prev);
        if (result.shouldComplete) {
          const { collected } = result.state;
          void hashCollected(collected).then((hash) => onStatusCaptured(collected, hash));
        }
        return result.state;
      });
    },
    [rules, secrets, onStatusCaptured]
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
        <h4>{script.name || "Untitled script"}</h4>
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
