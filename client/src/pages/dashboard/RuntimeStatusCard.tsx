import { StatusBoard } from "@/components/StatusBoard";
import type { RuntimeStatus } from "@/hooks/useRuntimeStatus";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function RuntimeStatusCard({ status }: { status: RuntimeStatus }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Current status</CardTitle>
      </CardHeader>
      <CardContent>
        <StatusBoard status={status} />
      </CardContent>
    </Card>
  );
}
