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
      subtitle={scriptDisplayName(activeScript)}
    >
      <Card className="max-w-xl space-y-4">
        <dl className="text-sm space-y-2">
          <div className="flex justify-between gap-4">
            <dt className="text-[#595959]">IVR rules</dt>
            <dd className="font-medium">{activeScript.ivrRules.length}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[#595959]">Flow steps</dt>
            <dd className="font-medium">{activeScript.conversationFlow.length}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[#595959]">Schema fields</dt>
            <dd className="font-medium">{activeScript.extractedSchema.length}</dd>
          </div>
        </dl>

        {readOnly && (
          <p className="text-sm text-muted">
            Bundled example — duplicate to edit.
          </p>
        )}

        <div className="flex flex-wrap gap-3 pt-2 border-t border-[#0a0a0b14]">
          <button type="button" className="btn btn-secondary" onClick={() => exportScriptJson(activeScript)}>
            Export template
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
