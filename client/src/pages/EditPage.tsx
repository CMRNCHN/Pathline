import { useEffect } from "react";
import { useScriptStore } from "../store/ScriptStore";
import { isBundledScript } from "../script/selectors";
import { scriptDisplayName } from "../script/storage";
import type { PathDocument } from "../script/types";
import { EditForm } from "./edit/EditForm";
import type { AppView } from "../navigation";

function exportPathJson(path: PathDocument): void {
  const blob = new Blob([JSON.stringify(path, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const slug = path.setup.name.replace(/\s+/g, "-").toLowerCase() || "path";
  a.href = url;
  a.download = `${slug}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

interface EditPageProps {
  scriptId: string;
  onNavigate: (view: AppView) => void;
}

export function EditPage({ scriptId, onNavigate }: EditPageProps) {
  const { activeScript, bundledScripts, updateCustom, duplicateToCustom, removeCustom, setActiveId } =
    useScriptStore();

  useEffect(() => {
    setActiveId(scriptId);
  }, [scriptId, setActiveId]);

  if (!activeScript || activeScript.id !== scriptId) {
    return (
      <div className="flex items-center justify-center h-full text-muted text-sm">
        Loading Path…
      </div>
    );
  }

  const readOnly = isBundledScript(bundledScripts, scriptId);

  const handleDelete = () => {
    if (!confirm(`Delete "${scriptDisplayName(activeScript)}"? This cannot be undone.`)) return;
    removeCustom(scriptId);
    onNavigate({ category: "paths" });
  };

  return (
    <div className="editor-page">
      <EditForm
        script={activeScript}
        readOnly={readOnly}
        onPatch={(patch) => updateCustom(scriptId, patch)}
        onDuplicate={() => {
          const copy = duplicateToCustom(activeScript);
          onNavigate({ category: "edit", scriptId: copy.id });
        }}
        onExport={() => exportPathJson(activeScript)}
        onDelete={readOnly ? undefined : handleDelete}
        onTest={() => onNavigate({ category: "run", scriptId })}
      />
    </div>
  );
}
