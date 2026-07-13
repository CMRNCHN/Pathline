import type { FormEvent } from "react";
import type { Path } from "@/script/types";
import { scriptDisplayName } from "@/script/storage";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

interface RunConfigureStepProps {
  script: Path;
  scripts: Path[];
  activeId: string;
  onActiveIdChange: (id: string) => void;
  variableNames: string[];
  variables: Record<string, string>;
  onVariableChange: (name: string, value: string) => void;
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
  variableNames,
  variables,
  onVariableChange,
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
          <p className="text-sm text-muted-foreground">Inputs stay on your device.</p>

          <div className="space-y-2">
            <label htmlFor="script" className="text-sm font-medium">
              Path
            </label>
            <select
              id="script"
              value={activeId}
              onChange={(e) => onActiveIdChange(e.target.value)}
              className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm"
            >
              {scripts.map((s) => (
                <option key={s.id} value={s.id}>
                  {scriptDisplayName(s)}
                </option>
              ))}
            </select>
            {script.setup.description && (
              <p className="text-xs text-muted-foreground">{script.setup.description}</p>
            )}
          </div>

          {variableNames.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium">Inputs</h3>
              {variableNames.map((name) => (
                <div key={name} className="space-y-2">
                  <label htmlFor={`var-${name}`} className="text-sm font-medium">
                    {name}
                  </label>
                  <Input
                    id={`var-${name}`}
                    type="password"
                    value={variables[name] ?? ""}
                    onChange={(e) => onVariableChange(name, e.target.value)}
                    placeholder={name}
                    autoComplete="off"
                    required
                  />
                </div>
              ))}
            </div>
          )}

          {outputFields.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Captures</h3>
              <p className="text-xs text-muted-foreground">
                What this Path saves during the call — reviewable later in History.
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
            <Input
              id="target"
              type="tel"
              value={targetNumber}
              onChange={(e) => onTargetNumberChange(e.target.value)}
              required
            />
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={loading || missingVariables.length > 0}
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
