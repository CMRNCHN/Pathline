import { KeyRound, Shield } from "lucide-react";
import { PageLayout } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { clearLocalKeys } from "@/crypto";

export function VaultPage() {
  return (
    <PageLayout
      title="Vault"
      subtitle="Local encryption material for callstate — never uploaded in plaintext."
    >
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Shield className="size-4" />
            </div>
            <div>
              <CardTitle>Device keys</CardTitle>
              <CardDescription>
                PromptPath seals callstate with keys kept on this device. Clear them if you want
                a fresh local crypto identity (existing encrypted blobs will no longer decrypt).
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              if (!confirm("Clear local encryption keys on this device?")) return;
              clearLocalKeys();
            }}
          >
            <KeyRound className="size-4" />
            Clear encryption keys
          </Button>
        </CardContent>
      </Card>
    </PageLayout>
  );
}
