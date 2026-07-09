import { useCallback, useEffect, useState } from "react";
import { fetchHealth } from "../api";
import { isSpeechRecognitionAvailable } from "../localStt";

export type ApiStatus = "checking" | "online" | "offline";

export interface RuntimeStatus {
  api: ApiStatus;
  apiMode: string | null;
  templates: "loading" | "ready" | "error";
  templateCount: number;
  customCount: number;
  stt: boolean;
  vault: "ready" | "idle";
  lastChecked: Date | null;
  refresh: () => void;
}

const POLL_MS = 30_000;

export function useRuntimeStatus(
  scriptsLoading: boolean,
  scriptsError: string | null,
  bundledCount: number,
  customCount: number
): RuntimeStatus {
  const [api, setApi] = useState<ApiStatus>("checking");
  const [apiMode, setApiMode] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [vault, setVault] = useState<"ready" | "idle">("idle");

  const checkApi = useCallback(async () => {
    setApi("checking");
    try {
      const health = await fetchHealth();
      setApi(health.status === "ok" ? "online" : "offline");
      setApiMode(health.mode ?? null);
    } catch {
      setApi("offline");
      setApiMode(null);
    }
    setLastChecked(new Date());
    setVault(sessionStorage.getItem("pp_status_key") ? "ready" : "idle");
  }, []);

  useEffect(() => {
    void checkApi();
    const id = window.setInterval(() => void checkApi(), POLL_MS);
    return () => window.clearInterval(id);
  }, [checkApi]);

  const templates: RuntimeStatus["templates"] = scriptsLoading
    ? "loading"
    : scriptsError
      ? "error"
      : "ready";

  return {
    api,
    apiMode,
    templates,
    templateCount: bundledCount + customCount,
    customCount,
    stt: isSpeechRecognitionAvailable(),
    vault,
    lastChecked,
    refresh: checkApi,
  };
}
