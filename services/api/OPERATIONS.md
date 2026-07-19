# Pathline API operations

The API stores only consent metadata and opaque client-encrypted artifacts. Production must set:

- `APP_ENV=production`
- `DATABASE_URL=postgresql+asyncpg://...`
- stable managed `JWT_SECRET` and `SESSION_PEPPER` values of at least 32 characters
- `AUTO_CREATE_SCHEMA=false`
- an explicit comma-separated `CORS_ORIGINS` allowlist

Apply schema changes before deploying:

```sh
cd services/api
alembic upgrade head
alembic current
```

Run Uvicorn with `--no-access-log` unless the deployment proxy is configured to redact URL path
parameters. Session identifiers appear in export/delete paths; application logs use only truncated
HMAC references and correlation IDs.

Do not rotate `SESSION_PEPPER` without a data-expiration plan: existing artifact keys become
unresolvable. Do not rotate `JWT_SECRET` without intentionally invalidating outstanding tokens.

## Backup and restore

Use the managed PostgreSQL service's encrypted point-in-time backups. Before a migration, also take
an encrypted logical backup with the provider's supported `pg_dump` workflow. Test restoration into
an isolated database, run `alembic current`, start the API against that database, and require
`GET /ready` to return 200. Never copy production artifact rows to developer laptops.

## Retention verification

The purge worker removes expired artifacts, their notifications, consent audits, revocations, and
idempotency records. Alert when `/ready` reports a stale purge worker. Periodically verify that all
of these queries return zero:

```sql
SELECT count(*) FROM callstate_records WHERE expires_at <= now();
SELECT count(*) FROM notifications WHERE expires_at <= now();
SELECT count(*) FROM consent_audits WHERE expires_at <= now();
SELECT count(*) FROM revoked_tokens WHERE expires_at <= now();
SELECT count(*) FROM idempotency_records WHERE expires_at <= now();
```

Restore drills and retention query results are deployment evidence; this repository does not select
or configure a particular backup provider.
