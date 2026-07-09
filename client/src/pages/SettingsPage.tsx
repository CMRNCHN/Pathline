import { Palette, Hash, HardDrive, Info } from "lucide-react";
import { PageLayout } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { clearLocalKeys } from "../crypto";
import { ACTIVE_SCRIPT_KEY, CUSTOM_SCRIPTS_KEY } from "../script/storage";

export function SettingsPage() {
  const clearAllLocalData = () => {
    if (!confirm("Delete all local scripts and reset app data? This cannot be undone.")) return;
    localStorage.removeItem(CUSTOM_SCRIPTS_KEY);
    localStorage.removeItem(ACTIVE_SCRIPT_KEY);
    localStorage.removeItem("pp-auto-listen");
    clearLocalKeys();
    window.location.reload();
  };

  return (
    <PageLayout
      eyebrow="Preferences"
      title="Settings"
      subtitle="Appearance, run defaults, and local data controls."
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem", maxWidth: "32rem" }}>
        <Card title="Appearance" icon={Palette}>
          <p className="hint">
            Light canvas with ink navigation and accent{" "}
            <span className="mono" style={{ color: "var(--accent)", fontWeight: 600 }}>#7D88F1</span>
          </p>
        </Card>

        <Card title="Run input" icon={Hash}>
          <p className="hint" style={{ margin: 0 }}>
            v1 runs use <strong>DTMF keypad</strong> only — press tones on your phone or softphone when
            prompted. Paste IVR phrases in the run panel to advance matching; voice input is not used.
          </p>
        </Card>

        <Card title="Data" icon={HardDrive}>
          <button
            type="button"
            onClick={() => {
              clearLocalKeys();
              alert("Session encryption keys cleared.");
            }}
            className="link-btn"
            style={{ marginRight: "1rem" }}
          >
            Clear encryption keys
          </button>
          <button type="button" onClick={clearAllLocalData} className="link-btn link-btn-danger">
            Clear all local data
          </button>
        </Card>

        <Card title="About" icon={Info}>
          <p className="hint" style={{ margin: 0 }}>
            PromptPath v1 · Known scripts · Client-mediated · DTMF · Encrypted status export
          </p>
        </Card>
      </div>
    </PageLayout>
  );
}
