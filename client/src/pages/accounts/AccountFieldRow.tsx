import { useState } from "react";
import type { AccountField } from "@/persistence/accountsStore";
import { listVaultEntries } from "@/persistence/vaultStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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

  return (
    <div className="grid grid-cols-1 gap-2 rounded-lg border p-3 sm:grid-cols-[1fr_7rem_1fr_auto]">
      <Input
        value={name}
        onChange={(e) => onChangeName(e.target.value)}
        placeholder="input_name"
        aria-label="Input name"
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
          value={field.value}
          onChange={(e) => onChangeField({ kind: "plain", value: e.target.value })}
          placeholder="Value"
          aria-label="Plain value"
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
          <SelectTrigger aria-label="Input Vault key">
            <SelectValue placeholder="Vault key…" />
          </SelectTrigger>
          <SelectContent>
            {vaultEntries.length === 0 ? (
              <SelectItem value="__empty" disabled>
                No vault entries
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
      <Button type="button" variant="ghost" size="sm" onClick={onRemove}>
        Remove
      </Button>
    </div>
  );
}
