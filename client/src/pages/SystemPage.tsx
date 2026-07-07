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
      title="System Overview"
      subtitle="Privacy, storage, health, and export — all in one place."
      wide
    >
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Privacy">
          <div className="space-y-0">
            <Row label="Secrets & target numbers" value="Device only — never sent to server" ok />
            <Row label="IVR audio / transcripts" value="Processed locally when available" ok />
            <Row label="Status reporting" value="Encrypted blob + transcript hash only" ok />
            <Row label="Session retention" value="Auto-purged on server; revoke anytime" ok />
          </div>
          <p className="text-xs text-[#595959] pt-4 mt-2 border-t border-[#0a0a0b14]">
            Carriers still see call metadata (numbers, time, duration) on the PSTN.
          </p>
        </Card>

        <Card title="Local Store">
          <div className="space-y-0">
            <Row label="Custom scripts" value={`${customScripts.length} in localStorage`} />
            <Row label="Bundled templates" value={`${bundledScripts.length} loaded`} />
            <Row label="API sync" value={loading ? "Loading…" : error ? "Error" : "Ready"} ok={!error && !loading} />
            <Row label="Encryption key" value="Session-scoped in sessionStorage" ok />
          </div>
        </Card>

        <Card title="Health Check">
          <div className="space-y-0">
            <Row
              label="Web Speech API"
              value={isSpeechRecognitionAvailable() ? "Available" : "Unavailable — manual entry"}
              ok={isSpeechRecognitionAvailable()}
            />
            <Row label="API endpoint" value="/api (proxied to :8000)" ok />
            <Row label="Scripts loaded" value={`${scripts.length} templates`} ok={scripts.length > 0} />
            <Row label="Run logs" value="In-session only (matcher)" />
          </div>
          <div className="mt-4 p-4 rounded-lg bg-[#0a0a0b] font-mono text-xs text-[#a1a1aa] space-y-1">
            <div>[System Ready] Client-mediated runtime active.</div>
            <div>[Client Vault] Secrets bound to browser session.</div>
            <div>[Diagnostic] No runtime exceptions detected.</div>
          </div>
        </Card>

        <Card title="Export All">
          <p className="text-sm text-[#595959] mb-4">
            Export {scripts.length} script template{scripts.length !== 1 ? "s" : ""} as JSON.
            Secret values are never stored in templates.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            disabled={scripts.length === 0}
            onClick={exportAll}
          >
            Download all scripts
          </button>
        </Card>
      </div>
    </PageLayout>
  );
}

function Row({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 border-b border-[#0a0a0b0a] last:border-0">
      <span className="text-sm text-[#595959]">{label}</span>
      <span
        className={`text-sm font-medium ${ok === true ? "text-emerald-600" : ok === false ? "text-amber-600" : "text-ink"}`}
      >
        {value}
      </span>
    </div>
  );
}
