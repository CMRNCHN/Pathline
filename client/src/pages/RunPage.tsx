import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Play } from "lucide-react";
import {
  mintToken,
  placeCallLocally,
  submitEncryptedCallState,
  exportCallState,
  deleteCallState,
  revokeToken,
} from "../api";
import { encryptCallStatePayload, generateUserId, generateSessionId, clearLocalKeys } from "../crypto";
import type { LocalCall } from "../types";
import { CallStateBoard } from "../components/CallStateBoard";
import {
  pathFromScript,
  projectLiveStatus,
  runLogToCallEvents,
  newCallEvent,
  callFromSession,
  type CallEvent,
} from "../callstate";
import type { KnownScript } from "../script/types";
import { extractOutputRules, extractVariableNames } from "../script/compile";
import {
  hashCollected,
  initialRunState,
  processPhrase,
  type RunState,
} from "../script/runEngine";
import { getActiveScript, mergeScripts } from "../script/selectors";
import { scriptDisplayName } from "../script/storage";
import { useScriptStore } from "../store/ScriptStore";
import { PageLayout } from "../components/ui/PageHeader";
import { RunStepBar } from "../components/ui/RunStepBar";
import { voiceInputPlaceholder, VOICE_INPUT_ENABLED } from "../runCapabilities";

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
  const [session, setSession] = useState<LocalCall | null>(null);
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

  const isLabScript = script?.id === "lab-account-status";

  useEffect(() => {
    if (!isLabScript) return;
    setVariables((prev) => ({
      ...prev,
      account_pin: prev.account_pin || "1234",
      ssn_last4: prev.ssn_last4 || "5678",
    }));
  }, [isLabScript]);

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
        phase: "active",
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

  const handleComplete = async (
    collected: Record<string, string>,
    transcriptHash: string,
    callEvents: CallEvent[]
  ) => {
    if (!token || !session) return;
    setLoading(true);
    setError(null);
    try {
      const encrypted = await encryptCallStatePayload({
        phase: "completed",
        fields: collected,
        transcript_hash: transcriptHash,
        completed_at: new Date().toISOString(),
      });

      await submitEncryptedCallState(token, session.sessionId, encrypted.ciphertext, encrypted.nonce);

      setSession({ ...session, phase: "completed", collected, callEvents });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit callstate");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!token || !session) return;
    try {
      const data = await exportCallState(token, session.sessionId);
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
      await deleteCallState(token, session.sessionId);
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
          holds your secrets, and sends DTMF on your phone when prompted. The server only receives encrypted callstate blobs.
        </p>

        <div className="consent-terms">
          <ul>
            <li>Your secrets and target number stay on this device — never sent to our servers</li>
            <li>Runs use <strong>DTMF keypad</strong> on your phone — required in v1</li>
            <li>Voice input is planned for a later release; not used today</li>
            <li>Only encrypted callstate is reported to PromptPath</li>
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

          {isLabScript && (
            <div className="lab-run-guide">
              <h3>Lab softphone setup</h3>
              <ol>
                <li>Start lab: <code>./scripts/lab.sh</code> (generates TLS creds in <code>.env</code>)</li>
                <li>Register softphone — <strong>TLS</strong> <code>127.0.0.1:5061</code>, user/pass from <code>lab/asterisk/generated/credentials.env</code></li>
                <li>Accept the self-signed certificate</li>
                <li>Dial extension <code>1000</code></li>
                <li>Paste IVR phrases below; press DTMF on the softphone when prompted</li>
              </ol>
              <p className="field-hint">
                Suggested paste sequence: <span className="mono">account</span> → <span className="mono">touch tone</span> → <span className="mono">pin</span> → <span className="mono">last four</span> → <span className="mono">balance</span> → <span className="mono">your dollars</span> → <span className="mono">goodbye</span>
              </p>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="target">Target number — local only</label>
            <input
              id="target"
              type="tel"
              value={targetNumber}
              onChange={(e) => setTargetNumber(e.target.value)}
              placeholder={isLabScript ? "Leave empty — use softphone to dial 1000" : undefined}
              required={!isLabScript}
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

  const path = pathFromScript(activeRun.script);

  return wrap(
    <div className="callstate-panel">
      {session.phase === "completed" && session.callEvents && (
        <CallStateBoard
          liveStatus={projectLiveStatus(
            callFromSession(session.sessionId, "local-client", path.id, session.callEvents),
            path
          )}
          path={path}
          label="Callstate"
        />
      )}

      {session.phase === "active" && (
        <MatcherPanel
          script={activeRun.script}
          variables={activeRun.variables}
          sessionId={session.sessionId}
          onCallStateCaptured={handleComplete}
        />
      )}

      {session.phase === "completed" && session.collected && (
        <div className="transcript-preview">
          <h4>Run output</h4>
          <pre>{JSON.stringify(session.collected, null, 2)}</pre>
          <p className="hint">Only a hash of this payload was included in the encrypted callstate sent to the server.</p>
        </div>
      )}

      <div className="callstate-actions">
        {session.phase === "completed" && (
          <button className="btn btn-secondary" onClick={handleExport}>
            Export encrypted callstate
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
  sessionId,
  onCallStateCaptured,
}: {
  script: KnownScript;
  variables: Record<string, string>;
  sessionId: string;
  onCallStateCaptured: (
    collected: Record<string, string>,
    transcriptHash: string,
    callEvents: CallEvent[]
  ) => void;
}) {
  const [run, setRun] = useState<RunState>(initialRunState);
  const [ivrText, setIvrText] = useState("");
  const path = pathFromScript(script);
  const callEvents = runLogToCallEvents(run.log, path);
  const call = callFromSession(sessionId, "local-client", path.id, callEvents);
  const liveStatus = projectLiveStatus(call, path);

  const applyPhraseNow = useCallback(
    (text: string) => {
      setRun((prev) => {
        const result = processPhrase(text, script, variables, prev);
        if (result.shouldComplete) {
          const { collected } = result.state;
          const events = runLogToCallEvents(result.state.log, path);
          const finalEvents = [
            ...events,
            newCallEvent("VERIFICATION_COMPLETE", path.definedSteps[path.definedSteps.length - 1]),
          ];
          void hashCollected(collected).then((hash) =>
            onCallStateCaptured(collected, hash, finalEvents)
          );
        }
        return result.state;
      });
    },
    [script, variables, onCallStateCaptured, path]
  );

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
      <CallStateBoard liveStatus={liveStatus} path={path} label="Live callstate" />

      <div className="run-panel-header">
        <h4>{scriptDisplayName(script)}</h4>
        {!run.completed && (
          <button
            type="button"
            className="btn btn-sm btn-secondary input-mode-placeholder"
            disabled
            title={voiceInputPlaceholder}
          >
            {voiceInputPlaceholder}
          </button>
        )}
      </div>

      <p className="hint">
        Paste what you hear to match the next step. Press DTMF on your phone when prompted
        {VOICE_INPUT_ENABLED ? "" : " (voice input not enabled yet)"}.
      </p>

      {run.pendingDtmf && (
        <div className="dtmf-action-card">
          <span className="dtmf-action-label">Press on your phone</span>
          <code className="dtmf-action-value">{run.pendingDtmf}</code>
          {run.pendingTrigger && (
            <span className="dtmf-action-trigger">After: {run.pendingTrigger}</span>
          )}
          <button type="button" className="btn btn-sm btn-secondary" onClick={dismissDtmf}>
            Sent ✓
          </button>
        </div>
      )}

      {!run.completed && (
        <>
          <div className="form-group">
            <label htmlFor="ivr-phrase">Match phrase</label>
            <textarea
              id="ivr-phrase"
              rows={2}
              value={ivrText}
              onChange={(e) => setIvrText(e.target.value)}
              placeholder="Paste what the IVR said…"
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
        <p className="hint success-hint">Run complete — encrypted callstate submitted.</p>
      )}
    </div>
  );
}
