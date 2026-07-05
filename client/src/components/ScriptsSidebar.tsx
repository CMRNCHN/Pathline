import { useRef } from "react";
import { useScripts } from "../context/ScriptContext";
import { DEFAULT_TAGS } from "../script/storage";

interface ScriptsSidebarProps {
  onImport: (raw: unknown) => void;
}

export function ScriptsSidebar({ onImport }: ScriptsSidebarProps) {
  const {
    filteredScripts,
    scripts,
    activeId,
    setActiveId,
    activeTag,
    setActiveTag,
    allTags,
    bundledIds,
    addCustom,
  } = useScripts();

  const importRef = useRef<HTMLInputElement>(null);
  const tags = [...new Set([...DEFAULT_TAGS, ...allTags])];

  const handleImportFile = async (file: File) => {
    try {
      onImport(JSON.parse(await file.text()));
    } catch {
      alert("Invalid script JSON");
    }
  };

  return (
    <aside className="script-sidebar">
      <div className="sidebar-head">
        <h3>Scripts</h3>
        <button className="btn btn-sm btn-secondary" onClick={() => addCustom()} title="New script">
          +
        </button>
      </div>

      <div className="tag-filters">
        <button
          className={`tag-chip ${activeTag === null ? "active" : ""}`}
          onClick={() => setActiveTag(null)}
        >
          All
        </button>
        {tags.map((tag) => (
          <button
            key={tag}
            className={`tag-chip ${activeTag === tag ? "active" : ""}`}
            onClick={() => setActiveTag(tag)}
          >
            {tag}
          </button>
        ))}
      </div>

      <ul className="sidebar-list">
        {(activeTag ? filteredScripts : scripts).map((s) => (
          <li key={s.id}>
            <button
              className={`sidebar-item ${s.id === activeId ? "active" : ""}`}
              onClick={() => setActiveId(s.id)}
            >
              {bundledIds.has(s.id) ? "◆ " : ""}{s.name}
            </button>
          </li>
        ))}
      </ul>

      <div className="sidebar-footer">
        <button className="btn btn-secondary btn-sm btn-full" onClick={() => importRef.current?.click()}>
          Import script…
        </button>
        <input
          ref={importRef}
          type="file"
          accept="application/json"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleImportFile(file);
            e.target.value = "";
          }}
        />
      </div>
    </aside>
  );
}
