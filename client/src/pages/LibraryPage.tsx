import { useMemo } from "react";
import { FileText, Phone, Plus } from "lucide-react";
import { useScriptStore } from "../store/ScriptStore";
import { isBundledScript, mergeScripts } from "../script/selectors";
import { PageLayout } from "../components/ui/PageHeader";
import { scriptDisplayName } from "../script/storage";
import type { AppView } from "../navigation";

interface LibraryPageProps {
  onNavigate: (view: AppView) => void;
  searchQuery: string;
}

export function LibraryPage({ onNavigate, searchQuery }: LibraryPageProps) {
  const { bundledScripts, customScripts, setActiveId, addCustom } = useScriptStore();

  const scripts = mergeScripts(bundledScripts, customScripts);

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return scripts;
    const q = searchQuery.toLowerCase();
    return scripts.filter(
      (s) =>
        s.setup.name.toLowerCase().includes(q) ||
        s.setup.description.toLowerCase().includes(q)
    );
  }, [scripts, searchQuery]);

  const openScript = (id: string) => {
    setActiveId(id);
    onNavigate({ category: "edit", scriptId: id });
  };

  const handleCreate = () => {
    const created = addCustom();
    setActiveId(created.id);
    onNavigate({ category: "edit", scriptId: created.id });
  };

  return (
    <PageLayout
      title="All Scripts"
      subtitle="Templates for IVR runs. Select one to edit, configure, or execute."
      action={
        <button
          type="button"
          onClick={handleCreate}
          className="flex items-center gap-2 bg-ink text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-surface transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          Create Script
        </button>
      }
    >
      {filtered.length === 0 ? (
        <div className="bg-white border border-[#0a0a0b14] rounded-xl p-12 text-center shadow-sm">
          <FileText className="w-10 h-10 text-[#595959] mx-auto mb-4 opacity-40" />
          <p className="text-[#595959] text-sm">
            {scripts.length === 0
              ? "No scripts yet. Create a template to get started."
              : "No scripts match your search."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((script) => (
            <div
              key={script.id}
              className="bg-white border border-[#0a0a0b14] p-5 rounded-xl shadow-sm hover:border-[#7d88f150] transition-all text-left"
            >
              <button type="button" onClick={() => openScript(script.id)} className="w-full text-left cursor-pointer">
                <div className="flex items-center justify-between mb-4">
                  <div className="bg-[#f4f4f5] p-2 rounded-lg">
                    <FileText className="w-5 h-5 text-ink" />
                  </div>
                  {isBundledScript(bundledScripts, script.id) && (
                    <span className="text-[10px] font-medium text-accent bg-[#7d88f114] px-2 py-1 rounded-full">
                      Example
                    </span>
                  )}
                </div>
                <h3 className="font-semibold text-ink mb-1">{scriptDisplayName(script)}</h3>
                <p className="text-sm text-[#595959] line-clamp-2 mb-3">
                  {script.setup.description || "No description"}
                </p>
                <div className="flex items-center gap-3 text-[11px] text-[#595959]">
                  <span>{script.extractedSchema.length} field{script.extractedSchema.length !== 1 ? "s" : ""}</span>
                  <span>·</span>
                  <span>{script.ivrRules.length} rule{script.ivrRules.length !== 1 ? "s" : ""}</span>
                </div>
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveId(script.id);
                  onNavigate({ category: "run", scriptId: script.id });
                }}
                className="mt-4 flex items-center gap-1.5 text-xs font-medium text-accent hover:underline cursor-pointer"
              >
                <Phone className="w-3.5 h-3.5" />
                Run template
              </button>
            </div>
          ))}
        </div>
      )}
    </PageLayout>
  );
}
