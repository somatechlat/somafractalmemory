---
title: "Endpoint Catalog"
last_modified: "2025-10-29"
---

# 📘 Endpoint Catalog

## Document Control

| Field | Value |
|---|---|
| Document Title | 📘 Endpoint Catalog |
| Document Identifier | SOMA-SFM-GUIDE-OPS-001 |
| Version | 1.2.0 |
| Date | 2026-10-03 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2027-01-03 |


## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-09-28 | SomaTech Engineering | Initial issue. Brought under the house ISO document-control contract. |
| 1.1.0 | 2026-09-28 | SomaTech Engineering | Replaced the link to `../VIBE_CODING_RULES.md`, which resolves outside `docs/` and so could never be a site page, with a path reference. Replaced "additional topics will be added here over time" with pointers to the documents that already cover deployment and production readiness. |
| 1.2.0 | 2026-10-03 | SomaTech Engineering | Truth pass against the code. Removed the JWT block, the OPA policy block, the rate-limiting block, the CORS block, `SOMA_MAX_REQUEST_BODY_MB`, `SOMA_API_PORT`, `SOMA_POSTGRES_URL` and `SOMA_SECRETS_PATH`. Those knobs were deleted because nothing reads them (`settings/infra.py:25-77`). `/stats` is no longer described as rate-limited. Configuration section rewritten to the `TUNABLES` registry. |


Auth: Bearer token unless noted. Accepts SOMA_API_TOKEN (shared) or `sfm_*` API keys. Token is required for all memory/search/graph routes.

## Health

- GET /health — no auth
- GET /healthz — no auth

## Memories

- POST /memories — create/store memory (auth required)
  - Body: { "coord": string, "payload": object, "memory_type": "episodic" | "semantic" }
  - 200 { "coord": string, "memory_type": string, "ok": true }

- GET /memories/{coord} — fetch memory (auth required)
  - 200 { "memory": object } | 404

- DELETE /memories/{coord} — delete memory (auth required)
  - 200 { "coord": string, "deleted": boolean }

## Search

- POST /memories/search — vector search (auth required)
  - Body: { "query": string, "top_k": int=5, "filters"?: object }
  - 200 { "memories": [ { ... } ] }

- GET /memories/search — query via query params (auth required)
  - Params: query (str), top_k (int=5), filters (JSON string)
  - 200 { "memories": [ { ... } ] }

## System

- GET /stats — no auth
- GET /metrics — Prometheus metrics, no auth
- GET /ping — no auth (pong)

Notes
- **Rate limiting: none.** No rate-limit middleware exists. `SOMA_RATE_LIMIT_*` knobs were deleted with the absent gate (`settings/infra.py:65-68`).
- **OPA: none.** There is no OPA client in this tree. An OPA container is composed in `infra/standalone/docker-compose.yml` but nothing calls it. `SOMA_OPA_*` knobs were deleted (`settings/infra.py:69-71`).
---
title: "Configuration Reference"
last_modified: "2025-10-29"
---

# ⚙️ Configuration Reference

Authoritative overview of environment variables and precedence.

**Every tunable is declared once on the `TUNABLES` registry in
`somafractalmemory/settings/model.py`.** A key that is not in `TUNABLES`
cannot be resolved (fail-closed, Rule 91). Keys deleted from that registry
were deleted because nothing reads them — a config knob with no reader is a
lie. The full deletion record is `somafractalmemory/settings/infra.py:25-77`.

## 🔐 Authentication / Authorization

- `SOMA_API_TOKEN` — static bearer token (string). **Required.** Compared with
  `hmac.compare_digest`. Unconfigured rejects every caller (fail-closed).
- Auth is the standalone bearer only. There is **no JWT mode**, no per-key
  credentials and no SomaBrain token validation in this tree.

## 🛂 Policy (OPA)

**None.** There is no OPA client. An OPA container is composed in
`infra/standalone/docker-compose.yml` but nothing evaluates requests against
it. `SOMA_OPA_URL`, `SOMA_OPA_TIMEOUT` and `SOMA_OPA_FAIL_OPEN` were deleted
with the absent gate.

## 🚦 Rate limiting

**None.** No rate-limit middleware exists. `SOMA_RATE_LIMIT_MAX` and
`SOMA_RATE_LIMIT_WINDOW_SECONDS` were deleted. `api.core.get_rate_limiter`
used to return `None` and claim otherwise; the stub is gone with the knobs.

## 🌐 CORS

**None.** No CORS middleware exists (`settings/django_core.py:181-185`).
`SOMA_CORS_ORIGINS` was deleted.

## 🗄️ Storage

Postgres (through Django ORM `DATABASES`):
- `SOMA_DB_NAME` (default `somafractalmemory`), `SOMA_DB_HOST` (default `localhost`), `SOMA_DB_PORT` (default `5432`)
- `SOMA_DB_USER` / `SOMA_DB_PASSWORD` — credentials, no code default. Vault
  first (`somafractalmemory/database`), then the deployment's injection channel.
  A Vault failure raises. There is no `SOMA_POSTGRES_URL` legacy DSN and no
  code-default fallback URL.

