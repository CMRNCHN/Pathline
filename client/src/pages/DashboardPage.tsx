import { useEffect, useMemo, useState } from "react";
import { RuntimeStatusCard } from "./dashboard/RuntimeStatusCard";
import { QuickActionsCard } from "./dashboard/QuickActionsCard";
import { RecentActivityList } from "./dashboard/RecentActivityList";
import { PageLayout } from "@/components/ui/PageHeader";
import { useRuntimeStatus } from "@/hooks/useRuntimeStatus";
import { loadRunHistory, subscribeRunHistory, type RunRecord } from "@/history/runHistory";
import type { AppView } from "@/navigation";
import { createAccount } from "@/persistence/accountsStore";
import { useScriptStore } from "@/store/ScriptStore";

interface DashboardPageProps {
  onNavigate: (view: AppView) => void;
}

export function DashboardPage({ onNavigate }: DashboardPageProps) {
  const { bundledScripts, customScripts, setActiveId, addCustom, loading, error } =
    useScriptStore();
  const [runs, setRuns] = useState<RunRecord[]>(() => loadRunHistory());

  useEffect(() => subscribeRunHistory(() => setRuns(loadRunHistory())), []);

  const runtime = useRuntimeStatus(
    loading,
    error,
    bundledScripts.length,
    customScripts.length
  );

  const recent = useMemo(() => runs.slice(0, 8), [runs]);

  const handleNewPath = () => {
    const created = addCustom();
    setActiveId(created.id);
    onNavigate({ category: "paths", pathId: created.id, panel: "edit" });
  };

  const handleNewAccount = () => {
    const created = createAccount();
    onNavigate({ category: "accounts", accountId: created.id });
  };

  return (
    <PageLayout
      title="Dashboard"
      subtitle="Recent activity, status, and shortcuts into Path Library or Accounts."
    >
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RuntimeStatusCard status={runtime} />
        <QuickActionsCard
          onNavigate={onNavigate}
          onNewPath={handleNewPath}
          onNewAccount={handleNewAccount}
        />
      </div>
      <RecentActivityList recent={recent} onNavigate={onNavigate} />
    </PageLayout>
  );
}
