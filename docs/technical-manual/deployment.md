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

1. **Create secrets (required)**
    ```bash
    # API token secret (referenced by .Values.secrets.apiTokenSecretName)
    kubectl create secret generic soma-api-token \
       --from-literal=SOMA_API_TOKEN=<your-secure-token> \
       -n somafractalmemory

    # Postgres password secret (referenced by .Values.secrets.postgresPasswordSecretName)
    kubectl create secret generic soma-postgres-password \
       --from-literal=SOMA_POSTGRES_PASSWORD=<your-secure-password> \
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

4. **Expose externally (optional)**
    Enable ingress in values and configure TLS:
    ```yaml
    ingress:
       enabled: true
       className: nginx
       hosts:
          - host: sfm.example.com
             paths:
                - path: /
                   pathType: Prefix
       tls:
          - hosts: ["sfm.example.com"]
             secretName: sfm-tls
    ```

### Optional: Scheduled Backups
Enable a backup CronJob that runs the built-in backup script on a schedule:
```yaml
backup:
   enabled: true
   schedule: "0 3 * * *"
   image: "somafractalmemory:latest"
   backupDir: "/backups"
   dataDir: "/data"
```

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

## CI/CD pipeline (GitHub Actions)
This repository includes an optional pipeline in `.github/workflows/deploy-soma-stack.yml` that can build, scan, and (optionally) deploy via Helm.

Key features:
- Build and push Docker image to GHCR with tags `latest`, `${DEPLOY_MODE}`, and the commit SHA.
- Helm lint and Trivy filesystem scan on the `helm/` chart.
- Optional cluster deployment and validations when a kubeconfig secret is provided.

Modes (workflow_dispatch input `deploy_mode`):
- `dev_full` (local overrides) → uses `helm/values-local-dev.yaml`
- `dev_prod` (prod-like toggles on) → uses `helm/values.yaml`
- `prod` (default production values) → uses `helm/values.yaml`
- `prod_ha` (production high-availability) → uses `helm/values-prod-ha.yaml`

Cluster prerequisites (optional steps):
- Add a repository secret `KUBE_CONFIG` containing a kubeconfig for your target cluster (base64 not required; raw content is fine). The workflow will place it at runtime and set `KUBECONFIG`.
- The release name is `soma` and the namespace is `soma-$DEPLOY_MODE`.
- Validation uses the label selector `app=somafractalmemory` to detect pods.

Helper script:
- Use `scripts/generate-global-env.sh <mode> [output_path]` to generate a unified env file. The workflow writes it to `$GITHUB_WORKSPACE/soma-global.env` by default. For local use:
   ```bash
   scripts/generate-global-env.sh prod ./soma-global.env
   ```

Manual run:
1. In GitHub → Actions → Deploy SomaStack → Run workflow → choose a mode.
2. If `KUBE_CONFIG` is configured, the workflow will deploy with Helm and run readiness checks; otherwise it will only build, push, and lint/scan.

Rollback: If a validation step fails (pods not ready, etc.), re-run the workflow with a previous commit SHA or remove the kubeconfig secret to skip deployment.
