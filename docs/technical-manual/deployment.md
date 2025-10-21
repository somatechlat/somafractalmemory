---
title: "Deployment Guide"
purpose: "Comprehensive instructions for deploying SomaFractalMemory across local, QA, and production environments"
audience:
  - "Platform & SRE teams"
  - "DevOps engineers"
last_updated: "2025-10-17"
review_frequency: "quarterly"
---

# Deployment Guide

This guide explains how to deploy SomaFractalMemory with Docker Compose for workstation testing or QA and with Helm for Kubernetes clusters. Both options expose the FastAPI `/memories` surface, Redis-backed cache, and Qdrant vector search tier.

## Prerequisites
- Docker Desktop 4.28+ (or Docker Engine 24+) with `docker compose`
- `make`, `curl`, and `jq`
- Access to the target Docker host or Kubernetes cluster
- A secret management process for production credentials

## Docker Compose (Local / QA)
Follow these steps to provision or redeploy the local stack. The sequence replaces stale containers so the API always reflects the latest code.

1. **Prepare environment defaults**
   ```bash
   cp .env.template .env
   ```
   - Set `SOMA_API_TOKEN` to a value you control.
   - The bundled credentials are development-only and safe for local testing.
   - Never commit the populated `.env` file.

2. **Redeploy the stack**
   ```bash
   docker compose down --remove-orphans
   docker compose build --progress=plain
   docker compose up -d
   ```
   The `build` step ensures the API container uses the currently checked-in source.

3. **Verify readiness**
   ```bash
   make compose-health
   curl -H "Authorization: Bearer $SOMA_API_TOKEN" http://127.0.0.1:9595/stats
   make test-e2e
   ```
   The automated end-to-end test stores and retrieves a memory to confirm Postgres, Redis, and Qdrant connectivity.

4. **Stop the stack (optional)**
   ```bash
   docker compose down
   ```

### Port Map (Compose)
| Service | Host Port | Container Port | Purpose |
|---------|-----------|----------------|---------|
| API     | 9595      | 9595           | Public HTTP entry point |
| Postgres| 40021     | 5432           | Canonical memory store |
| Redis   | 40022     | 6379           | Hot cache |
| Qdrant  | 40023     | 6333           | Vector similarity search |

> ⚠️ Replace every credential in `.env` with production-grade secrets before deploying outside of local or QA environments.

## Kubernetes (Helm)
Use the Helm chart in `helm/` to deploy SomaFractalMemory to a Kubernetes namespace.

1. **Create secrets**
   ```bash
   kubectl create secret generic somafractal-secrets \
     --from-literal=SOMA_API_TOKEN=replace-me \
     --from-literal=SOMA_POSTGRES_URL=postgresql://user:pass@postgres:5432/somamemory \
     -n somafractalmemory
   ```

2. **Install or upgrade the release**
   ```bash
   helm upgrade --install somafractalmemory ./helm \
     -f ./helm/values-prod-ha.yaml \
     --namespace somafractalmemory --create-namespace
   ```

3. **Validate deployment**
   ```bash
   kubectl get pods -n somafractalmemory
   kubectl port-forward svc/somafractalmemory 9595:9595 -n somafractalmemory
   curl -H "Authorization: Bearer $SOMA_API_TOKEN" http://127.0.0.1:9595/readyz
   ```

4. **Expose externally**
   Configure ingress, mesh routes, or load balancers for `/memories`, `/stats`, `/metrics`, `/healthz`, and `/readyz` as required by your platform.

### Port Map (Kubernetes)
| Service | Service Port | Target Port | Notes |
|---------|--------------|-------------|-------|
| API     | 9595         | 9595        | Matches HTTP exposure in Compose |
| Postgres| 40021        | 5432        | Mirror Compose host mapping |
| Redis   | 40022        | 6379        | Shared with rate limiter |
| Qdrant  | 40023        | 6333        | Vector search API |

## Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| `SOMA_API_TOKEN` | Bearer token required for `/memories` routes | `devtoken`
| `SOMA_POSTGRES_URL` | Connection string for Postgres | `postgresql://soma:soma@postgres:5432/somamemory`
| `REDIS_HOST` / `REDIS_PORT` | Redis connection details | `redis` / `6379`
| `QDRANT_URL` | Qdrant endpoint | `http://qdrant:6333`
| `SOMA_RATE_LIMIT_MAX` | Requests allowed per rate-limit window | `120`
| `SOMA_RATE_LIMIT_WINDOW_SECONDS` | Rate-limit window length (seconds) | `60`
| `SOMA_MAX_REQUEST_BODY_MB` | Maximum accepted payload size (MB) | `5`

> **CAUTION (DEVELOPMENT ONLY)**: The rate limiter is a safety control to protect the API and downstream stores from abusive or accidental high-volume traffic. You may temporarily increase `SOMA_RATE_LIMIT_MAX` or set it to `0` to disable the limiter for local development or load testing, but never perform this change in production. After testing, restore the original values and redeploy. When increasing limits, also monitor Postgres, Redis, and Qdrant for resource pressure.

## Post-Deployment Checklist
- [ ] `/readyz` returns HTTP 200 with `kv_store`, `vector_store`, and `graph_store` set to `true`.
- [ ] `/metrics` is scraped by the monitoring stack.
- [ ] `/stats` reflects non-zero `total_memories` after smoke tests.
- [ ] Container logs show no recurring connection failures.

## Troubleshooting
- **API returns 404 for `/memories`**: Rebuild and redeploy the API container (`docker compose build && docker compose up -d`). Endpoints are tied to the running image.
- **Port conflict on localhost**: Override the host ports in `.env` (e.g., `POSTGRES_HOST_PORT=5435`) before starting Compose.
- **Rate limiter blocks traffic**: Increase `SOMA_RATE_LIMIT_MAX` or set it to `0` during load testing in non-production environments.
- **Rate limiter blocks traffic**: Increase `SOMA_RATE_LIMIT_MAX` or set it to `0` during load testing in non-production environments.

> NOTE: Changes to rate limiting should be made only in development or QA environments. Do not disable or raise limits in production. Follow your platform's change control process when performing load tests that temporarily alter operational controls.

## Further Reading
- [Monitoring Guide](monitoring.md)
- [Architecture Overview](architecture.md)
- [Runbooks](runbooks/)
