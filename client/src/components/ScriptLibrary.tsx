import { FileText, Phone, Plus } from "lucide-react";
import { useScriptStore } from "../store/ScriptStore";
import { isBundledScript, mergeScripts } from "../script/selectors";
import { PageShell } from "./ui/PageShell";
import type { AppView } from "./AppSidebar";

interface ScriptLibraryProps {
  onNavigate: (view: AppView) => void;
  searchQuery: string;
}

export function ScriptLibrary({ onNavigate, searchQuery }: ScriptLibraryProps) {
  const { bundledScripts, customScripts, setActiveId, addCustom } = useScriptStore();
  const scripts = mergeScripts(bundledScripts, customScripts);

  const filtered = searchQuery.trim()
    ? scripts.filter((s) => {
        const q = searchQuery.toLowerCase();
        return (
          s.name.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q) ||
          s.tags.some((t) => t.toLowerCase().includes(q))
        );
      })
    : scripts;

  const openScript = (id: string) => {
    setActiveId(id);
    onNavigate({ category: "edit", scriptId: id });
  };

  const handleCreate = () => {
    const created = addCustom();
    onNavigate({ category: "edit", scriptId: created.id });
  };

  return (
    <PageShell
      title="Script Templates"
      subtitle="Author and manage IVR run templates. Runners execute these without editing the flow."
      action={
        <button
          onClick={handleCreate}
          className="flex items-center gap-2 bg-ink text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-surface transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Script
        </button>
      }
    >
      {filtered.length === 0 ? (
        <div className="bg-white border border-[#0a0a0b14] rounded-xl p-12 text-center shadow-sm">
          <FileText className="w-10 h-10 text-muted mx-auto mb-4 opacity-40" />
          <p className="text-muted text-sm">No scripts yet. Create a template to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((script) => (
            <button
              key={script.id}
              type="button"
              onClick={() => openScript(script.id)}
              className="bg-white border border-[#0a0a0b14] p-5 rounded-xl shadow-sm hover:border-[#7d88f150] cursor-pointer transition-all text-left group"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="bg-[#f4f4f5] p-2 rounded-lg group-hover:bg-[#7d88f114] transition-colors">
                  <FileText className="w-5 h-5 text-ink" />
                </div>
                {isBundledScript(bundledScripts, script.id) && (
                  <span className="text-[10px] font-medium text-accent bg-[#7d88f114] px-2 py-1 rounded-full">
                    Example
                  </span>
                )}
              </div>
              <h3 className="font-semibold text-ink mb-1">{script.name || "Untitled"}</h3>
              <p className="text-sm text-muted line-clamp-2 mb-3">
                {script.description || "No description"}
              </p>
              <div className="flex items-center gap-3 text-[11px] text-muted">
                <span>{script.results.length} result field{script.results.length !== 1 ? "s" : ""}</span>
                <span>·</span>
                <span>{script.secrets.length} secret{script.secrets.length !== 1 ? "s" : ""}</span>
              </div>
              <div
                className="mt-4 flex items-center gap-1.5 text-xs font-medium text-accent opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveId(script.id);
                  onNavigate({ category: "run", scriptId: script.id });
                }}
              >
                <Phone className="w-3.5 h-3.5" />
                Run template
              </div>
            </button>
          ))}
        </div>
      )}
    </PageShell>
  );
}
