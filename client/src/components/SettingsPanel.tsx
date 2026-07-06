import { useState } from "react";
import { PageShell } from "./ui/PageShell";
import { clearLocalKeys } from "../crypto";

export function SettingsPanel() {
  const [autoListen, setAutoListen] = useState(false);

  return (
    <PageShell
      title="Settings"
      subtitle="Device preferences and local security options."
    >
      <div className="space-y-6">
        <section className="bg-white border border-[#0a0a0b14] rounded-xl p-6 shadow-sm">
          <h3 className="font-semibold text-ink mb-4">Run defaults</h3>
          <label className="flex items-center justify-between gap-4 cursor-pointer">
            <div>
              <div className="text-sm font-medium text-ink">Auto-listen on run start</div>
              <div className="text-xs text-muted mt-0.5">Enable Web Speech when a run begins</div>
            </div>
            <Toggle checked={autoListen} onChange={setAutoListen} />
          </label>
        </section>

        <section className="bg-white border border-[#0a0a0b14] rounded-xl p-6 shadow-sm">
          <h3 className="font-semibold text-ink mb-4">Security</h3>
          <label className="flex items-center gap-3 text-sm text-ink cursor-pointer">
            <input type="checkbox" defaultChecked className="rounded border-[#0a0a0b22] accent-ink" />
            Clear encryption keys when revoking a session
          </label>
          <button
            type="button"
            onClick={() => {
              clearLocalKeys();
              alert("Local encryption keys cleared.");
            }}
            className="mt-4 text-sm text-muted hover:text-ink underline"
          >
            Clear local keys now
          </button>
        </section>

        <section className="bg-white border border-[#0a0a0b14] rounded-xl p-6 shadow-sm">
          <h3 className="font-semibold text-ink mb-2">About</h3>
          <p className="text-sm text-muted">
            PromptPath v1 · Known scripts only · Client-mediated · Encrypted status
          </p>
        </section>
      </div>
    </PageShell>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="w-10 h-5 rounded-full transition-all relative shrink-0"
      style={{ background: checked ? "#7d88f1" : "#d4d4d8" }}
    >
      <span
        className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all shadow-sm"
        style={{ left: checked ? "22px" : "2px" }}
      />
    </button>
  );
}
