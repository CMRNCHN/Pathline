import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { initPersistence, saveActiveScriptId, saveCustomScripts } from "../persistence";
import type { PathDocument } from "../script/types";
import { normalizeScript } from "../script/compile";
import { getActiveScript, isBundledScript } from "../script/selectors";
import {
  BUNDLED_SCRIPT_FILES,
  duplicateScript,
  newScript,
} from "../script/storage";

export interface ScriptStore {
  bundledScripts: PathDocument[];
  customScripts: PathDocument[];
  activeId: string;
  activeScript: PathDocument | undefined;
  loading: boolean;
  error: string | null;
  persistReady: boolean;
  setActiveId: (id: string) => void;
  updateCustom: (id: string, patch: Partial<PathDocument>) => void;
  addCustom: (script?: PathDocument) => PathDocument;
  removeCustom: (id: string) => void;
  duplicateToCustom: (source: PathDocument) => PathDocument;
  importScript: (raw: unknown) => void;
}

const ScriptStoreContext = createContext<ScriptStore | null>(null);

function useScriptStoreState(): ScriptStore {
  const [bundledScripts, setBundledScripts] = useState<PathDocument[]>([]);
  const [customScripts, setCustomScripts] = useState<PathDocument[]>([]);
  const [activeId, setActiveId] = useState("");
  const [persistReady, setPersistReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const bundledRef = useRef(bundledScripts);

  useEffect(() => {
    bundledRef.current = bundledScripts;
  }, [bundledScripts]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const persisted = await initPersistence();
        if (cancelled) return;
        setCustomScripts(persisted.customScripts);
        setActiveId(persisted.activeScriptId);
        setPersistReady(true);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load local storage");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const results = await Promise.allSettled(
          BUNDLED_SCRIPT_FILES.map(async (file) => {
            const res = await fetch(`/scripts/${file}`);
            if (!res.ok) throw new Error(`Failed to load ${file}`);
            return normalizeScript(await res.json());
          })
        );
        const loaded = results
          .filter((r): r is PromiseFulfilledResult<PathDocument> => r.status === "fulfilled")
          .map((r) => r.value);
        if (!cancelled) {
          setBundledScripts(loaded);
          if (loaded.length === 0 && results.length > 0) {
            setError("Failed to load bundled Workflows");
          }
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load bundled Workflows");
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
    if (!persistReady) return;
    void saveCustomScripts(customScripts);
  }, [customScripts, persistReady]);

  useEffect(() => {
    if (!persistReady) return;
    void saveActiveScriptId(activeId);
  }, [activeId, persistReady]);

  useEffect(() => {
    if (activeId) return;
    const first = bundledScripts[0] ?? customScripts[0];
    if (first) setActiveId(first.id);
  }, [activeId, bundledScripts, customScripts]);

  const activeScript = getActiveScript(bundledScripts, customScripts, activeId);

  const updateCustom = useCallback((id: string, patch: Partial<PathDocument>) => {
    setCustomScripts((prev) => prev.map((s) => (s.id === id ? { ...s, ...patch } : s)));
  }, []);

  const addCustom = useCallback((script?: PathDocument) => {
    const next = script ?? newScript();
    setCustomScripts((prev) => [...prev, next]);
    setActiveId(next.id);
    return next;
  }, []);

  const removeCustom = useCallback(
    (id: string) => {
      if (isBundledScript(bundledRef.current, id)) return;
      setCustomScripts((prev) => prev.filter((s) => s.id !== id));
      if (activeId === id) setActiveId("");
    },
    [activeId]
  );

  const duplicateToCustom = useCallback((source: PathDocument) => {
    const copy = duplicateScript(source);
    setCustomScripts((prev) => [...prev, copy]);
    setActiveId(copy.id);
    return copy;
  }, []);

  const importScript = useCallback((raw: unknown) => {
    const next = normalizeScript(raw);
    if (!next.id) next.id = crypto.randomUUID();
    setCustomScripts((prev) => {
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

  return {
    bundledScripts,
    customScripts,
    activeId,
    activeScript,
    loading,
    error,
    persistReady,
    setActiveId,
    updateCustom,
    addCustom,
    removeCustom,
    duplicateToCustom,
    importScript,
  };
}

export function ScriptStoreProvider({ children }: { children: ReactNode }) {
  const store = useScriptStoreState();
  return <ScriptStoreContext.Provider value={store}>{children}</ScriptStoreContext.Provider>;
}

export function useScriptStore(): ScriptStore {
  const store = useContext(ScriptStoreContext);
  if (!store) throw new Error("useScriptStore must be used within ScriptStoreProvider");
  return store;
}
