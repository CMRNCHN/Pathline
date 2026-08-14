/** Session-only Run secret drafts — never written into Workflow JSON. */

const PREFIX = "pathline.runSecrets.";

export function loadRunSecretsDraft(scriptId: string): Record<string, string> {
  try {
    const raw = sessionStorage.getItem(PREFIX + scriptId);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    const out: Record<string, string> = {};
    for (const [key, value] of Object.entries(parsed)) {
      if (typeof value === "string") out[key] = value;
    }
    return out;
  } catch {
    return {};
  }
}

export function saveRunSecretsDraft(scriptId: string, secrets: Record<string, string>): void {
  try {
    sessionStorage.setItem(PREFIX + scriptId, JSON.stringify(secrets));
  } catch {
    // Quota / private mode — ignore; Run page still works empty.
  }
}
