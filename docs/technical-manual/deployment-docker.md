---
title: "Docker Runbook (Evented Enterprise)"
last_modified: "2025-10-29"
---

# 🐳 Docker Runbook (Evented Enterprise)

Deploy the full stack locally with one public API port and persistent storage.

## ✅ Prerequisites

- Docker Desktop with Compose v2
- Ports available on host:
  - 9595 (API)
  - Optional dev-only: 40021 (Postgres), 40022 (Redis), 40023 (Qdrant)

## 🔐 .env baseline

Use `.env.example` as a starting point. Minimal local config:

```
SOMA_API_TOKEN=devtoken
SOMA_RATE_LIMIT_MAX=0
SOMA_RATE_LIMIT_WINDOW_SECONDS=0
# Optional CORS: SOMA_CORS_ORIGINS=https://app.example.com
```

For shared or hardened setups, use a strong token and enable rate limiting (e.g., 600 req/min).

## 🚀 Start the stack

```bash
docker compose --profile core up -d
```

This brings up: Postgres, Redis, Qdrant, API. The API is published to http://127.0.0.1:9595.

## 🩺 Verify

```bash
curl -fsS http://127.0.0.1:9595/healthz
```

Write a memory:

```bash
curl -s -X POST http://127.0.0.1:9595/memories \
  -H "Authorization: Bearer ${SOMA_API_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"coord":"0.1,0.2,0.3","payload":{"ok":true},"memory_type":"episodic"}'
```

## 🔧 Hardening (recommended)

- Auth: Use a strong SOMA_API_TOKEN or enable JWT mode (HS256/RS256; exp/iat required; optional iss/aud)
- Rate limit: Set SOMA_RATE_LIMIT_MAX and SOMA_RATE_LIMIT_WINDOW_SECONDS > 0
- CORS: Set SOMA_CORS_ORIGINS if you have browser clients
- OPA policy (optional): OPA_URL and OPA_POLICY_PATH, with an allow decision
- Ports: Expose only 9595; keep Postgres/Redis/Qdrant internal unless needed
- Persistence: Named volumes are configured by default (pgdata, redisdata, qdrantdata)

## 🧰 Recovery tips

- Restart cleanly:
  - `docker compose --profile core down`
  - `docker compose --profile core up -d`
- Fix dev volume corruption (safe for dev only):
  - `docker volume rm somafractalmemory_pgdata somafractalmemory_redisdata`
  - `docker compose --profile core up -d`

## 🔎 Files of interest

- `docker-compose.yml` — services, health checks, volumes, network
- `somafractalmemory/http_api.py` — API endpoints, auth, rate limiting, OPA
- `docs/technical-manual/security-secrets.md` — tokens and secret handling
