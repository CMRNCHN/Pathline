import { useRef } from "react";
import {
  Search,
  Settings,
  Radio,
  FileText,
  Pencil,
  Play,
  Sliders,
  LayoutDashboard,
  Upload,
} from "lucide-react";
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
  const { bundledScripts, customScripts, activeId, setActiveId, importScript } =
    useScriptStore();
  const importRef = useRef<HTMLInputElement>(null);

  const openScript = activeId ? getActiveScript(bundledScripts, customScripts, activeId) : undefined;
  const scriptContext =
    view.category === "edit" || view.category === "run" || view.category === "script-settings";

  return (
    <header className="topnav">
      <div className="topnav-row">
        <button
          type="button"
          onClick={() => onNavigate({ category: "library" })}
          className="topnav-brand"
        >
          <Radio className="topnav-brand-icon" />
          PromptPath
        </button>

        <nav className="topnav-links">
          <button
            type="button"
            className={`topnav-link${view.category === "library" ? " topnav-link-active" : ""}`}
            onClick={() => onNavigate({ category: "library" })}
          >
            <FileText size={14} />
            Scripts
          </button>
          <button
            type="button"
            className={`topnav-link${view.category === "system" ? " topnav-link-active" : ""}`}
            onClick={() => onNavigate({ category: "system" })}
          >
            <LayoutDashboard size={14} />
            System
          </button>
        </nav>

        <div className="topnav-spacer" />

        <div className="topnav-search-wrap">
          <Search className="topnav-search-icon" />
          <input
            type="text"
            placeholder="Search scripts…"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="topnav-search"
          />
        </div>

        <button
          type="button"
          onClick={() => importRef.current?.click()}
          className="topnav-ghost"
          title="Import script"
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
              alert("Invalid script JSON");
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

      {openScript && scriptContext && (
        <div className="topnav-context">
          <span className="topnav-context-name">{scriptDisplayName(openScript)}</span>
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
            <button
              type="button"
              className={`topnav-tab${view.category === "script-settings" ? " topnav-tab-active" : ""}`}
              onClick={() => onNavigate({ category: "script-settings", scriptId: activeId })}
            >
              <Sliders size={12} />
              Settings
            </button>
          </nav>
        </div>
      )}
    </header>
  );
}
