import { useMemo, useRef, useState } from "react";
import {
  Plus,
  Search,
  Settings,
  Activity,
  FileText,
  Database,
  Shield,
  List,
  Pencil,
  Play,
} from "lucide-react";
import { useScriptStore } from "../store/ScriptStore";
import { deriveTags, filterScripts, isBundledScript, mergeScripts } from "../script/selectors";
import { DEFAULT_TAGS } from "../script/storage";
import { SidebarItem, SidebarSection } from "./ui/Sidebar";

export type AppView =
  | { category: "library" }
  | { category: "edit"; scriptId: string }
  | { category: "run"; scriptId: string }
  | { category: "system"; id: "privacy" | "storage" | "logs" }
  | { category: "settings" };

interface AppSidebarProps {
  view: AppView;
  onNavigate: (view: AppView) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

export function AppSidebar({ view, onNavigate, searchQuery, onSearchChange }: AppSidebarProps) {
  const { bundledScripts, customScripts, activeId, setActiveId, addCustom, importScript } =
    useScriptStore();
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const importRef = useRef<HTMLInputElement>(null);

  const scripts = mergeScripts(bundledScripts, customScripts);
  const visibleScripts = useMemo(() => {
    const byTag = filterScripts(scripts, activeTag);
    if (!searchQuery.trim()) return byTag;
    const q = searchQuery.toLowerCase();
    return byTag.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.tags.some((t) => t.toLowerCase().includes(q))
    );
  }, [scripts, activeTag, searchQuery]);

  const tags = [...new Set([...DEFAULT_TAGS, ...deriveTags(scripts)])];

  const handleNewScript = () => {
    const created = addCustom();
    onNavigate({ category: "edit", scriptId: created.id });
  };

  const openScript = (id: string) => {
    setActiveId(id);
    onNavigate({ category: "edit", scriptId: id });
  };

  return (
    <aside className="w-64 shrink-0 bg-ink flex flex-col h-full border-r border-[#1c1c1c]">
      <div className="p-4 space-y-4 shrink-0">
        <div className="flex items-center gap-2 text-white font-semibold text-lg px-2">
          <Activity className="w-5 h-5 text-accent" />
          PromptPath
        </div>

        <button
          onClick={handleNewScript}
          className="w-full bg-white text-ink rounded-md px-4 py-2 text-sm font-medium hover:bg-zinc-200 transition-colors flex items-center justify-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Script
        </button>

        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#71717a]" />
          <input
            type="text"
            placeholder="Search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full bg-surface border border-[#2a2a2a] rounded-md pl-9 pr-3 py-1.5 text-sm text-zinc-200 placeholder:text-[#71717a] focus:outline-none focus:border-[#3f3f46]"
          />
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 space-y-1 pb-4">
        <SidebarSection label="Scripts">
          <SidebarItem
            icon={FileText}
            label="All Scripts"
            isActive={view.category === "library"}
            onClick={() => onNavigate({ category: "library" })}
          />
          {visibleScripts.map((s) => (
            <SidebarItem
              key={s.id}
              icon={isBundledScript(bundledScripts, s.id) ? FileText : Pencil}
              label={s.name || "Untitled"}
              isActive={
                (view.category === "edit" || view.category === "run") && view.scriptId === s.id
              }
              indent={1}
              onClick={() => openScript(s.id)}
            />
          ))}
        </SidebarSection>

        {activeId && (
          <SidebarSection label="Open Script">
            <SidebarItem
              icon={Pencil}
              label="Edit"
              isActive={view.category === "edit" && view.scriptId === activeId}
              indent={1}
              onClick={() => onNavigate({ category: "edit", scriptId: activeId })}
            />
            <SidebarItem
              icon={Play}
              label="Run"
              isActive={view.category === "run" && view.scriptId === activeId}
              indent={1}
              onClick={() => onNavigate({ category: "run", scriptId: activeId })}
            />
          </SidebarSection>
        )}

        {tags.length > 0 && (
          <SidebarSection label="Tags">
            <SidebarItem
              label="All"
              isActive={activeTag === null}
              indent={1}
              onClick={() => setActiveTag(null)}
            />
            {tags.map((tag) => (
              <SidebarItem
                key={tag}
                label={tag}
                isActive={activeTag === tag}
                indent={1}
                onClick={() => setActiveTag(tag)}
              />
            ))}
          </SidebarSection>
        )}

        <SidebarSection label="System">
          <SidebarItem
            icon={Shield}
            label="Privacy"
            isActive={view.category === "system" && view.id === "privacy"}
            indent={1}
            onClick={() => onNavigate({ category: "system", id: "privacy" })}
          />
          <SidebarItem
            icon={Database}
            label="Local Store"
            isActive={view.category === "system" && view.id === "storage"}
            indent={1}
            onClick={() => onNavigate({ category: "system", id: "storage" })}
          />
          <SidebarItem
            icon={List}
            label="Logs"
            isActive={view.category === "system" && view.id === "logs"}
            indent={1}
            onClick={() => onNavigate({ category: "system", id: "logs" })}
          />
        </SidebarSection>
      </nav>

      <div className="p-4 border-t border-[#1c1c1c] shrink-0 space-y-1">
        <button
          type="button"
          onClick={() => importRef.current?.click()}
          className="w-full text-left text-xs text-[#71717a] hover:text-zinc-300 px-3 py-1.5 transition-colors"
        >
          Import script…
        </button>
        <input
          ref={importRef}
          type="file"
          accept="application/json"
          hidden
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            try {
              importScript(JSON.parse(await file.text()));
            } catch {
              alert("Invalid script JSON");
            }
            e.target.value = "";
          }}
        />
        <SidebarItem
          icon={Settings}
          label="Settings"
          isActive={view.category === "settings"}
          onClick={() => onNavigate({ category: "settings" })}
        />
      </div>
    </aside>
  );
}
