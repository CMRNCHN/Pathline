import { useMemo, useState } from "react";
import {
  type Account,
  type AccountField,
  saveAccount,
  deleteAccount,
} from "@/persistence/accountsStore";
import { pathsAvailableForAccount } from "@/script/pathReadiness";
import { mergeScripts } from "@/script/selectors";
import { scriptDisplayName } from "@/script/storage";
import { useScriptStore } from "@/store/ScriptStore";
import type { AppView } from "@/navigation";
import { AccountFieldRow } from "./AccountFieldRow";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

interface AccountDetailProps {
  account: Account;
  onChange: (account: Account) => void;
  onDeleted: () => void;
  onNavigate: (view: AppView) => void;
}

export function AccountDetail({ account, onChange, onDeleted, onNavigate }: AccountDetailProps) {
  const { bundledScripts, customScripts } = useScriptStore();
  const paths = mergeScripts(bundledScripts, customScripts);
  const readyPaths = useMemo(() => pathsAvailableForAccount(account, paths), [account, paths]);
  const [draftName, setDraftName] = useState(account.name);

  const persist = (next: Account) => {
    saveAccount(next);
    onChange(next);
  };

  const fieldEntries = Object.entries(account.fields);

  const renameField = (oldName: string, nextName: string) => {
    const trimmed = nextName.trim();
    if (!trimmed || trimmed === oldName) return;
    if (account.fields[trimmed]) return;
    const fields = { ...account.fields };
    fields[trimmed] = fields[oldName];
    delete fields[oldName];
    persist({ ...account, fields });
  };

  const setField = (name: string, field: AccountField) => {
    persist({ ...account, fields: { ...account.fields, [name]: field } });
  };

  const removeField = (name: string) => {
    const fields = { ...account.fields };
    delete fields[name];
    persist({ ...account, fields });
  };

  const addField = () => {
    let n = 1;
    let key = `input_${n}`;
    while (account.fields[key]) {
      n += 1;
      key = `input_${n}`;
    }
    persist({
      ...account,
      fields: { ...account.fields, [key]: { kind: "plain", value: "" } },
    });
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto">
      <div className="space-y-2">
        <Input
          value={draftName}
          onChange={(e) => setDraftName(e.target.value)}
          onBlur={() => {
            const name = draftName.trim() || "Untitled account";
            setDraftName(name);
            persist({ ...account, name });
          }}
          aria-label="Account name"
        />
        <Textarea
          value={account.notes ?? ""}
          onChange={(e) => persist({ ...account, notes: e.target.value })}
          placeholder="Notes (optional)"
          rows={2}
        />
      </div>

      <section className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-medium">Fields</h3>
          <Button type="button" size="sm" variant="outline" onClick={addField}>
            Add field
          </Button>
        </div>
        {fieldEntries.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Add fields that match Path Inputs (e.g. account_pin). Secrets bind to Input Vault keys.
          </p>
        ) : (
          fieldEntries.map(([name, field]) => (
            <AccountFieldRow
              key={name}
              name={name}
              field={field}
              onChangeName={(next) => renameField(name, next)}
              onChangeField={(f) => setField(name, f)}
              onRemove={() => removeField(name)}
            />
          ))
        )}
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-medium">Paths ready for this account</h3>
        {readyPaths.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No Paths match yet. Fill fields that cover each Path&apos;s Inputs.
          </p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {readyPaths.map((path) => (
              <li key={path.id}>
                <Button
                  type="button"
                  variant="secondary"
                  className="w-full justify-start"
                  onClick={() =>
                    onNavigate({ category: "paths", pathId: path.id, panel: "run" })
                  }
                >
                  {scriptDisplayName(path)}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Button
        type="button"
        variant="destructive"
        onClick={() => {
          if (!confirm(`Delete account "${account.name}"?`)) return;
          deleteAccount(account.id);
          onDeleted();
        }}
      >
        Delete account
      </Button>
    </div>
  );
}
