import { useScriptStore } from "../store/ScriptStore";
import { isBundledScript } from "../script/selectors";
import type { ScriptDocument } from "../script/types";
import { PageLayout } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import type { AppView } from "../navigation";

function exportScriptJson(script: ScriptDocument): void {
  const blob = new Blob([JSON.stringify(script, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const slug = script.name.replace(/\s+/g, "-").toLowerCase() || "script";
  a.download = `${slug}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

interface ScriptSettingsPageProps {
  scriptId: string;
  onNavigate: (view: AppView) => void;
}

export function ScriptSettingsPage({ scriptId, onNavigate }: ScriptSettingsPageProps) {
  const { activeScript, bundledScripts, updateCustom, duplicateToCustom, removeCustom, setActiveId } =
    useScriptStore();

  if (!activeScript || activeScript.id !== scriptId) {
    return (
      <div className="flex items-center justify-center h-64 text-muted text-sm">
        Script not found.
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
      title="Script Settings"
      subtitle={activeScript.name || "Untitled script"}
    >
      <Card className="max-w-xl space-y-6">
        <div className="form-group">
          <label htmlFor="settings-target">Target</label>
          <input
            id="settings-target"
            type="tel"
            value={activeScript.target}
            onChange={(e) => updateCustom(scriptId, { target: e.target.value })}
            disabled={readOnly}
          />
        </div>

        <div className="form-group">
          <label htmlFor="settings-timeout">Timeout (seconds)</label>
          <input
            id="settings-timeout"
            type="number"
            value={Math.round(activeScript.timeoutMs / 1000)}
            onChange={(e) =>
              updateCustom(scriptId, { timeoutMs: Number(e.target.value) * 1000 })
            }
            disabled={readOnly}
          />
        </div>

        {readOnly && (
          <p className="text-sm text-muted">
            This is a bundled example script. Duplicate it to edit settings.
          </p>
        )}

        <div className="flex flex-wrap gap-3 pt-2 border-t border-[#0a0a0b14]">
          <button type="button" className="btn btn-secondary" onClick={() => exportScriptJson(activeScript)}>
            Export script
          </button>
          <button type="button" className="btn btn-secondary" onClick={handleDuplicate}>
            Duplicate
          </button>
          {!readOnly && (
            <button type="button" className="btn btn-danger" onClick={handleDelete}>
              Delete script
            </button>
          )}
        </div>
      </Card>
    </PageLayout>
  );
}
