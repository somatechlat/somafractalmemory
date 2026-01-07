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

- OPA_URL — e.g., http://opa:8181 (default used if unset)
- OPA_POLICY_PATH — e.g., soma/authz/allow
  - Decision expected as boolean or object with `allow` boolean

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
4. Fallback: postgresql://soma:soma@postgres:5432/somamemory

Redis config:
- REDIS_URL (parsed) OR individual: REDIS_HOST, REDIS_PORT, REDIS_DB

Qdrant config:
- QDRANT_URL OR QDRANT_HOST + QDRANT_PORT (default 6333)

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
