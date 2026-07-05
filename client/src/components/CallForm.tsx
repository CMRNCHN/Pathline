import { useEffect, useState } from "react";
import type { KnownScript } from "../script/types";
import { useScripts } from "../context/ScriptContext";

interface CallFormProps {
  loadingScripts: boolean;
  scriptError: string | null;
  onStart: (data: {
    script: KnownScript;
    targetNumber: string;
    secrets: Record<string, string>;
  }) => void;
  loading: boolean;
}

export function CallForm({
  loadingScripts,
  scriptError,
  onStart,
  loading,
}: CallFormProps) {
  const { scripts, activeId, setActiveId } = useScripts();
  const [targetNumber, setTargetNumber] = useState("");
  const [secrets, setSecrets] = useState<Record<string, string>>({});

  const script = scripts.find((s) => s.id === activeId) ?? scripts[0];
  const secretKeys = script?.secrets ?? [];

  useEffect(() => {
    if (script?.target) setTargetNumber(script.target);
    else setTargetNumber("");
  }, [script?.id, script?.target]);

  const missingSecrets = secretKeys.filter((k) => !secrets[k]?.trim());

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!script) return;
    onStart({ script, targetNumber, secrets });
  };

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
    <form className="call-form" onSubmit={handleSubmit}>
      <div className="mode-badge">Known script · privacy-preserving status run</div>

      <p className="hint privacy-note">
        Pick a script and fill local secrets. Number stays on device; only encrypted status reaches the server.
      </p>

      <div className="form-group">
        <label htmlFor="script">Script</label>
        <select
          id="script"
          value={script.id}
          onChange={(e) => setActiveId(e.target.value)}
        >
          {scripts.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        {script.description && <p className="field-hint">{script.description}</p>}
      </div>

      {secretKeys.length > 0 && (
        <div className="secrets-section">
          <h3>Local secrets</h3>
          {secretKeys.map((key) => (
            <div key={key} className="form-group">
              <label htmlFor={`secret-${key}`}>{key}</label>
              <input
                id={`secret-${key}`}
                type="password"
                value={secrets[key] ?? ""}
                onChange={(e) => setSecrets((prev) => ({ ...prev, [key]: e.target.value }))}
                placeholder={`Enter ${key}`}
                autoComplete="off"
                required
              />
            </div>
          ))}
        </div>
      )}

      <div className="form-group">
        <label htmlFor="target">Target number (E.164) — local only</label>
        <input
          id="target"
          type="tel"
          placeholder="+15551234567"
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
        {loading ? "Starting…" : "Start status check"}
      </button>
    </form>
  );
}
