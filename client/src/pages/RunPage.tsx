import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Play } from "lucide-react";
import {
  mintToken,
  linkConsentSession,
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
  callFromSession,
  type CallEvent,
} from "../callstate";
import type { Path } from "../script/types";
import { extractOutputRules, extractVariableNames } from "../script/compile";
import { getActiveScript, mergeScripts } from "../script/selectors";
import { scriptDisplayName } from "../script/storage";
import { recordRun, updateRunUpload } from "../history/runHistory";
import { useScriptStore } from "../store/ScriptStore";
import { PageLayout } from "../components/ui/PageHeader";
import { RunStepBar } from "../components/ui/RunStepBar";
import { RunActivePanel } from "../components/run/RunActivePanel";
import { RunConfigureStep } from "../components/run/RunConfigureStep";
import { RunConsentStep } from "../components/run/RunConsentStep";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { RunSession } from "../engine/runSession";
import { isAutomatedTransport, useRunSessionFactory } from "../hooks/useRunSession";

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
        <Badge variant="secondary" className="gap-1">
          <Play size={14} />
          Client-mediated
        </Badge>
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
  const [uploadFailed, setUploadFailed] = useState(false);
  const [pendingUpload, setPendingUpload] = useState<{
    ciphertext: string;
    nonce: string;
    idempotencyKey: string;
  } | null>(null);
  const [userId] = useState(() => generateUserId());

  const [targetNumber, setTargetNumber] = useState("");
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [runSession, setRunSession] = useState<RunSession | null>(null);

  const createRunSession = useRunSessionFactory();
  const automated = useMemo(() => isAutomatedTransport(), []);

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

  useEffect(() => {
    return () => {
      void runSession?.hangup();
    };
  }, [runSession]);

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
      const nextRunSession = createRunSession(script, variables, sessionId);
      setActiveRun({ script, variables });
      setSession({
        sessionId,
        scriptId: script.id,
        scriptName: scriptDisplayName(script),
        targetNumber,
        phase: "active",
        startedAt: new Date().toISOString(),
      });
      setRunSession(nextRunSession);
      setStep("active");
      if (targetNumber.trim()) {
        await nextRunSession.startCall(targetNumber.trim());
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
    const completedAt = new Date().toISOString();
    try {
      const encrypted = await encryptCallStatePayload({
        phase: "completed",
        fields: collected,
        transcript_hash: transcriptHash,
        completed_at: completedAt,
      });
      const upload = {
        ciphertext: encrypted.ciphertext,
        nonce: encrypted.nonce,
        idempotencyKey: `callstate-${session.sessionId}`,
      };
      setPendingUpload(upload);
      // Crash-safe ordering: persist local History, the audit chain, and the
      // exact idempotent retry payload before attempting any network upload.
      await recordRun({
        runId: session.sessionId,
        pathId: session.scriptId,
        pathName: session.scriptName,
        outcome: "completed",
        startedAt: session.startedAt,
        completedAt,
        captured: collected,
        ledgerEvents: callEvents,
        ledgerHead: transcriptHash,
        uploadState: "pending",
        pendingUpload: upload,
      });

      try {
        await submitEncryptedCallState(
          token,
          session.sessionId,
          encrypted.ciphertext,
          encrypted.nonce,
          upload.idempotencyKey
        );
        await updateRunUpload(session.sessionId, "uploaded");
        setUploadFailed(false);
      } catch (uploadError) {
        const message = uploadError instanceof Error ? uploadError.message : "Encrypted upload failed";
        await updateRunUpload(session.sessionId, "failed", message);
        setUploadFailed(true);
        setError(`${message}. The completed Run is saved locally and can be retried.`);
      }

      setSession({ ...session, phase: "completed", collected, callEvents });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save completed Run locally");
    } finally {
      setLoading(false);
    }
  };

  const handleRetryUpload = async () => {
    if (!token || !session?.collected || !pendingUpload) return;
    setLoading(true);
    setError(null);
    try {
      await submitEncryptedCallState(
        token,
        session.sessionId,
        pendingUpload.ciphertext,
        pendingUpload.nonce,
        pendingUpload.idempotencyKey
      );
      await updateRunUpload(session.sessionId, "uploaded");
      setUploadFailed(false);
    } catch (retryError) {
      const message = retryError instanceof Error ? retryError.message : "Encrypted upload retry failed";
      await updateRunUpload(session.sessionId, "failed", message);
      setError(`${message}. The completed Run remains saved locally.`);
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
      a.download = `pathline-export-${session.sessionId.slice(0, 8)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  };

  const handleRevoke = async () => {
    await runSession?.hangup();
    if (token && session) {
      await deleteCallState(token, session.sessionId);
      await revokeToken(token);
    }
    clearLocalKeys();
    setToken(null);
    setSession(null);
    setActiveRun(null);
    setRunSession(null);
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
      <RunConsentStep
        consentChecked={consentChecked}
        onConsentChange={setConsentChecked}
        loading={loading}
        error={error}
        onDecline={() => setError("Consent declined — cannot proceed")}
        onAccept={handleConsent}
      />
    );
  }

  if (step === "configure") {
    if (loadingScripts) {
      return wrap(<p className="text-sm text-muted-foreground">Loading scripts…</p>);
    }

    if (scriptError) {
      return wrap(
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{scriptError}</AlertDescription>
        </Alert>
      );
    }

    if (!script) {
      return wrap(
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">No Workflows yet. Create one from Workflows.</p>
          </CardContent>
        </Card>
      );
    }

    return wrap(
      <RunConfigureStep
        script={script}
        scripts={scripts}
        activeId={activeId}
        onActiveIdChange={setActiveId}
        variableNames={variableNames}
        variables={variables}
        onVariableChange={(name, value) =>
          setVariables((prev) => ({ ...prev, [name]: value }))
        }
        outputFields={outputFields}
        targetNumber={targetNumber}
        onTargetNumberChange={setTargetNumber}
        loading={loading}
        missingVariables={missingVariables}
        error={error}
        onSubmit={handleStart}
      />
    );
  }

  if (!session || !activeRun) return null;

  const path = pathFromScript(activeRun.script);

  return wrap(
    <div className="space-y-4">
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

      {session.phase === "active" && runSession && (
        <RunActivePanel
          runSession={runSession}
          script={activeRun.script}
          sessionId={session.sessionId}
          automated={automated}
          onCallStateCaptured={handleComplete}
        />
      )}

      {session.phase === "completed" && session.collected && (
        <Card>
          <CardContent className="space-y-2 pt-6">
            <h4 className="text-sm font-medium">Captured</h4>
            <pre className="rounded-lg bg-muted p-3 text-xs font-mono overflow-x-auto">
              {JSON.stringify(session.collected, null, 2)}
            </pre>
            <p className="text-xs text-muted-foreground">
              Saved to History on this device. Only a hash of this payload was sent to the server.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap gap-2">
        {session.phase === "completed" && (
          <Button type="button" variant="outline" onClick={handleExport}>
            Export
          </Button>
        )}
        {session.phase === "completed" && uploadFailed && (
          <Button type="button" variant="outline" onClick={() => void handleRetryUpload()} disabled={loading}>
            Retry encrypted upload
          </Button>
        )}
        <Button type="button" variant="destructive" onClick={handleRevoke} disabled={loading}>
          Revoke & delete all
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
