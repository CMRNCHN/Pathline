import { useState } from "react";
import type { AccountField } from "@/persistence/accountsStore";
import { listVaultEntries } from "@/persistence/vaultStore";
import { CopyButton } from "@/components/CopyButton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  formatFieldDisplay,
  isCreditCardFieldName,
  normalizeFieldStorage,
} from "@/lib/formatFieldValue";

interface AccountFieldRowProps {
  name: string;
  field: AccountField;
  onChangeName: (next: string) => void;
  onChangeField: (field: AccountField) => void;
  onRemove: () => void;
}

export function AccountFieldRow({
  name,
  field,
  onChangeName,
  onChangeField,
  onRemove,
}: AccountFieldRowProps) {
  const vaultEntries = listVaultEntries();
  const [vaultPick, setVaultPick] = useState(field.kind === "secret" ? field.vaultKey : "");
  const plainValue = field.kind === "plain" ? field.value : "";
  const displayValue =
    field.kind === "plain" ? formatFieldDisplay(name, plainValue) : "";
  const copyValue =
    field.kind === "plain"
      ? plainValue
      : field.vaultKey /* key name only — never reveal sealed secret */;

  return (
    <div className="grid grid-cols-1 gap-2 rounded-lg border p-3 sm:grid-cols-[1fr_7rem_1fr_auto_auto]">
      <Input
        value={name}
        onChange={(e) => onChangeName(e.target.value)}
        placeholder="input_name"
        aria-label="Input name"
        className="font-mono"
      />
      <Select
        value={field.kind}
        onValueChange={(kind) => {
          if (kind === "plain") onChangeField({ kind: "plain", value: "" });
          else onChangeField({ kind: "secret", vaultKey: vaultPick || "" });
        }}
      >
        <SelectTrigger aria-label="Field kind">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="plain">Plain</SelectItem>
          <SelectItem value="secret">Secret</SelectItem>
        </SelectContent>
      </Select>
      {field.kind === "plain" ? (
        <Input
          value={displayValue}
          onChange={(e) =>
            onChangeField({
              kind: "plain",
              value: normalizeFieldStorage(name, e.target.value),
            })
          }
          placeholder={
            isCreditCardFieldName(name) ? "####-####-####-####" : "Value"
          }
          inputMode={isCreditCardFieldName(name) ? "numeric" : undefined}
          autoComplete="off"
          data-1p-ignore="true"
          data-lpignore="true"
          data-form-type="other"
          aria-label="Plain value"
          className="font-mono"
        />
      ) : (
        <Select
          value={field.vaultKey || undefined}
          onValueChange={(key) => {
            if (!key) return;
            setVaultPick(key);
            onChangeField({ kind: "secret", vaultKey: key });
          }}
        >
          <SelectTrigger aria-label="Sealed secret key">
            <SelectValue placeholder="Sealed secret…" />
          </SelectTrigger>
          <SelectContent>
            {vaultEntries.length === 0 ? (
              <SelectItem value="__empty" disabled>
                No sealed secrets yet
              </SelectItem>
            ) : (
              vaultEntries.map((entry) => (
                <SelectItem key={entry.key} value={entry.key}>
                  {entry.label} ({entry.key})
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
      )}
      <CopyButton value={copyValue} label={`Copy ${name}`} />
      <Button type="button" variant="ghost" size="sm" onClick={onRemove}>
        Remove
      </Button>
    </div>
  );
}
