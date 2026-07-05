import { useCallback, useEffect, useMemo, useState } from "react";
import type { KnownScript, StatusRule } from "../script/types";
import {
  BUNDLED_SCRIPT_FILES,
  duplicateScript,
  loadActiveScriptId,
  loadCustomScripts,
  newScript,
  saveActiveScriptId,
  saveCustomScripts,
  syncSecrets,
} from "../script/storage";

export function useScriptStore() {
  const [bundled, setBundled] = useState<KnownScript[]>([]);
  const [custom, setCustom] = useState<KnownScript[]>(loadCustomScripts);
  const [activeId, setActiveId] = useState(loadActiveScriptId);
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
            return syncSecrets((await res.json()) as KnownScript);
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

  useEffect(() => {
    if (!activeId && scripts[0]) setActiveId(scripts[0].id);
  }, [scripts, activeId]);

  const activeScript = scripts.find((s) => s.id === activeId) ?? scripts[0];
  const isActiveBundled = activeScript ? bundledIds.has(activeScript.id) : false;

  const updateCustom = useCallback((id: string, patch: Partial<KnownScript>) => {
    setCustom((prev) =>
      prev.map((s) => (s.id === id ? syncSecrets({ ...s, ...patch }) : s))
    );
  }, []);

  const updateActive = useCallback(
    (patch: Partial<KnownScript>) => {
      if (!activeScript) return;
      if (bundledIds.has(activeScript.id)) return;
      updateCustom(activeScript.id, patch);
    },
    [activeScript, bundledIds, updateCustom]
  );

  const addCustom = useCallback((script?: KnownScript) => {
    const next = syncSecrets(script ?? newScript());
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

  const duplicateToCustom = useCallback(
    (source: KnownScript) => {
      const copy = duplicateScript(source);
      setCustom((prev) => [...prev, copy]);
      setActiveId(copy.id);
      return copy;
    },
    []
  );

  const importScript = useCallback((script: KnownScript) => {
    const next = syncSecrets({ ...script, id: script.id || crypto.randomUUID() });
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

  const updateActiveRule = useCallback(
    (ruleIndex: number, patch: Partial<StatusRule>) => {
      if (!activeScript || bundledIds.has(activeScript.id)) return;
      const rules = activeScript.rules.map((r, i) =>
        i === ruleIndex ? { ...r, ...patch } : r
      );
      updateCustom(activeScript.id, { rules });
    },
    [activeScript, bundledIds, updateCustom]
  );

  const addActiveRule = useCallback(
    (rule: StatusRule) => {
      if (!activeScript || bundledIds.has(activeScript.id)) return;
      updateCustom(activeScript.id, { rules: [...activeScript.rules, rule] });
    },
    [activeScript, bundledIds, updateCustom]
  );

  const removeActiveRule = useCallback(
    (ruleIndex: number) => {
      if (!activeScript || bundledIds.has(activeScript.id)) return;
      updateCustom(activeScript.id, {
        rules: activeScript.rules.filter((_, i) => i !== ruleIndex),
      });
    },
    [activeScript, bundledIds, updateCustom]
  );

  const addSecretKey = useCallback(
    (key: string) => {
      if (!activeScript || bundledIds.has(activeScript.id) || !key.trim()) return;
      const k = key.trim();
      if (activeScript.secrets?.includes(k)) return;
      updateCustom(activeScript.id, {
        secrets: [...(activeScript.secrets ?? []), k],
      });
    },
    [activeScript, bundledIds, updateCustom]
  );

  const removeSecretKey = useCallback(
    (key: string) => {
      if (!activeScript || bundledIds.has(activeScript.id)) return;
      updateCustom(activeScript.id, {
        secrets: (activeScript.secrets ?? []).filter((s) => s !== key),
      });
    },
    [activeScript, bundledIds, updateCustom]
  );

  const syncActiveSecrets = useCallback(() => {
    if (!activeScript || bundledIds.has(activeScript.id)) return;
    updateCustom(activeScript.id, syncSecrets(activeScript));
  }, [activeScript, bundledIds, updateCustom]);

  return {
    scripts,
    bundled,
    custom,
    bundledIds,
    loading,
    error,
    activeScript,
    activeId,
    setActiveId,
    isActiveBundled,
    updateActive,
    addCustom,
    removeCustom,
    duplicateToCustom,
    importScript,
    updateActiveRule,
    addActiveRule,
    removeActiveRule,
    addSecretKey,
    removeSecretKey,
    syncActiveSecrets,
  };
}

export type ScriptStore = ReturnType<typeof useScriptStore>;
