import { createContext, useContext, type ReactNode } from "react";
import { useScriptStore, type ScriptStore } from "../hooks/useScriptStore";

const ScriptContext = createContext<ScriptStore | null>(null);

export function ScriptProvider({ children }: { children: ReactNode }) {
  const store = useScriptStore();
  return <ScriptContext.Provider value={store}>{children}</ScriptContext.Provider>;
}

export function useScripts(): ScriptStore {
  const ctx = useContext(ScriptContext);
  if (!ctx) throw new Error("useScripts must be used within ScriptProvider");
  return ctx;
}
