import { Copy, Download, Trash2 } from "lucide-react";
import { useScriptStore } from "../store/ScriptStore";
import { isBundledScript } from "../script/selectors";
import type { ScriptDocument } from "../script/types";
import { PageLayout } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
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
      subtitle={scriptDisplayName(activeScript)}
    >
      <Card className="max-w-xl">
        <dl style={{ display: "flex", flexDirection: "column", gap: "0.65rem", marginBottom: "1.25rem" }}>
          <StatRow label="IVR rules" value={activeScript.ivrRules.length} />
          <StatRow label="Flow steps" value={activeScript.conversationFlow.length} />
          <StatRow label="Schema fields" value={activeScript.extractedSchema.length} />
        </dl>

        {readOnly && (
          <p className="hint" style={{ marginBottom: "1rem" }}>
            Bundled example — duplicate to edit.
          </p>
        )}

        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.65rem", paddingTop: "1rem", borderTop: "1px solid var(--border)" }}>
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

function StatRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="data-row">
      <span className="data-row-label">{label}</span>
      <span className="data-row-value mono">{value}</span>
    </div>
  );
}
