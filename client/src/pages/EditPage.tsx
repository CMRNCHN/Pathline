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
      <div className="flex items-center justify-center h-full text-muted text-sm">
        Loading script…
      </div>
    );
  }

  const readOnly = isBundledScript(bundledScripts, scriptId);

  return (
    <div className="p-6 max-w-5xl mx-auto">
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
