import type { FormEvent } from "react";
import type { Path } from "@/script/types";
import type { Account } from "@/persistence/accountsStore";
import { scriptDisplayName } from "@/script/storage";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { CopyButton } from "@/components/CopyButton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface RunConfigureStepProps {
  script: Path;
  scripts: Path[];
  activeId: string;
  onActiveIdChange: (id: string) => void;
  accounts: Account[];
  accountId: string;
  onAccountIdChange: (id: string) => void;
  variableNames: string[];
  variables: Record<string, string>;
  outputFields: string[];
  targetNumber: string;
  onTargetNumberChange: (value: string) => void;
  loading: boolean;
  missingVariables: string[];
  error: string | null;
  onSubmit: (e: FormEvent) => void;
}

export function RunConfigureStep({
  script,
  scripts,
  activeId,
  onActiveIdChange,
  accounts,
  accountId,
  onAccountIdChange,
  variableNames,
  variables,
  outputFields,
  targetNumber,
  onTargetNumberChange,
  loading,
  missingVariables,
  error,
  onSubmit,
}: RunConfigureStepProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Configure run</CardTitle>
        <Badge variant="secondary">{scriptDisplayName(script)}</Badge>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={onSubmit}>
          <p className="text-sm text-muted-foreground">
            Inputs are resolved from a local Account profile. Secrets are unsealed from the
            device vault — never typed or stored in Path JSON.
          </p>

          <div className="space-y-2">
            <label htmlFor="script" className="text-sm font-medium">
              Path
            </label>
            <Select
              value={activeId}
              onValueChange={(id) => id && onActiveIdChange(id)}
            >
              <SelectTrigger id="script" className="w-full">
                <SelectValue placeholder="Select a Path" />
              </SelectTrigger>
              <SelectContent>
                {scripts.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {scriptDisplayName(s)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {script.setup.description && (
              <p className="text-xs text-muted-foreground">{script.setup.description}</p>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="account" className="text-sm font-medium">
              Account
            </label>
            <Select
              value={accountId || undefined}
              onValueChange={(id) => id && onAccountIdChange(id)}
            >
              <SelectTrigger id="account" className="w-full">
                <SelectValue placeholder="Select an Account" />
              </SelectTrigger>
              <SelectContent>
                {accounts.map((account) => (
                  <SelectItem key={account.id} value={account.id}>
                    {account.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {accounts.length === 0 && (
              <p className="text-xs text-muted-foreground">
                Create an Account under Accounts and bind sealed secrets first.
              </p>
            )}
          </div>

          {variableNames.length > 0 && accountId && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium">Resolved inputs</h3>
              {variableNames.map((name) => (
                <div key={name} className="flex items-center justify-between gap-2 text-sm">
                  <span className="font-mono">{name}</span>
                  <div className="flex items-center gap-1">
                    <Badge variant={variables[name] ? "secondary" : "destructive"}>
                      {variables[name] ? "Vault / profile ready" : "Missing"}
                    </Badge>
                    <CopyButton
                      value={variables[name] ?? ""}
                      label={`Copy ${name}`}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {outputFields.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Captures</h3>
              <p className="text-xs text-muted-foreground">
                What this Path saves during the call — reviewable later in history.
              </p>
              <div className="flex flex-wrap gap-2">
                {outputFields.map((field) => (
                  <Badge key={field} variant="outline" className="font-mono">
                    {field}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-2">
            <label htmlFor="target" className="text-sm font-medium">
              Target number — local only
            </label>
            <div className="flex items-center gap-1">
              <Input
                id="target"
                type="tel"
                value={targetNumber}
                onChange={(e) => onTargetNumberChange(e.target.value)}
                required
                className="flex-1"
              />
              <CopyButton value={targetNumber} label="Copy target number" />
            </div>
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={loading || !accountId || missingVariables.length > 0}
          >
            {loading ? "Starting…" : "Run"}
          </Button>
        </form>

        {error && (
          <Alert variant="destructive" className="mt-4">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
