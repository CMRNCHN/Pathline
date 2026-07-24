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

interface AccountsPageProps {
  accountId?: string;
  onNavigate: (view: AppView) => void;
}

export function AccountsPage({ accountId, onNavigate }: AccountsPageProps) {
  const [accounts, setAccounts] = useState<Account[]>(() => listAccounts());
  const selected = accountId ? getAccount(accountId) : undefined;

  useEffect(() => {
    setAccounts(listAccounts());
  }, [accountId]);

  const refresh = () => setAccounts(listAccounts());

  const handleCreate = () => {
    const created = createAccount();
    refresh();
    onNavigate({ category: "accounts", accountId: created.id });
  };

  return (
    <PageLayout
      title="Accounts"
      subtitle="Stored Inputs for Paths — plain values here, secrets via Input Vault."
      action={
        <Button type="button" variant="outline" onClick={() => onNavigate({ category: "vault" })}>
          Open Input Vault
        </Button>
      }
      wide
    >
      <div className="grid min-h-[28rem] grid-cols-1 gap-4 lg:grid-cols-[minmax(14rem,18rem)_1fr]">
        <AccountList
          accounts={accounts}
          selectedId={accountId}
          onSelect={(id) => onNavigate({ category: "accounts", accountId: id })}
          onCreate={handleCreate}
        />
        <div className="min-h-[24rem] rounded-xl border bg-card/30 p-3 md:p-4">
          {selected ? (
            <AccountDetail
              key={selected.id}
              account={selected}
              onChange={() => refresh()}
              onDeleted={() => {
                refresh();
                onNavigate({ category: "accounts" });
              }}
              onNavigate={onNavigate}
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              Select an account or create one.
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}
