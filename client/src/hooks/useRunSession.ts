import { useMemo } from "react";
import { RunSession } from "@/engine/runSession";
import { createAppTransport, isAutomatedTransport } from "@/transport/createAppTransport";
import type { PathDocument } from "@/script/types";

export function useRunSessionFactory() {
  const transport = useMemo(() => createAppTransport(), []);

  return useMemo(
    () => (path: PathDocument, variables: Record<string, string>, sessionId: string) =>
      new RunSession({
        path,
        variables,
        sessionId,
        transport,
      }),
    [transport],
  );
}

export { isAutomatedTransport };
