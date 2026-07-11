import { Search, Settings, Radio, GitBranch, Clock, Pencil, Play, Upload } from "lucide-react";
import { useRef } from "react";
import { useScriptStore } from "../store/ScriptStore";
import { getActiveScript } from "../script/selectors";
import { scriptDisplayName } from "../script/storage";
import { normalizeScript } from "../script/compile";
import type { AppView } from "../navigation";

interface TopNavProps {
  view: AppView;
  onNavigate: (view: AppView) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

export function TopNav({ view, onNavigate, searchQuery, onSearchChange }: TopNavProps) {
  const { bundledScripts, customScripts, activeId, setActiveId, importScript } = useScriptStore();
  const importRef = useRef<HTMLInputElement>(null);

  const openPath = activeId ? getActiveScript(bundledScripts, customScripts, activeId) : undefined;
  const pathContext = view.category === "edit" || view.category === "run";

  return (
    <header className="topnav">
      <div className="topnav-row">
        <button
          type="button"
          onClick={() => onNavigate({ category: "paths" })}
          className="topnav-brand"
        >
          <Radio className="topnav-brand-icon" />
          Pathline
        </button>

        <nav className="topnav-links">
          <button
            type="button"
            className={`topnav-link${view.category === "paths" ? " topnav-link-active" : ""}`}
            onClick={() => onNavigate({ category: "paths" })}
          >
            <GitBranch size={14} />
            Paths
          </button>
          <button
            type="button"
            className={`topnav-link${view.category === "history" ? " topnav-link-active" : ""}`}
            onClick={() => onNavigate({ category: "history" })}
          >
            <Clock size={14} />
            History
          </button>
        </nav>

        <div className="topnav-spacer" />

        {view.category === "paths" && (
          <div className="topnav-search-wrap">
            <Search className="topnav-search-icon" />
            <input
              type="text"
              placeholder="Search paths…"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="topnav-search"
            />
          </div>
        )}

        <button
          type="button"
          onClick={() => importRef.current?.click()}
          className="topnav-ghost"
          title="Import a Path"
        >
          <Upload size={14} />
          <span>Import</span>
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
              alert("Invalid Path file");
            }
            e.target.value = "";
          }}
        />

        <button
          type="button"
          onClick={() => onNavigate({ category: "settings" })}
          className={`topnav-icon-btn${view.category === "settings" ? " topnav-icon-btn-active" : ""}`}
          title="Settings"
        >
          <Settings size={16} />
        </button>
      </div>

      {openPath && pathContext && (
        <div className="topnav-context">
          <span className="topnav-context-name">{scriptDisplayName(openPath)}</span>
          <span className="topnav-context-divider" />
          <nav className="topnav-context-tabs">
            <button
              type="button"
              className={`topnav-tab${view.category === "edit" ? " topnav-tab-active" : ""}`}
              onClick={() => onNavigate({ category: "edit", scriptId: activeId })}
            >
              <Pencil size={12} />
              Edit
            </button>
            <button
              type="button"
              className={`topnav-tab${view.category === "run" ? " topnav-tab-active" : ""}`}
              onClick={() => onNavigate({ category: "run", scriptId: activeId })}
            >
              <Play size={12} />
              Run
            </button>
          </nav>
        </div>
      )}
    </header>
  );
}
