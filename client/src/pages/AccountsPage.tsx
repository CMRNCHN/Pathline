import { useEffect, useState } from "react";
import {
  createAccount,
  getAccount,
  listAccounts,
  type Account,
} from "@/persistence/accountsStore";
import type { AppView } from "@/navigation";
import { AccountList } from "./accounts/AccountList";
import { AccountDetail } from "./accounts/AccountDetail";
import { PageLayout } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/button";
import { VaultList, useVaultEntries } from "./vault/VaultList";

interface AccountsPageProps {
  accountId?: string;
  panel?: "profile" | "secrets";
  onNavigate: (view: AppView) => void;
}

export function AccountsPage({ accountId, panel = "profile", onNavigate }: AccountsPageProps) {
  const [accounts, setAccounts] = useState<Account[]>(() => listAccounts());
  const selected = accountId ? getAccount(accountId) : undefined;
  const { entries, refresh: refreshVault } = useVaultEntries();
  const activePanel = panel === "secrets" ? "secrets" : "profile";

  useEffect(() => {
    setAccounts(listAccounts());
  }, [accountId]);

  const refresh = () => setAccounts(listAccounts());

  const handleCreate = () => {
    const created = createAccount();
    refresh();
    onNavigate({ category: "accounts", accountId: created.id, panel: "profile" });
  };

  return (
    <PageLayout
      title="Accounts"
      subtitle="Profiles and sealed secrets for Path Inputs. Secrets never go in Path JSON."
      action={
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant={activePanel === "profile" ? "default" : "outline"}
            size="sm"
            onClick={() =>
              onNavigate({ category: "accounts", accountId, panel: "profile" })
            }
          >
            Profiles
          </Button>
          <Button
            type="button"
            variant={activePanel === "secrets" ? "default" : "outline"}
            size="sm"
            onClick={() => onNavigate({ category: "accounts", panel: "secrets" })}
          >
            Sealed secrets ({entries.length})
          </Button>
        </div>
      }
      wide
    >
      {activePanel === "secrets" ? (
        <div className="rounded-xl border bg-card/30 p-3 md:p-4">
          <VaultList entries={entries} onRefresh={refreshVault} />
        </div>
      ) : (
        <div className="grid h-[min(70vh,42rem)] min-h-[28rem] grid-cols-1 gap-4 lg:grid-cols-[minmax(14rem,18rem)_1fr]">
          <div className="min-h-0">
            <AccountList
              accounts={accounts}
              selectedId={accountId}
              onSelect={(id) =>
                onNavigate({ category: "accounts", accountId: id, panel: "profile" })
              }
              onCreate={handleCreate}
            />
          </div>
          <div className="min-h-0 overflow-y-auto overscroll-contain touch-pan-y rounded-xl border bg-card/30 p-3 md:p-4">
            {selected ? (
              <AccountDetail
                key={selected.id}
                account={selected}
                onChange={() => refresh()}
                onDeleted={() => {
                  refresh();
                  onNavigate({ category: "accounts", panel: "profile" });
                }}
                onNavigate={onNavigate}
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                Select a profile or create one. Profiles stay on this device.
              </div>
            )}
          </div>
        </div>
      )}
    </PageLayout>
  );
}
