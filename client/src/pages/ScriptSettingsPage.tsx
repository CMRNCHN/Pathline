import { Copy, Download, Trash2 } from "lucide-react";
import { useScriptStore } from "../store/ScriptStore";
import { isBundledScript } from "../script/selectors";
import type { ScriptDocument } from "../script/types";
import { PageLayout } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { extractOutputRules } from "../script/compile";
import { scriptDisplayName } from "../script/storage";
import type { AppView } from "../navigation";

function exportScriptJson(script: ScriptDocument): void {
  const blob = new Blob([JSON.stringify(script, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const slug = script.setup.name.replace(/\s+/g, "-").toLowerCase() || "script";
  a.download = `${slug}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

interface ScriptSettingsPageProps {
  scriptId: string;
  onNavigate: (view: AppView) => void;
}

export function ScriptSettingsPage({ scriptId, onNavigate }: ScriptSettingsPageProps) {
  const { activeScript, bundledScripts, duplicateToCustom, removeCustom, setActiveId } =
    useScriptStore();

  if (!activeScript || activeScript.id !== scriptId) {
    return (
      <div className="page">
        <p className="hint">Script not found.</p>
      </div>
    );
  }

  const readOnly = isBundledScript(bundledScripts, scriptId);

  const handleDelete = () => {
    if (!confirm("Delete this script permanently?")) return;
    removeCustom(scriptId);
    setActiveId("");
    onNavigate({ category: "library" });
  };

  const handleDuplicate = () => {
    const copy = duplicateToCustom(activeScript);
    onNavigate({ category: "edit", scriptId: copy.id });
  };

  return (
    <PageLayout
      eyebrow="Template"
      title="Script settings"
      subtitle={`${scriptDisplayName(activeScript)} — export, duplicate, or delete this RUN template.`}
    >
      <Card className="script-settings-card">
        <div className="script-settings-stats">
          <StatRow label="Setup fields" value="Name · Target · Description · Timeout" />
          <StatRow label="Runtime variables" value={activeScript.setup.runtimeVariables.length} />
          <StatRow label="Rules" value={activeScript.ivrRules.length} />
          <StatRow label="Collected outputs" value={extractOutputRules(activeScript).length} />
        </div>

        {readOnly && (
          <p className="hint script-settings-note">Bundled example — duplicate to edit.</p>
        )}

        <div className="script-settings-actions">
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => exportScriptJson(activeScript)}>
            <Download size={14} />
            Export
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={handleDuplicate}>
            <Copy size={14} />
            Duplicate
          </button>
          {!readOnly && (
            <button type="button" className="btn btn-danger btn-sm" onClick={handleDelete}>
              <Trash2 size={14} />
              Delete
            </button>
          )}
        </div>
      </Card>
    </PageLayout>
  );
}

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="data-row">
      <span className="data-row-label">{label}</span>
      <span className="data-row-value mono">{value}</span>
    </div>
  );
}
