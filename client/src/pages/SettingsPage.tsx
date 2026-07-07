import { useState } from "react";
import { PageLayout } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { clearLocalKeys } from "../crypto";
import { ACTIVE_SCRIPT_KEY, CUSTOM_SCRIPTS_KEY } from "../script/storage";

export function SettingsPage() {
  const [autoListen, setAutoListen] = useState(
    () => localStorage.getItem("pp-auto-listen") === "1"
  );

  const persistAutoListen = (value: boolean) => {
    setAutoListen(value);
    localStorage.setItem("pp-auto-listen", value ? "1" : "0");
  };

  const clearAllLocalData = () => {
    if (!confirm("Delete all local scripts and reset app data? This cannot be undone.")) return;
    localStorage.removeItem(CUSTOM_SCRIPTS_KEY);
    localStorage.removeItem(ACTIVE_SCRIPT_KEY);
    clearLocalKeys();
    window.location.reload();
  };

  return (
    <PageLayout title="Settings" subtitle="Theme, defaults, and local data controls.">
      <div className="space-y-6 max-w-lg">
        <Card title="Appearance">
          <p className="text-sm text-[#595959]">
            Light theme with accent <span className="text-accent font-medium">#7D88F1</span>
          </p>
        </Card>

        <Card title="Run defaults">
          <label className="flex items-center justify-between gap-4 cursor-pointer">
            <div>
              <div className="text-sm font-medium text-ink">Auto-listen on run start</div>
              <div className="text-xs text-[#595959] mt-0.5">Enable Web Speech when a run begins</div>
            </div>
            <Toggle checked={autoListen} onChange={persistAutoListen} />
          </label>
        </Card>

        <Card title="Data">
          <button
            type="button"
            onClick={() => {
              clearLocalKeys();
              alert("Session encryption keys cleared.");
            }}
            className="text-sm text-[#595959] hover:text-ink underline mr-4"
          >
            Clear encryption keys
          </button>
          <button
            type="button"
            onClick={clearAllLocalData}
            className="text-sm text-red-600 hover:text-red-700 underline"
          >
            Clear all local data
          </button>
        </Card>

        <Card title="About">
          <p className="text-sm text-[#595959]">
            PromptPath v1 · Known scripts only · Client-mediated · Encrypted status
          </p>
        </Card>
      </div>
    </PageLayout>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="w-10 h-5 rounded-full transition-all relative shrink-0 cursor-pointer"
      style={{ background: checked ? "#7d88f1" : "#d4d4d8" }}
      aria-pressed={checked}
    >
      <span
        className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all shadow-sm"
        style={{ left: checked ? "22px" : "2px" }}
      />
    </button>
  );
}
