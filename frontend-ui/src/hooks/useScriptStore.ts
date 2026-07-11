import { useCallback, useEffect, useMemo, useState } from "react";
import type { ScriptDocument } from "../script/types";
import { normalizeScript } from "../script/compile";
import {
  BUNDLED_SCRIPT_FILES,
  duplicateScript,
  inferTags,
  loadActiveScriptId,
  loadCustomScripts,
  newScript,
  saveActiveScriptId,
  saveCustomScripts,
} from "../script/storage";

export function useScriptStore() {
  const [bundled, setBundled] = useState<ScriptDocument[]>([]);
  const [custom, setCustom] = useState<ScriptDocument[]>(() =>
    loadCustomScripts().map((s) => normalizeScript(s))
  );
  const [activeId, setActiveId] = useState(loadActiveScriptId);
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const loaded = await Promise.all(
          BUNDLED_SCRIPT_FILES.map(async (file) => {
            const res = await fetch(`/scripts/${file}`);
            if (!res.ok) throw new Error(`Failed to load ${file}`);
            const doc = normalizeScript(await res.json());
            return { ...doc, tags: doc.tags.length ? doc.tags : inferTags(doc) };
          })
        );
        if (!cancelled) setBundled(loaded);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load bundled scripts");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    saveCustomScripts(custom);
  }, [custom]);

  useEffect(() => {
    saveActiveScriptId(activeId);
  }, [activeId]);

  const bundledIds = useMemo(() => new Set(bundled.map((s) => s.id)), [bundled]);
  const scripts = useMemo(() => [...bundled, ...custom], [bundled, custom]);

  const filteredScripts = useMemo(() => {
    if (!activeTag) return scripts;
    return scripts.filter((s) =>
      s.tags.some((t) => t.toLowerCase() === activeTag.toLowerCase())
    );
  }, [scripts, activeTag]);

  useEffect(() => {
    if (!activeId && scripts[0]) setActiveId(scripts[0].id);
  }, [scripts, activeId]);

  const activeScript = scripts.find((s) => s.id === activeId) ?? scripts[0];
  const isActiveBundled = activeScript ? bundledIds.has(activeScript.id) : false;

  const updateCustom = useCallback((id: string, patch: Partial<ScriptDocument>) => {
    setCustom((prev) =>
      prev.map((s) => (s.id === id ? { ...s, ...patch } : s))
    );
  }, []);

  const updateActive = useCallback(
    (patch: Partial<ScriptDocument>) => {
      if (!activeScript || bundledIds.has(activeScript.id)) return;
      updateCustom(activeScript.id, patch);
    },
    [activeScript, bundledIds, updateCustom]
  );

  const addCustom = useCallback((script?: ScriptDocument) => {
    const next = script ?? newScript();
    setCustom((prev) => [...prev, next]);
    setActiveId(next.id);
    return next;
  }, []);

  const removeCustom = useCallback(
    (id: string) => {
      if (bundledIds.has(id)) return;
      setCustom((prev) => prev.filter((s) => s.id !== id));
      if (activeId === id) setActiveId("");
    },
    [activeId, bundledIds]
  );

  const duplicateToCustom = useCallback((source: ScriptDocument) => {
    const copy = duplicateScript(source);
    setCustom((prev) => [...prev, copy]);
    setActiveId(copy.id);
    return copy;
  }, []);

  const importScript = useCallback((raw: unknown) => {
    const next = normalizeScript(raw);
    if (!next.id) next.id = crypto.randomUUID();
    setCustom((prev) => {
      const idx = prev.findIndex((s) => s.id === next.id);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = next;
        return updated;
      }
      return [...prev, next];
    });
    setActiveId(next.id);
  }, []);

  const allTags = useMemo(() => {
    const tags = new Set<string>();
    for (const s of scripts) {
      for (const t of s.tags) tags.add(t);
    }
    return [...tags].sort();
  }, [scripts]);

  return {
    scripts,
    filteredScripts,
    bundled,
    custom,
    bundledIds,
    loading,
    error,
    activeScript,
    activeId,
    setActiveId,
    activeTag,
    setActiveTag,
    allTags,
    isActiveBundled,
    updateActive,
    addCustom,
    removeCustom,
    duplicateToCustom,
    importScript,
  };
}

export type ScriptStore = ReturnType<typeof useScriptStore>;
