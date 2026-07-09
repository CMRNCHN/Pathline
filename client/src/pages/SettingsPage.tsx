import { useEffect, useState } from "react";
import { Palette, Mic, HardDrive, Info } from "lucide-react";
import { PageLayout } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { Toggle } from "../components/ui/Toggle";
import { clearLocalKeys } from "../crypto";
import {
  clearAllPersistence,
  readPreferences,
  savePreferences,
} from "../persistence";

export function SettingsPage() {
  const [autoListen, setAutoListen] = useState(false);

  useEffect(() => {
    void readPreferences().then((prefs) => {
      setAutoListen(prefs.autoListen);
    });
  }, []);

  const persistAutoListen = (value: boolean) => {
    setAutoListen(value);
    void savePreferences({ autoListen: value });
  };

  const clearAllLocalData = () => {
    if (!confirm("Delete all local scripts, run configs, and history? This cannot be undone.")) return;
    void clearAllPersistence().then(() => {
      clearLocalKeys();
      window.location.reload();
    });
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
            Clean ink-on-canvas palette with high-contrast navigation and neutral accents.
          </p>
        </Card>

        <Card title="Run defaults" icon={Mic}>
          <div className="setting-row">
            <div>
              <p className="setting-row-title">Auto-listen on run start</p>
              <p className="setting-row-desc">Enable Web Speech when a run begins</p>
            </div>
            <Toggle checked={autoListen} onChange={persistAutoListen} label="Auto-listen" />
          </div>
        </Card>

        <Card title="Data" icon={HardDrive}>
          <p className="hint" style={{ marginBottom: "0.85rem" }}>
            Scripts, run configs, and history are stored in IndexedDB on this device.
          </p>
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
            PromptPath v1 · Known scripts · Client-mediated · Encrypted status export
          </p>
        </Card>
      </div>
    </PageLayout>
  );
}
