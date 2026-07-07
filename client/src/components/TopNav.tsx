import { useRef, type ReactNode } from "react";
import {
  Plus,
  Search,
  Settings,
  Activity,
  FileText,
  Pencil,
  Play,
  Sliders,
  LayoutDashboard,
  Upload,
} from "lucide-react";
import { useScriptStore } from "../store/ScriptStore";
import { getActiveScript } from "../script/selectors";
import { normalizeScript } from "../script/compile";
import type { AppView } from "../navigation";

interface TopNavProps {
  view: AppView;
  onNavigate: (view: AppView) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

function NavLink({
  active,
  onClick,
  children,
}: {
  active?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors cursor-pointer whitespace-nowrap ${
        active
          ? "bg-surface text-white"
          : "text-[#a1a1aa] hover:text-white hover:bg-white/5"
      }`}
    >
      {children}
    </button>
  );
}

export function TopNav({ view, onNavigate, searchQuery, onSearchChange }: TopNavProps) {
  const { bundledScripts, customScripts, activeId, setActiveId, addCustom, importScript } =
    useScriptStore();
  const importRef = useRef<HTMLInputElement>(null);

  const openScript = activeId ? getActiveScript(bundledScripts, customScripts, activeId) : undefined;
  const scriptContext =
    view.category === "edit" || view.category === "run" || view.category === "script-settings";

  const handleNewScript = () => {
    const created = addCustom();
    setActiveId(created.id);
    onNavigate({ category: "edit", scriptId: created.id });
  };

  return (
    <header className="shrink-0 bg-ink border-b border-[#1c1c1c]">
      <div className="flex items-center gap-2 px-4 h-14">
        <button
          type="button"
          onClick={() => onNavigate({ category: "library" })}
          className="flex items-center gap-2 text-white font-semibold mr-2 hover:opacity-90 transition-opacity shrink-0"
        >
          <Activity className="w-5 h-5 text-accent" />
          PromptPath
        </button>

        <nav className="flex items-center gap-1">
          <NavLink
            active={view.category === "library"}
            onClick={() => onNavigate({ category: "library" })}
          >
            <span className="flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" />
              Scripts
            </span>
          </NavLink>
          <NavLink
            active={view.category === "system"}
            onClick={() => onNavigate({ category: "system" })}
          >
            <span className="flex items-center gap-1.5">
              <LayoutDashboard className="w-3.5 h-3.5" />
              System
            </span>
          </NavLink>
        </nav>

        <div className="flex-1 min-w-0" />

        <div className="relative hidden sm:block w-48 lg:w-64 shrink-0">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#71717a] pointer-events-none" />
          <input
            type="text"
            placeholder="Search scripts"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full bg-surface border border-[#2a2a2a] rounded-md pl-9 pr-3 py-1.5 text-sm text-zinc-200 placeholder:text-[#71717a] focus:outline-none focus:border-accent"
          />
        </div>

        <button
          type="button"
          onClick={() => importRef.current?.click()}
          className="hidden sm:flex items-center gap-1.5 text-xs text-[#a1a1aa] hover:text-white px-2 py-1.5 transition-colors cursor-pointer shrink-0"
          title="Import script"
        >
          <Upload className="w-3.5 h-3.5" />
          Import
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
              const raw = JSON.parse(await file.text());
              const next = normalizeScript(raw);
              importScript(raw);
              setActiveId(next.id);
              onNavigate({ category: "edit", scriptId: next.id });
            } catch {
              alert("Invalid script JSON");
            }
            e.target.value = "";
          }}
        />

        <button
          type="button"
          onClick={handleNewScript}
          className="bg-white text-ink rounded-md px-3 py-1.5 text-sm font-medium hover:bg-zinc-200 transition-colors flex items-center gap-1.5 cursor-pointer shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">New</span>
        </button>

        <button
          type="button"
          onClick={() => onNavigate({ category: "settings" })}
          className={`p-2 rounded-md transition-colors cursor-pointer shrink-0 ${
            view.category === "settings"
              ? "bg-surface text-white"
              : "text-[#a1a1aa] hover:text-white hover:bg-white/5"
          }`}
          title="Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>

      {openScript && scriptContext && (
        <div className="flex items-center gap-2 px-4 py-2 border-t border-[#1c1c1c] bg-[#0d0d0e]">
          <span className="text-xs text-[#71717a] truncate max-w-[140px] sm:max-w-xs">
            {openScript.name || "Untitled"}
          </span>
          <span className="text-[#2a2a2a]">|</span>
          <nav className="flex items-center gap-1">
            <NavLink
              active={view.category === "edit"}
              onClick={() => onNavigate({ category: "edit", scriptId: activeId })}
            >
              <span className="flex items-center gap-1.5">
                <Pencil className="w-3.5 h-3.5" />
                Edit
              </span>
            </NavLink>
            <NavLink
              active={view.category === "run"}
              onClick={() => onNavigate({ category: "run", scriptId: activeId })}
            >
              <span className="flex items-center gap-1.5">
                <Play className="w-3.5 h-3.5" />
                Run
              </span>
            </NavLink>
            <NavLink
              active={view.category === "script-settings"}
              onClick={() => onNavigate({ category: "script-settings", scriptId: activeId })}
            >
              <span className="flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5" />
                Settings
              </span>
            </NavLink>
          </nav>
        </div>
      )}
    </header>
  );
}
