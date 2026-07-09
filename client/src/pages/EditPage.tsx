import { useEffect } from "react";
import { useScriptStore } from "../store/ScriptStore";
import { isBundledScript } from "../script/selectors";
import { EditForm } from "./edit/EditForm";
import type { AppView } from "../navigation";

interface EditPageProps {
  scriptId: string;
  onNavigate: (view: AppView) => void;
}

export function EditPage({ scriptId, onNavigate }: EditPageProps) {
  const { activeScript, bundledScripts, updateCustom, duplicateToCustom, setActiveId } =
    useScriptStore();

  useEffect(() => {
    setActiveId(scriptId);
  }, [scriptId, setActiveId]);

  if (!activeScript || activeScript.id !== scriptId) {
    return (
      <div className="editor-page">
        <div className="editor-loading">
          <span className="editor-loading-dot" />
          Loading template…
        </div>
      </div>
    );
  }

  const readOnly = isBundledScript(bundledScripts, scriptId);

  return (
    <div className="editor-page">
      <EditForm
        script={activeScript}
        readOnly={readOnly}
        onPatch={(patch) => updateCustom(scriptId, patch)}
        onDuplicate={() => duplicateToCustom(activeScript)}
        onTest={() => onNavigate({ category: "run", scriptId })}
      />
    </div>
  );
}
