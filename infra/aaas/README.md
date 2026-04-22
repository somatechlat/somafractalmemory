# AAAS (Agent-as-a-Service) Deployment

## Overview

This directory contains the infrastructure configuration for SomaFractalMemory
in **AAAS mode** — multi-tenant API key management with SomaBrain integration.

AAAS is a **separate deployment concern** from Standalone mode.

## Status: NOT YET DEPLOYED

AAAS mode requires:
- SomaBrain central auth integration (`sbk_*` API keys)
- Usage tracking middleware and billing sync (Lago)
- Per-tenant API key management (`sfm_live_*`, `sfm_test_*`)
- UsageRecord aggregation with hour-bucket upserts

## Code References

The AAAS code lives in the main codebase but is **not loaded** in standalone mode:

| Module | Purpose |
|---|---|
| `somafractalmemory/admin/aaas/auth.py` | MultiAuth, APIKeyAuth, SomaBrain integration |
| `somafractalmemory/admin/aaas/models.py` | APIKey, UsageRecord Django models |
| `somafractalmemory/admin/aaas/middleware.py` | UsageTrackingMiddleware (billing) |
| `somafractalmemory/admin/aaas/sync.py` | UsageSyncClient → SomaBrain Lago |
| `somafractalmemory/api/routers/aaas_admin.py` | API Key CRUD + Usage Stats endpoints |

## Settings

AAAS mode uses `somafractalmemory.settings` (the default settings, not standalone).
The default settings include:
- `somafractalmemory.admin.aaas` in `INSTALLED_APPS`
- `UsageTrackingMiddleware` in `MIDDLEWARE`

## Future Docker Compose

When AAAS mode is ready for deployment, create `docker-compose.yml` here
that sets:
```yaml
environment:
  DJANGO_SETTINGS_MODULE: "somafractalmemory.settings"
  SFM_AUTH_MODE: "integrated"  # or "standalone" for sfm_* keys only
  SOMABRAIN_URL: "http://somabrain:10100"
  SOMABRAIN_API_TOKEN: "${SOMABRAIN_API_TOKEN}"
```

## Port Authority

AAAS mode uses the same port range as standalone (10xxx).
No port conflicts — the API port is always 10101.
