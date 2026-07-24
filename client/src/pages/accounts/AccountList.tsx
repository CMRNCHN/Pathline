import { Plus } from "lucide-react";
import type { Account } from "@/persistence/accountsStore";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { EmptyState } from "@/components/ui/EmptyState";
import { Users } from "lucide-react";

interface AccountListProps {
  accounts: Account[];
  selectedId?: string;
  onSelect: (id: string) => void;
  onCreate: () => void;
}

export function AccountList({ accounts, selectedId, onSelect, onCreate }: AccountListProps) {
  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <Button type="button" size="sm" onClick={onCreate} className="w-full">
        <Plus className="size-4" />
        New account
      </Button>
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
        {accounts.length === 0 ? (
          <EmptyState icon={Users} title="No accounts yet">
            Create an account to store Inputs for Paths.
          </EmptyState>
        ) : (
          accounts.map((account) => (
            <button
              key={account.id}
              type="button"
              onClick={() => onSelect(account.id)}
              className={cn(
                "flex w-full flex-col gap-0.5 rounded-lg border px-3 py-2.5 text-left",
                selectedId === account.id ? "border-primary bg-primary/5" : "hover:bg-muted/60"
              )}
            >
              <span className="truncate text-sm font-medium">{account.name}</span>
              <span className="text-xs text-muted-foreground">
                {Object.keys(account.fields).length} field
                {Object.keys(account.fields).length === 1 ? "" : "s"}
              </span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
