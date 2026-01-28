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
