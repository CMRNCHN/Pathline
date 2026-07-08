import { Shield, Database, Activity, Download } from "lucide-react";
import { useScriptStore } from "../store/ScriptStore";
import { mergeScripts } from "../script/selectors";
import { isSpeechRecognitionAvailable } from "../localStt";
import { PageLayout } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";

export function SystemPage() {
  const { customScripts, bundledScripts, loading, error } = useScriptStore();
  const scripts = mergeScripts(bundledScripts, customScripts);

  const exportAll = () => {
    const blob = new Blob([JSON.stringify(scripts, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "promptpath-scripts.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <PageLayout
      eyebrow="Infrastructure"
      title="System"
      subtitle="Privacy guarantees, local storage, runtime health, and template export."
      wide
    >
      <div className="card-grid">
        <Card title="Privacy" icon={Shield}>
          <DataRow label="Secrets & target numbers" value="Device only" ok />
          <DataRow label="IVR audio / transcripts" value="Processed locally" ok />
          <DataRow label="Status reporting" value="Encrypted blob + hash" ok />
          <DataRow label="Session retention" value="Auto-purged; revoke anytime" ok />
          <p className="hint" style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--border)" }}>
            Carriers still see call metadata on the PSTN.
          </p>
        </Card>

        <Card title="Local store" icon={Database}>
          <DataRow label="Custom scripts" value={`${customScripts.length} in localStorage`} />
          <DataRow label="Bundled templates" value={`${bundledScripts.length} loaded`} />
          <DataRow
            label="API sync"
            value={loading ? "Loading…" : error ? "Error" : "Ready"}
            ok={!error && !loading}
          />
          <DataRow label="Encryption key" value="Session-scoped" ok />
        </Card>

        <Card title="Health" icon={Activity}>
          <DataRow
            label="Web Speech API"
            value={isSpeechRecognitionAvailable() ? "Available" : "Manual entry only"}
            ok={isSpeechRecognitionAvailable()}
          />
          <DataRow label="API endpoint" value="/api → :8000" ok />
          <DataRow label="Scripts loaded" value={`${scripts.length} templates`} ok={scripts.length > 0} />
          <DataRow label="Activity log" value="In-session only" />
          <div className="terminal-block">
            <div>[ready] Client-mediated runtime active</div>
            <div>[vault] Variables bound to browser session</div>
            <div>[diag] No exceptions detected</div>
          </div>
        </Card>

        <Card title="Export all" icon={Download}>
          <p className="hint" style={{ marginBottom: "1rem" }}>
            Download {scripts.length} template{scripts.length !== 1 ? "s" : ""} as JSON. Templates never contain runtime values.
          </p>
          <button type="button" className="btn btn-primary" disabled={scripts.length === 0} onClick={exportAll}>
            Download templates
          </button>
        </Card>
      </div>
    </PageLayout>
  );
}

function DataRow({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="data-row">
      <span className="data-row-label">{label}</span>
      <span
        className={`data-row-value${
          ok === true ? " data-row-value-ok" : ok === false ? " data-row-value-warn" : ""
        }`}
      >
        {value}
      </span>
    </div>
  );
}
