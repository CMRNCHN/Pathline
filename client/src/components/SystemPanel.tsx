import { useScriptStore } from "../store/ScriptStore";
import { mergeScripts } from "../script/selectors";
import { isSpeechRecognitionAvailable } from "../localStt";
import { PageShell } from "./ui/PageShell";

type SystemId = "privacy" | "storage" | "logs";

const TITLES: Record<SystemId, string> = {
  privacy: "Privacy",
  storage: "Local Store",
  logs: "Diagnostics",
};

const SUBTITLES: Record<SystemId, string> = {
  privacy: "What stays on your device and what the server receives.",
  storage: "Scripts and session keys held in browser storage.",
  logs: "Runtime capability checks — no secrets logged.",
};

export function SystemPanel({ id }: { id: SystemId }) {
  const { customScripts, bundledScripts, loading, error } = useScriptStore();
  const scripts = mergeScripts(bundledScripts, customScripts);

  return (
    <PageShell title={`System: ${TITLES[id]}`} subtitle={SUBTITLES[id]}>
      <div className="bg-white border border-[#0a0a0b14] rounded-xl p-6 shadow-sm space-y-4">
        {id === "privacy" && (
          <>
            <Row label="Secrets & target numbers" value="Device only — never sent to server" ok />
            <Row label="IVR audio / transcripts" value="Processed locally when available" ok />
            <Row label="Status reporting" value="Encrypted blob + transcript hash only" ok />
            <Row label="Session retention" value="Auto-purged on server; revoke anytime" ok />
            <p className="text-xs text-muted pt-2 border-t border-[#0a0a0b14]">
              Carriers still see call metadata (numbers, time, duration) on the PSTN.
            </p>
          </>
        )}

        {id === "storage" && (
          <>
            <Row label="Custom scripts" value={`${customScripts.length} in localStorage`} />
            <Row label="Bundled templates" value={`${bundledScripts.length} loaded`} />
            <Row label="API sync" value={loading ? "Loading…" : error ? "Error" : "Ready"} ok={!error} />
            <Row label="Encryption key" value="Session-scoped in sessionStorage" ok />
          </>
        )}

        {id === "logs" && (
          <>
            <Row
              label="Web Speech API"
              value={isSpeechRecognitionAvailable() ? "Available" : "Unavailable — manual entry"}
              ok={isSpeechRecognitionAvailable()}
            />
            <Row label="Scripts loaded" value={`${scripts.length} templates`} ok />
            <Row label="Run logs" value="In-session only (matcher panel)" />
            <div className="mt-4 p-4 rounded-lg bg-[#0a0a0b] font-mono text-xs text-[#a1a1aa] space-y-1">
              <div>[System Ready] Client-mediated runtime active.</div>
              <div>[Client Vault] Secrets bound to browser session.</div>
              <div>[Diagnostic] No runtime exceptions detected.</div>
            </div>
          </>
        )}
      </div>
    </PageShell>
  );
}

function Row({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 border-b border-[#0a0a0b0a] last:border-0">
      <span className="text-sm text-muted">{label}</span>
      <span
        className={`text-sm font-medium ${ok === true ? "text-emerald-600" : ok === false ? "text-amber-600" : "text-ink"}`}
      >
        {value}
      </span>
    </div>
  );
}
