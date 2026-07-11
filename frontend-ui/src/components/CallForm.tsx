import { useEffect, useState } from "react";
import type { KnownScript } from "../script/types";
import { requiredSecretNames } from "../script/compile";
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

  const secretFields = (() => {
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
  })();

  useEffect(() => {
    if (script?.target) setTargetNumber(script.target);
    else setTargetNumber("");
  }, [script?.id, script?.target]);

  const missingSecrets = secretFields.filter((s) => s.required && !secrets[s.name]?.trim());

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
      <div className="mode-badge">{script.name}</div>

      <p className="hint privacy-note">
        This script needs a few values from you. They stay on your device.
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
          placeholder=""
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
  );
}
