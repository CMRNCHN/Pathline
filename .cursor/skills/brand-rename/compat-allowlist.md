# Compat allowlist template

After a rename, **only** these patterns may still contain the old brand token.

```
# legacy PromptPath — read old localStorage key then migrate
# legacy PromptPath — env fallback PROMPTPATH_* → PATHLINE_*
# legacy PromptPath — window.__promptpathSipBridge alias
```

## Rules

1. Every allowlisted line must sit next to an active shim that prefers the **new** name.
2. Shims are temporary: remove after the look-ahead window (14 days) once telemetry / support confirms no old clients, or keep env/storage readers one more release if needed.
3. Verify agent: if a hit lacks a `legacy PromptPath` marker, it is a failure.
4. Do not allowlist marketing copy, README titles, or package names — those must be the new brand.
