import { useEffect } from "react";
import { Pencil, Phone } from "lucide-react";
import { EditForm } from "@/pages/edit/EditForm";
import { RunPage } from "@/pages/RunPage";
import { useScriptStore } from "@/store/ScriptStore";
import { isBundledScript } from "@/script/selectors";
import { scriptDisplayName } from "@/script/storage";
import type { PathDocument } from "@/script/types";
import type { AppView } from "@/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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

interface PathDetailProps {
  pathId: string;
  panel: "edit" | "run";
  onNavigate: (view: AppView) => void;
}

export function PathDetail({ pathId, panel, onNavigate }: PathDetailProps) {
  const { activeScript, bundledScripts, updateCustom, duplicateToCustom, removeCustom, setActiveId } =
    useScriptStore();

  useEffect(() => {
    setActiveId(pathId);
  }, [pathId, setActiveId]);

  if (!activeScript || activeScript.id !== pathId) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Loading Path…
      </div>
    );
  }

  const readOnly = isBundledScript(bundledScripts, pathId);

  const handleDelete = () => {
    if (!confirm(`Delete "${scriptDisplayName(activeScript)}"? This cannot be undone.`)) return;
    removeCustom(pathId);
    onNavigate({ category: "paths" });
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2 border-b pb-3">
        <h2 className="mr-auto min-w-0 truncate text-base font-semibold">
          {scriptDisplayName(activeScript)}
        </h2>
        <Button
          type="button"
          size="sm"
          variant={panel === "edit" ? "default" : "outline"}
          onClick={() => onNavigate({ category: "paths", pathId, panel: "edit" })}
        >
          <Pencil className="size-3.5" />
          Edit
        </Button>
        <Button
          type="button"
          size="sm"
          variant={panel === "run" ? "default" : "outline"}
          onClick={() => onNavigate({ category: "paths", pathId, panel: "run" })}
        >
          <Phone className="size-3.5" />
          Dial
        </Button>
      </div>

      <div className={cn("min-h-0 flex-1 overflow-y-auto", panel === "edit" && "editor-page")}>
        {panel === "edit" ? (
          <EditForm
            script={activeScript}
            readOnly={readOnly}
            onPatch={(patch) => updateCustom(pathId, patch)}
            onDuplicate={() => {
              const copy = duplicateToCustom(activeScript);
              onNavigate({ category: "paths", pathId: copy.id, panel: "edit" });
            }}
            onExport={() => exportPathJson(activeScript)}
            onDelete={readOnly ? undefined : handleDelete}
            onTest={() => onNavigate({ category: "paths", pathId, panel: "run" })}
          />
        ) : (
          <RunPage scriptId={pathId} embedded />
        )}
      </div>
    </div>
  );
}
