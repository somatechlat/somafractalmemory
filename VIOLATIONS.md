# SOMAFRACTALMEMORY - VIBE Violations Log

**Updated:** 2026-02-15
**Status:** ✅ No known active violations from the latest static sweep (code is source of truth).

This file tracks concrete, code-referenced violations of the repo's VIBE rules. If you find a new
violation, add it with file + line + reproduction notes.

## Resolved In This Sweep (2026-02-15)

- Secret leakage: removed printing of `VAULT_TOKEN` in `somafractalmemory/admin/core/security/debug_vault.py`.
- Hardcoded secrets in infra:
  - `infra/k8s/sfm-resilient.yaml` no longer commits `SOMA_API_TOKEN` / DB credentials; it now references a Secret `sfm-secrets`.
  - `infra/standalone/docker-compose.yml` requires explicit secrets (`SOMA_API_TOKEN`, `SFM_DB_PASSWORD`, `SFM_VAULT_TOKEN`, MinIO creds); no default token fallbacks.
  - Removed unused, kompose-generated `infra/k8s/*.yaml` manifests that embedded tokens and stale commands; Tilt uses `infra/k8s/sfm-resilient.yaml`.
- Doc drift fixed to match current code:
  - Removed `/api/v1`/`/api/v2` path drift; canonical routes are `/memories`, `/memories/search`, `/graph/*`.
  - Ports now match `infra/standalone/docker-compose.yml` and Tilt.
  - Updated `AGENT.md` to reflect actual repo layout and entrypoints.
- Tooling/test drift fixed:
  - `scripts/verify_openapi.py` now targets Django Ninja OpenAPI generation.
  - Removed obsolete test file and fixed broken imports; pytest collection succeeds.
  - Removed Qdrant/FastAPI references in tests/docs where they were stale.
- Packaging metadata aligned with repo license and declared framework:
  - `pyproject.toml` now declares Apache-2.0 and Django 5.1+.

## Remaining Non-Violation Note

- `somafractalmemory/admin/core/services.py` uses a deterministic hash embedder by default. This is
  code-accurate but CPU-expensive and not equivalent to production-grade embedding models; treat as
  an operational/performance consideration when sizing deployments.
