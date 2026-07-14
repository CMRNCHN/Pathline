import { useEffect, useMemo, useState } from "react";
import { Clock, Download, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageLayout } from "../components/ui/PageHeader";
import { EmptyState } from "../components/ui/EmptyState";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
} from "../components/ui/table";
import {
  deleteRun,
  loadRunHistory,
  subscribeRunHistory,
  type RunRecord,
} from "../history/runHistory";

type RunFilter = "all" | "completed" | "failed" | "abandoned";

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function outcomeBadgeVariant(outcome: RunRecord["outcome"]) {
  if (outcome === "completed") return "default" as const;
  if (outcome === "failed") return "destructive" as const;
  return "secondary" as const;
}

function exportRun(record: RunRecord): void {
  const blob = new Blob([JSON.stringify(record, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `promptpath-run-${record.runId.slice(0, 8)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export function HistoryPage() {
  return <RunsPage />;
}

export function RunsPage() {
  const [records, setRecords] = useState<RunRecord[]>(() => loadRunHistory());
  const [openId, setOpenId] = useState<string | null>(null);
  const [filter, setFilter] = useState<RunFilter>("all");

  useEffect(() => subscribeRunHistory(() => setRecords(loadRunHistory())), []);

  const filtered = useMemo(() => {
    if (filter === "all") return records;
    return records.filter((r) => r.outcome === filter);
  }, [records, filter]);

  const open = openId ? records.find((r) => r.runId === openId) : undefined;

  const counts = useMemo(
    () => ({
      all: records.length,
      completed: records.filter((r) => r.outcome === "completed").length,
      failed: records.filter((r) => r.outcome === "failed").length,
      abandoned: records.filter((r) => r.outcome === "abandoned").length,
    }),
    [records]
  );

  return (
    <PageLayout
      title="Runs"
      subtitle="Every Path execution on this device — completed, failed, or abandoned."
    >
      <div className="flex flex-wrap gap-2">
        {(
          [
            ["all", "All"],
            ["completed", "Completed"],
            ["failed", "Failed"],
            ["abandoned", "Abandoned"],
          ] as const
        ).map(([key, label]) => (
          <Button
            key={key}
            type="button"
            size="sm"
            variant={filter === key ? "default" : "outline"}
            onClick={() => setFilter(key)}
          >
            {label}
            <Badge variant="secondary" className="ml-1 tabular-nums">
              {counts[key]}
            </Badge>
          </Button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={Clock} title="No Runs in this view">
          {records.length === 0
            ? "Run a Path and its result will appear here."
            : "Try another filter."}
        </EmptyState>
      ) : (
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[minmax(16rem,22rem)_1fr]">
          <Card size="sm">
            <CardContent className="flex flex-col gap-2 pt-0">
              <ul className="m-0 flex list-none flex-col gap-2 p-0">
                {filtered.map((record) => (
                  <li key={record.runId}>
                    <button
                      type="button"
                      onClick={() => setOpenId(record.runId)}
                      className={cn(
                        "flex w-full items-center justify-between gap-3 rounded-lg border px-3.5 py-2.5 text-left transition-colors hover:bg-muted/50",
                        openId === record.runId
                          ? "border-foreground ring-1 ring-foreground/20"
                          : "border-border"
                      )}
                    >
                      <div className="flex min-w-0 flex-col gap-0.5">
                        <span className="truncate text-sm font-semibold">{record.pathName}</span>
                        <span className="text-xs text-muted-foreground">
                          {formatWhen(record.completedAt)}
                        </span>
                      </div>
                      <Badge variant={outcomeBadgeVariant(record.outcome)}>
                        {record.outcome}
                      </Badge>
                    </button>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {open && (
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <CardTitle>{open.pathName}</CardTitle>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Run {open.runId.slice(0, 8)} · {formatWhen(open.completedAt)}
                    </p>
                  </div>
                  <Badge variant={outcomeBadgeVariant(open.outcome)}>{open.outcome}</Badge>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                <div>
                  <h4 className="mb-2 text-sm font-medium">Captured</h4>
                  {Object.keys(open.captured).length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Nothing was captured on this Run.
                    </p>
                  ) : (
                    <Table>
                      <TableBody>
                        {Object.entries(open.captured).map(([key, value]) => (
                          <TableRow key={key}>
                            <TableCell className="font-mono text-muted-foreground">
                              {key}
                            </TableCell>
                            <TableCell className="font-mono">{value}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>
              </CardContent>

              <CardFooter className="gap-2 border-t">
                <Button type="button" variant="outline" size="sm" onClick={() => exportRun(open)}>
                  <Download />
                  Export
                </Button>
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    deleteRun(open.runId);
                    setOpenId(null);
                  }}
                >
                  <Trash2 />
                  Delete
                </Button>
              </CardFooter>
            </Card>
          )}
        </div>
      )}
    </PageLayout>
  );
}
