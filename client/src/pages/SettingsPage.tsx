import { Shield, Activity, HardDrive, Download, Info } from "lucide-react";
import { PageLayout } from "../components/ui/PageHeader";
import { SectionCard } from "../components/ui/SectionCard";
import { useScriptStore } from "../store/ScriptStore";
import { mergeScripts } from "../script/selectors";
import { clearLocalKeys } from "../crypto";
import { ACTIVE_SCRIPT_KEY, CUSTOM_SCRIPTS_KEY } from "../script/storage";
import { clearRunHistory, loadRunHistory } from "../history/runHistory";

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

export function SettingsPage() {
  const { customScripts, bundledScripts, loading, error } = useScriptStore();
  const paths = mergeScripts(bundledScripts, customScripts);
  const runCount = loadRunHistory().length;

  const exportAll = () => {
    const blob = new Blob([JSON.stringify(paths, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "pathline-paths.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearAllLocalData = () => {
    if (!confirm("Delete all Paths, Run History, and local data? This cannot be undone.")) return;
    localStorage.removeItem(CUSTOM_SCRIPTS_KEY);
    localStorage.removeItem(ACTIVE_SCRIPT_KEY);
    clearRunHistory();
    clearLocalKeys();
    window.location.reload();
  };

  return (
    <PageLayout
      title="Settings"
      subtitle="Privacy, health, and local data — everything Pathline keeps on your device."
      wide
    >
      <div className="card-grid">
        <SectionCard title="Privacy" icon={Shield}>
          <DataRow label="Secrets & target numbers" value="Device only" ok />
          <DataRow label="Call audio" value="Processed locally" ok />
          <DataRow label="Status reporting" value="Encrypted blob + hash" ok />
          <DataRow label="Retention" value="Auto-purged; revoke anytime" ok />
          <p className="hint" style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--border)" }}>
            Carriers still see call metadata on the PSTN.
          </p>
        </SectionCard>

        <SectionCard title="Health" icon={Activity}>
          <DataRow label="DTMF input" value="Active — required for a Run" ok />
          <DataRow label="Voice input" value="Planned — not used yet" />
          <DataRow label="API endpoint" value="/api → :8000" ok />
          <DataRow label="Paths loaded" value={`${paths.length}`} ok={paths.length > 0} />
          <DataRow
            label="API sync"
            value={loading ? "Loading…" : error ? "Error" : "Ready"}
            ok={!error && !loading}
          />
        </SectionCard>

        <SectionCard title="Local data" icon={HardDrive}>
          <DataRow label="Your Paths" value={`${customScripts.length} saved`} />
          <DataRow label="Example Paths" value={`${bundledScripts.length} bundled`} />
          <DataRow label="Run History" value={`${runCount} recorded`} />
          <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", marginTop: "1rem" }}>
            <button
              type="button"
              onClick={() => {
                clearLocalKeys();
                alert("Session encryption keys cleared.");
              }}
              className="link-btn"
            >
              Clear encryption keys
            </button>
            <button type="button" onClick={clearAllLocalData} className="link-btn link-btn-danger">
              Clear all local data
            </button>
          </div>
        </SectionCard>

        <SectionCard title="Export all Paths" icon={Download}>
          <p className="hint" style={{ marginBottom: "1rem" }}>
            Download {paths.length} Path{paths.length !== 1 ? "s" : ""} as JSON. Paths never contain Input values.
          </p>
          <button type="button" className="btn btn-primary" disabled={paths.length === 0} onClick={exportAll}>
            Download Paths
          </button>
        </SectionCard>

        <SectionCard title="About" icon={Info}>
          <p className="hint" style={{ margin: 0 }}>
            Pathline · Client-mediated · DTMF Runs · Encrypted Status export
          </p>
        </SectionCard>
      </div>
    </PageLayout>
  );
}
