import { useState } from "react";
import {
  mintToken,
  placeCallLocally,
  submitEncryptedStatus,
  exportStatus,
  deleteStatus,
  revokeToken,
} from "./api";
import { encryptStatusPayload, generateUserId, generateSessionId, clearLocalKeys } from "./crypto";
import type { LocalSession } from "./types";
import type { KnownScript } from "./script/types";
import { ConsentPanel } from "./components/ConsentPanel";
import { CallForm } from "./components/CallForm";
import { ActiveSession } from "./components/ActiveSession";
import { ScriptEditor } from "./components/ScriptEditor";
import { useScripts } from "./context/ScriptContext";

type Step = "consent" | "configure" | "active";
type View = "call" | "scripts";

interface ActiveRun {
  script: KnownScript;
  secrets: Record<string, string>;
}

export default function App() {
  const { loading: loadingScripts, error: scriptError, setActiveId } = useScripts();
  const [view, setView] = useState<View>("call");
  const [step, setStep] = useState<Step>("consent");
  const [token, setToken] = useState<string | null>(null);
  const [session, setSession] = useState<LocalSession | null>(null);
  const [activeRun, setActiveRun] = useState<ActiveRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userId] = useState(() => generateUserId());

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

  const handleStart = async (data: {
    script: KnownScript;
    targetNumber: string;
    secrets: Record<string, string>;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const sessionId = generateSessionId();
      setActiveRun({ script: data.script, secrets: data.secrets });
      setSession({
        sessionId,
        scriptId: data.script.id,
        scriptName: data.script.name,
        targetNumber: data.targetNumber,
        status: "in_progress",
        startedAt: new Date().toISOString(),
      });
      setStep("active");
      setView("call");
      placeCallLocally(data.targetNumber);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async (
    collected: Record<string, string>,
    transcriptHash: string
  ) => {
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

      await submitEncryptedStatus(
        token,
        session.sessionId,
        encrypted.ciphertext,
        encrypted.nonce
      );

      setSession({
        ...session,
        status: "completed",
        collected,
      });
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
  };

  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <span className="logo-icon">◈</span>
          <h1>PromptPath</h1>
        </div>
        <p className="tagline">Client-mediated · privacy by minimization</p>
        {step !== "consent" && (
          <nav className="view-tabs">
            <button
              className={`view-tab ${view === "call" ? "active" : ""}`}
              onClick={() => setView("call")}
            >
              Call
            </button>
            <button
              className={`view-tab ${view === "scripts" ? "active" : ""}`}
              onClick={() => setView("scripts")}
            >
              Scripts
            </button>
          </nav>
        )}
      </header>

      <main className={`main ${view === "scripts" ? "main-wide" : ""}`}>
        {view === "scripts" ? (
          <ScriptEditor
            onTest={(scriptId) => {
              setActiveId(scriptId);
              setView("call");
              if (step === "consent") setStep("configure");
            }}
          />
        ) : (
          <>
            {step === "consent" && (
              <ConsentPanel
                onAccept={handleConsent}
                onDecline={() => setError("Consent declined — cannot proceed")}
              />
            )}

            {step === "configure" && (
              <CallForm
                loadingScripts={loadingScripts}
                scriptError={scriptError}
                onStart={handleStart}
                loading={loading}
              />
            )}

            {step === "active" && session && activeRun && (
              <ActiveSession
                session={session}
                script={activeRun.script}
                secrets={activeRun.secrets}
                onComplete={handleComplete}
                onRevoke={handleRevoke}
                onExport={handleExport}
                loading={loading}
              />
            )}

            {error && <div className="error-banner">{error}</div>}
          </>
        )}
      </main>

      <footer className="footer">
        <p>v1 · Known scripts only · Encrypted status · Auto-purge enabled</p>
      </footer>
    </div>
  );
}
