import { useState } from "react";
import {
  deleteVaultEntry,
  listVaultEntries,
  type InputVaultEntry,
  upsertVaultEntry,
} from "@/persistence/vaultStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface VaultEntryDialogProps {
  open: boolean;
  onClose: () => void;
  initial?: InputVaultEntry | null;
  onSaved: () => void;
}

/** Inline form (structure pass — no new Dialog primitive). */
export function VaultEntryDialog({ open, onClose, initial, onSaved }: VaultEntryDialogProps) {
  const [key, setKey] = useState(initial?.key ?? "");
  const [label, setLabel] = useState(initial?.label ?? "");
  const [secret, setSecret] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          {initial ? "Update secret" : "Add Input Vault secret"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Input
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="key (e.g. chase_pin)"
          disabled={Boolean(initial)}
          aria-label="Vault key"
        />
        <Input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Label"
          aria-label="Vault label"
        />
        <Input
          type="password"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          placeholder={initial ? "New value (required to rotate)" : "Secret value"}
          aria-label="Secret value"
          autoComplete="off"
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={saving}
            onClick={() => {
              void (async () => {
                const k = key.trim();
                const l = label.trim() || k;
                if (!k || !secret) {
                  setError("Key and secret value are required.");
                  return;
                }
                setSaving(true);
                setError(null);
                try {
                  await upsertVaultEntry(k, l, secret);
                  onSaved();
                  onClose();
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Failed to save");
                } finally {
                  setSaving(false);
                }
              })();
            }}
          >
            Save
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function VaultEntryRow({
  entry,
  onEdit,
  onDeleted,
}: {
  entry: InputVaultEntry;
  onEdit: () => void;
  onDeleted: () => void;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border px-3 py-2">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{entry.label}</p>
        <p className="truncate font-mono text-xs text-muted-foreground">{entry.key}</p>
      </div>
      <Button type="button" size="sm" variant="outline" onClick={onEdit}>
        Rotate
      </Button>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        onClick={() => {
          if (!confirm(`Delete vault entry "${entry.label}"?`)) return;
          deleteVaultEntry(entry.key);
          onDeleted();
        }}
      >
        Delete
      </Button>
    </div>
  );
}

export function VaultList({
  entries,
  onRefresh,
}: {
  entries: InputVaultEntry[];
  onRefresh: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<InputVaultEntry | null>(null);

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button
          type="button"
          onClick={() => {
            setEditing(null);
            setOpen(true);
          }}
        >
          Add secret
        </Button>
      </div>
      {open && (
        <VaultEntryDialog
          open={open}
          onClose={() => setOpen(false)}
          initial={editing}
          onSaved={onRefresh}
        />
      )}
      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No secrets yet. Add sealed values Accounts can bind as Inputs.
        </p>
      ) : (
        entries.map((entry) => (
          <VaultEntryRow
            key={entry.key}
            entry={entry}
            onEdit={() => {
              setEditing(entry);
              setOpen(true);
            }}
            onDeleted={onRefresh}
          />
        ))
      )}
    </div>
  );
}

export function useVaultEntries() {
  const [entries, setEntries] = useState(() => listVaultEntries());
  const refresh = () => setEntries(listVaultEntries());
  return { entries, refresh };
}
