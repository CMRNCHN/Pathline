import { StatusBoard } from "@/components/StatusBoard";
import type { RuntimeStatus } from "@/hooks/useRuntimeStatus";

export function RuntimeHealthSection({ status }: { status: RuntimeStatus }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-medium">Runtime health</h2>
      <StatusBoard status={status} />
    </section>
  );
}
