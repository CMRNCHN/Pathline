import { getAccount, type Account } from "@/persistence/accountsStore";
import { revealVaultSecret } from "@/persistence/vaultStore";

export interface ResolvedRunVariables {
  variables: Record<string, string>;
  missing: string[];
}

/**
 * Hydrates run variables from an Account profile.
 * Secret fields are unsealed from the device vault — never from Path JSON.
 */
export async function resolveRunVariablesFromAccount(
  accountId: string | null | undefined,
  variableNames: string[]
): Promise<ResolvedRunVariables> {
  if (!accountId) {
    return { variables: {}, missing: variableNames };
  }

  const account = getAccount(accountId);
  if (!account) {
    return { variables: {}, missing: variableNames };
  }

  return resolveAccountFields(account, variableNames);
}

export async function resolveAccountFields(
  account: Account,
  variableNames: string[]
): Promise<ResolvedRunVariables> {
  const variables: Record<string, string> = {};
  const missing: string[] = [];

  for (const name of variableNames) {
    const field = account.fields[name];
    if (!field) {
      missing.push(name);
      continue;
    }

    if (field.kind === "plain") {
      if (!field.value.trim()) {
        missing.push(name);
        continue;
      }
      variables[name] = field.value;
      continue;
    }

    const secret = await revealVaultSecret(field.vaultKey);
    if (!secret?.trim()) {
      missing.push(name);
      continue;
    }
    variables[name] = secret;
  }

  return { variables, missing };
}
