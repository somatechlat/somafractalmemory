---
title: "Endpoint Catalog"
last_modified: "2025-10-29"
---

# 📘 Endpoint Catalog

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

- GET /stats — no auth (rate-limited)
- GET /metrics — Prometheus metrics, no auth
- GET /ping — no auth (pong)

Notes
- Rate limiting: controlled by SOMA_RATE_LIMIT_MAX and SOMA_RATE_LIMIT_WINDOW_SECONDS; Redis-backed if available
- OPA policy (optional): requests are evaluated against OPA_URL + OPA_POLICY_PATH; dev client allows if OPA is unavailable
---
title: "Configuration Reference"
last_modified: "2025-10-29"
---

# ⚙️ Configuration Reference

Authoritative overview of environment variables and precedence.

## 🔐 Authentication / Authorization

- SOMA_API_TOKEN — static bearer token (string)
- SOMA_API_TOKEN_FILE — path to file containing the token (string)
- JWT_ENABLED — enable JWT mode (bool-like)
- JWT_SECRET — HS256 secret (string)
- JWT_PUBLIC_KEY — RS256 public key (PEM)
- JWT_ISSUER — expected issuer (optional)
- JWT_AUDIENCE — expected audience (optional)

## 🛂 Policy (OPA)

- SOMA_OPA_URL — e.g., http://opa:8181 (default http://opa:8181)
- SOMA_OPA_TIMEOUT — timeout in seconds (default 1.0)
- SOMA_OPA_FAIL_OPEN — "true" allows access on error (default "false" / Fail Closed)
  - Policy path is hardcoded to `soma/authz/allow` or configured via code.

## 🚦 Rate limiting

- SOMA_RATE_LIMIT_MAX — requests per window (<=0 disables)
- SOMA_RATE_LIMIT_WINDOW_SECONDS — window length in seconds (<=0 disables)
- Backend: Redis if reachable (host/port/db), otherwise in-memory

## 🌐 CORS

- SOMA_CORS_ORIGINS — comma-separated origins (e.g., https://a.com,https://b.com)

## 🗄️ Storage (precedence)

Postgres URL resolution (first set wins):
1. SOMA_POSTGRES_URL
2. settings.postgres_url (centralized settings, if present)
3. POSTGRES_URL
4. Fallback: postgresql://soma@postgres:5432/somamemory

Redis config:
- REDIS_URL (parsed) OR individual: REDIS_HOST, REDIS_PORT, REDIS_DB

Milvus config (Standard):
- SOMA_MILVUS_HOST (default "milvus")
- SOMA_MILVUS_PORT (default 19530)

HASHICORP VAULT (Secrets):
- SOMA_VAULT_URL — e.g. http://vault:8200 (Required for secrets in prod)
- SOMA_VAULT_ROLE — Kubernetes role for auth
- SOMA_SECRETS_PATH — Path to secret in Vault

## 🔭 Observability

- LOG_LEVEL — default INFO
- /metrics — Prometheus scrape
- OpenTelemetry tracing enabled by default; console exporter fallback in dev

## 📦 API / server

- SOMA_API_PORT — container port (default 10101)
- API_PORT — host-published port (Compose mapping)
- SOMA_MAX_REQUEST_BODY_MB — max request size (default 5MB)

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
- Engineering rules and workflow: see [Vibe Coding Rules](../VIBE_CODING_RULES.md)

Additional topics will be added here over time, including deployment, monitoring, and runbooks.
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
- SOMA_API_TOKEN: Bearer token for API access (string)
- SOMA_API_TOKEN_FILE: Path to a file containing the token (string)
- JWT_ENABLED (optional): Enable JWT auth mode (bool-like)
- JWT_SECRET (optional): HMAC secret if JWT (HS256) is used (string)
- JWT_PUBLIC_KEY (optional): RSA public key if JWT (RS256) is used (PEM)
- JWT_ISSUER/JWT_AUDIENCE (optional): Validate iss/aud claims
- POSTGRES_PASSWORD: Postgres password (string)
- SOMA_API_PORT: API port inside container (int; default 10101)

## Production guidance

- **Never** commit real secrets to the repository.
- **Mandatory in Production**: Use HashiCorp Vault.
  - Set `SOMA_VAULT_URL` and `SOMA_VAULT_ROLE`.
  - Secrets are injected into process memory at startup.
- Rotate tokens regularly and audit usage.

## Rotation and audit

- Maintain an inventory of issued tokens and rotation dates.
- Log auth failures and suspicious access patterns.
- Prefer per-service or per-user tokens over shared tokens.

## Local quick check

- Start services: `docker compose -f infra/standalone/docker-compose.yml up -d`
- Health: GET `http://127.0.0.1:10101/healthz`
- Use Authorization: `Bearer $SOMA_API_TOKEN`
