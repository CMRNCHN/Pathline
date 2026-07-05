# Deferred Services (v2 / v3)

These services were scaffolded during initial exploration. They are **not part of v1** and are not started by default in `docker-compose.yml`.

| Service | Phase | Purpose |
|---------|-------|---------|
| `did-manager/` | v2 | DID pool, cooldown, provider distribution |
| `orchestrator/` | v3 | Server-mediated call placement (PJSIP) |
| `stt/` | v3 | Server-side STT (fallback only) |
| `kms/` | v3 | Production key release |
| `auth/` | — | Superseded by `services/api/` |
| `notifications/` | — | Merged into `services/api/` |

Enable when the threat model and roadmap justify the added attack surface.