Redis:
- `SOMA_REDIS_HOST` (absent = no Redis), `SOMA_REDIS_PORT` (default `6379`), `SOMA_REDIS_DB` (default `0`), `SOMA_REDIS_PASSWORD` (absent = no AUTH)

Milvus:
- `SOMA_MILVUS_HOST` (absent = no Milvus), `SOMA_MILVUS_PORT` (default `19530`), `SOMA_MILVUS_TIMEOUT_S` (default `10.0`)
- `SOMA_VECTOR_DIM` (default `768`), `SOMA_SIMILARITY_METRIC` (default `cosine`), `SOMA_MILVUS_NLIST` (default `128`), `SOMA_MILVUS_NPROBE` (default `16`)

HashiCorp Vault (secrets):
- `SOMA_VAULT_URL` — Vault address (bootstrap also reads `SOMA_VAULT_ADDR` / `VAULT_ADDR`)
- Credentials are resolved per-secret in `settings.django_core._credential`.
  There is no generic `SOMA_SECRETS_PATH` prefix.

## 🔭 Observability

- `SOMA_LOG_LEVEL` (default `INFO`), `SOMA_LOG_JSON` (default `false`)
- `SOMA_PROBE_TIMEOUT_S` (default `2.0`)
- `/metrics` — Prometheus scrape
- OpenTelemetry tracing enabled by default; console exporter fallback in dev.
  There is no Langfuse integration (`SOMA_LANGFUSE_*` deleted).

## 📦 API / server

- The process binds where gunicorn/daphne is told to bind. There is no
  `SOMA_API_PORT` settings reader.
- No request body cap. `SOMA_MAX_REQUEST_BODY_MB` was deleted with the absent
  middleware.

## 🧪 Quick checks

- Health: `curl -fsS http://127.0.0.1:10101/healthz`
- Stats: `curl -s http://127.0.0.1:10101/stats`
- Endpoints: see Endpoint Catalog
---
title: "Technical Manual Overview"
project: "somafractalmemory"
last_modified: "2025-10-25"
---

# Technical Manual Overview

This section contains operational and architectural guidance for SomaFractalMemory.

- Security and Secrets (Dev vs Prod): see below (embedded in this document)
- Deployment (Docker): see [deployment.md](deployment.md)
- Configuration Reference: see below (embedded in this document)
- Endpoint Catalog: see below (embedded in this document)
- Engineering rules and workflow: see `VIBE_CODING_RULES.md` at the repository
  root. It is deliberately not linked here: it sits outside `docs/`, so it is
  not part of the published site.

Deployment, monitoring and runbook material is in
[deployment.md](deployment.md) and
[PRODUCTION_READINESS.md](PRODUCTION_READINESS.md).
---
title: "Security and Secrets (Dev vs Prod)"
project: "somafractalmemory"
last_modified: "2025-10-25"
---

# Security and Secrets (Dev vs Prod)

This document explains how secrets are handled for local development versus production.

## Development defaults

- The standalone Docker Compose stack requires an explicit `SOMA_API_TOKEN`.
- Do not commit real tokens to git; use `.env` locally and Secrets in Kubernetes.

## Overriding secrets

You can override the default token and other settings without editing compose by using an `.env` file or shell env vars.

Options (precedence: shell > .env > compose defaults):
- Shell: `export SOMA_API_TOKEN=your-token && docker compose -f infra/standalone/docker-compose.yml up -d`
- `.env` file at repo root (see `.env.example`), then `docker compose -f infra/standalone/docker-compose.yml up -d`.

Common variables:
- `SOMA_API_TOKEN`: Bearer token for API access (string)
- `SOMA_DB_USER` / `SOMA_DB_PASSWORD`: Postgres credentials (Vault first, no code default)
- `SOMA_SECRET_KEY`: Django crypto key

There is **no JWT mode**. `JWT_ENABLED`, `JWT_SECRET`, `JWT_PUBLIC_KEY`,
`JWT_ISSUER` and `JWT_AUDIENCE` were deleted: nothing validated a JWT
(`settings/infra.py:53-54`). There is no `SOMA_API_PORT` settings reader.

## Production guidance

- **Never** commit real secrets to the repository.
- **Mandatory in Production**: Use HashiCorp Vault.
  - Set `SOMA_VAULT_URL`.
  - Secrets are resolved in process memory by `django_core._credential`; they
    are **never** written back to the environment (Rule 164).
  - A Vault failure **raises**. It is not a graceful fallback.
- Rotate the bearer token regularly and audit usage. Rotation is a coordinated
  restart: standalone mode has one shared `SOMA_API_TOKEN`.

## Rotation and audit

- Maintain an inventory of issued tokens and rotation dates.
- Log auth failures and suspicious access patterns.
- Prefer per-service or per-user tokens over shared tokens.

## Local quick check

- Start services: `docker compose -f infra/standalone/docker-compose.yml up -d`
- Health: GET `http://127.0.0.1:10101/healthz`
- Use Authorization: `Bearer $SOMA_API_TOKEN`
