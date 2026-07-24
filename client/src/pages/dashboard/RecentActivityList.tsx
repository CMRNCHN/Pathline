import type { RunRecord } from "@/history/runHistory";
import type { AppView } from "@/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

interface RecentActivityListProps {
  recent: RunRecord[];
  onNavigate: (view: AppView) => void;
}

export function RecentActivityList({ recent, onNavigate }: RecentActivityListProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Recent activity</CardTitle>
        <CardDescription>Latest Runs on this device.</CardDescription>
      </CardHeader>
      <CardContent>
        {recent.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No runs yet. Open Path Library and dial a Path.
          </p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {recent.map((record) => (
              <li key={record.runId}>
                <Button
                  type="button"
                  variant="ghost"
                  className="h-auto w-full justify-between gap-3 px-3 py-2"
                  onClick={() =>
                    onNavigate({
                      category: "paths",
                      pathId: record.pathId,
                      panel: "edit",
                    })
                  }
                >
                  <span className="min-w-0 text-left">
                    <span className="block truncate text-sm font-medium">{record.pathName}</span>
                    <span className="block text-xs text-muted-foreground">
                      {formatWhen(record.completedAt)}
                    </span>
                  </span>
                  <Badge
                    variant={
                      record.outcome === "completed"
                        ? "default"
                        : record.outcome === "failed"
                          ? "destructive"
                          : "secondary"
                    }
                  >
                    {record.outcome}
                  </Badge>
                </Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
