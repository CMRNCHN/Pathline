import { useEffect } from "react";
import { useScriptStore } from "../store/ScriptStore";
import { isBundledScript } from "../script/selectors";
import { ScriptEditorView } from "./ScriptEditorView";

interface ScriptEditorProps {
  scriptId: string;
  onTest?: (scriptId: string) => void;
}

export function ScriptEditor({ scriptId, onTest }: ScriptEditorProps) {
  const {
    activeScript,
    bundledScripts,
    updateCustom,
    duplicateToCustom,
    removeCustom,
    setActiveId,
  } = useScriptStore();

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
    <div className="h-full p-6 overflow-hidden flex flex-col">
      <ScriptEditorView
        script={activeScript}
        readOnly={readOnly}
        onPatch={(patch) => updateCustom(scriptId, patch)}
        onDuplicate={() => duplicateToCustom(activeScript)}
        onDelete={() => removeCustom(scriptId)}
        onTest={onTest ? () => onTest(scriptId) : undefined}
      />
    </div>
  );
}
