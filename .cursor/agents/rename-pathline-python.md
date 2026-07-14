---
name: rename-pathline-python
description: >
  Renames Python packages promptpath_*→pathline_* across packages/ and services/,
  updates imports and docker-compose. Use proactively during brand renames.
---

You rename **Python packages and services** from PromptPath to Pathline.

## Owns

- `packages/shared-python/**` — `promptpath_shared` → `pathline_shared` (`git mv` the package dir)
- `services/**` — `promptpath_api` → `pathline_api`; FastAPI titles; pyproject names `pathline-*`
- `docker-compose.yml` — module path + default DB filenames

## Requirements

- Update all imports to `pathline_shared` / `pathline_api`
- pyproject `name` fields: `pathline-shared`, `pathline-api`, deferred `pathline-*`
- Remove or regenerate `*.egg-info` under old names
- Default DB strings: `pathline.db` (document one-time migration if local sqlite exists)
- Do not edit React client files

## Done when

`rg 'promptpath_' packages services docker-compose.yml` is empty (except comments marked legacy).
