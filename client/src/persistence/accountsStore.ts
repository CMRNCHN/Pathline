/** Local Account profiles — field map plugs into Path setup.inputs. Secrets use vaultKey only. */

export type AccountField =
  | { kind: "plain"; value: string }
  | { kind: "secret"; vaultKey: string };

export interface Account {
  id: string;
  name: string;
  notes?: string;
  fields: Record<string, AccountField>;
  updatedAt: string;
}

const STORAGE_KEY = "pathline-accounts";

function readAll(): Account[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Account[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(accounts: Account[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(accounts));
}

export function listAccounts(): Account[] {
  return readAll().sort((a, b) => a.name.localeCompare(b.name));
}

export function getAccount(id: string): Account | undefined {
  return readAll().find((a) => a.id === id);
}

export function saveAccount(account: Account): void {
  const all = readAll();
  const idx = all.findIndex((a) => a.id === account.id);
  const next = { ...account, updatedAt: new Date().toISOString() };
  if (idx >= 0) all[idx] = next;
  else all.push(next);
  writeAll(all);
}

export function createAccount(name = "New account"): Account {
  const account: Account = {
    id: crypto.randomUUID(),
    name,
    fields: {},
    updatedAt: new Date().toISOString(),
  };
  saveAccount(account);
  return account;
}

export function deleteAccount(id: string): void {
  writeAll(readAll().filter((a) => a.id !== id));
}

/** Resolved Input names available from an account (plain values + secret vault keys present). */
export function accountInputNames(account: Account): string[] {
  return Object.keys(account.fields).filter((name) => {
    const field = account.fields[name];
    if (!field) return false;
    if (field.kind === "plain") return Boolean(field.value.trim());
    return Boolean(field.vaultKey.trim());
  });
}
