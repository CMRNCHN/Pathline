import { Shield } from "lucide-react";
import { clearLocalKeys } from "@/crypto";
import { clearVaultEntries } from "@/persistence/vaultStore";
import { PageLayout } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { VaultList, useVaultEntries } from "./vault/VaultList";

export function VaultPage() {
  const { entries, refresh } = useVaultEntries();

  return (
    <PageLayout
      title="Input Vault"
      subtitle="Sealed secret slots on this device. Accounts bind field names to these keys."
    >
      <VaultList entries={entries} onRefresh={refresh} />

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Shield className="size-4" />
            </div>
            <div>
              <CardTitle>Device crypto</CardTitle>
              <CardDescription>
                Clearing keys makes existing sealed vault values and callstate unreadable on this
                device.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              if (!confirm("Clear device encryption keys?")) return;
              clearLocalKeys();
              alert("Device keys cleared.");
            }}
          >
            Clear encryption keys
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={() => {
              if (!confirm("Delete all Input Vault entries?")) return;
              clearVaultEntries();
              refresh();
            }}
          >
            Clear all vault entries
          </Button>
        </CardContent>
      </Card>
    </PageLayout>
  );
}
