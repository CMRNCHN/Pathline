import { useEffect, useState } from "react";
import { Clock, Download, Trash2 } from "lucide-react";
import { PageLayout } from "../components/ui/PageHeader";
import { EmptyState } from "../components/ui/EmptyState";
import { Badge } from "../components/ui/Badge";
import {
  deleteRun,
  loadRunHistory,
  subscribeRunHistory,
  type RunRecord,
} from "../history/runHistory";

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function outcomeVariant(outcome: RunRecord["outcome"]) {
  if (outcome === "completed") return "success" as const;
  if (outcome === "failed") return "warn" as const;
  return "muted" as const;
}

function exportRun(record: RunRecord): void {
  const blob = new Blob([JSON.stringify(record, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `pathline-run-${record.runId.slice(0, 8)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export function HistoryPage() {
  const [records, setRecords] = useState<RunRecord[]>(() => loadRunHistory());
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => subscribeRunHistory(() => setRecords(loadRunHistory())), []);

  const open = openId ? records.find((r) => r.runId === openId) : undefined;

  return (
    <PageLayout
      title="History"
      subtitle="Every completed Run of a Path, stored on this device only."
    >
      {records.length === 0 ? (
        <EmptyState icon={Clock} title="No Runs yet">
          Run a Path and its result will appear here.
        </EmptyState>
      ) : (
        <div className="history-layout">
          <ul className="history-list">
            {records.map((record) => (
              <li key={record.runId}>
                <button
                  type="button"
                  className={`history-row${openId === record.runId ? " history-row-active" : ""}`}
                  onClick={() => setOpenId(record.runId)}
                >
                  <div className="history-row-main">
                    <span className="history-row-name">{record.pathName}</span>
                    <span className="history-row-time">{formatWhen(record.completedAt)}</span>
                  </div>
                  <Badge variant={outcomeVariant(record.outcome)}>{record.outcome}</Badge>
                </button>
              </li>
            ))}
          </ul>

          {open && (
            <section className="history-detail">
              <header className="history-detail-head">
                <div>
                  <h3>{open.pathName}</h3>
                  <p className="field-hint">
                    Run {open.runId.slice(0, 8)} · {formatWhen(open.completedAt)}
                  </p>
                </div>
                <Badge variant={outcomeVariant(open.outcome)}>{open.outcome}</Badge>
              </header>

              <h4 className="outputs-subtitle">Captured</h4>
              {Object.keys(open.captured).length === 0 ? (
                <p className="field-hint">Nothing was captured on this Run.</p>
              ) : (
                <dl className="history-captured">
                  {Object.entries(open.captured).map(([key, value]) => (
                    <div key={key} className="data-row">
                      <span className="data-row-label mono">{key}</span>
                      <span className="data-row-value mono">{value}</span>
                    </div>
                  ))}
                </dl>
              )}

              <div className="history-detail-actions">
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => exportRun(open)}>
                  <Download size={14} />
                  Export
                </button>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() => {
                    deleteRun(open.runId);
                    setOpenId(null);
                  }}
                >
                  <Trash2 size={14} />
                  Delete
                </button>
              </div>
            </section>
          )}
        </div>
      )}
    </PageLayout>
  );
}
