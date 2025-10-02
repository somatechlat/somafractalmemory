# Canonical Documentation for SomaFractalMemory

This document is the operational source of truth for developers and operators. It consolidates the steps required to run the stack locally, configure services, and keep documentation builds up to date.

---

## 1. Prepare the Environment
1. Copy the shared environment file:
   ```bash
   cp .env.example .env
   ```
2. (Optional) Create a Python virtual environment and install the package in editable mode:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```
3. Adjust `.env` to match the target mode (`MEMORY_MODE`, ports, credentials). The file is consumed by every Docker service via `env_file: .env` in `docker-compose.yml`.

---

## 2. Build and Run the Stack
1. **Build images** after code changes:
   ```bash
   docker compose build
   ```
2. **Start everything** (Redis, Postgres, Qdrant, Redpanda, API, consumer, sandbox API):
   ```bash
   docker compose up -d
   ```
3. **Access endpoints**:
   * API: <http://localhost:9595>
   * Sandbox API (`test_api`): <http://localhost:8888>
   * Prometheus metrics: `/metrics`
   * Swagger UI: `/docs`
4. **Stop services** while preserving data:
   ```bash
   docker compose down
   ```
5. **Wipe volumes** when you need a clean slate:
   ```bash
   docker compose down -v
   ```

Named volumes created by the compose file: `redis_data`, `qdrant_storage`, `postgres_data`, `redpanda_data`.


## 3. Local Kubernetes Stack (Kind + Helm)
This workflow mirrors the production topology on a single Kind node. It is the
baseline for pre-commit validation and the reference for the automation scripts
in `scripts/run_ci.sh` and `scripts/port_forward_api.sh`.

### 3.1 Prerequisites
- Docker Desktop (or Docker Engine) provisioned with **8 vCPUs** and **32 GiB** of
   memory.
- [`kind`](https://kind.sigs.k8s.io/) v0.23+ and `kubectl`/`helm` on your PATH.
- Built API image tag available locally (for the default chart this is
   `somatechlat/soma-memory-api:dev-local-20251002`).

### 3.2 Create or refresh the Kind cluster
The repository ships `helm/kind-config.yaml` to keep node configuration
consistent:

```bash
kind delete cluster --name soma-fractal-memory 2>/dev/null || true
kind create cluster --config helm/kind-config.yaml
```

> **Tip:** If Docker’s resource allocation changes, restart Docker Desktop and
> recreate the cluster so the new limits propagate to Kind.

### 3.3 Load images and deploy the Helm chart

```bash
# Load the API/worker image into the Kind node (repeat for any custom builds)
kind load docker-image somatechlat/soma-memory-api:dev-local-20251002 \
   --name soma-fractal-memory

# Install/upgrade the full stack
helm upgrade --install soma-memory ./helm \
   --namespace soma-memory \
   --create-namespace \
   --wait --timeout=600s

# Confirm everything is running
kubectl get pods -n soma-memory
```

For production-grade persistence, pass the hardened override file and adjust
storage classes for your cluster:

```bash
helm upgrade --install soma-memory ./helm \
   --namespace soma-memory \
   --create-namespace \
   --values helm/values-production.yaml \
   --set postgres.persistence.storageClass=standard \
   --set qdrant.persistence.storageClass=standard \
   --set redis.persistence.storageClass=standard \
   --set redpanda.persistence.storageClass=standard \
   --wait --timeout=600s

kubectl get pvc -n soma-memory
```

### 3.4 Expose the API on `localhost:9595`
Use the idempotent helper (it runs `kubectl port-forward` via `nohup`, so it
stays in the background and writes logs to `/tmp/port-forward-*.log` instead of
blocking the terminal):

```bash
./scripts/port_forward_api.sh start
curl -s http://127.0.0.1:9595/healthz | jq .
```

Stop the forward with `./scripts/port_forward_api.sh stop`.

### 3.5 Run the clustered CI checks

```bash
./scripts/run_ci.sh
```

The script waits for the API pod, recreates port-forwards (API, Postgres, Redis,
Qdrant, Redpanda), and runs the pytest suite against the live services. If a pod
is missing, the script prints the failing component and exits non-zero.

### 3.6 Persistence checklist
- Ensure every required PVC is `Bound`:
   ```bash
   kubectl get pvc -n soma-memory
   ```
- Verify Redpanda retains data across restarts by scaling its deployment down
   and back up (`kubectl -n soma-memory scale deploy/soma-memory-somafractalmemory-redpanda --replicas=0/1`).
- For cloud clusters override the `storageClass` values in
   `helm/values-production.yaml` (e.g., `gp3`, `premium-rwo`, `managed-csi`).

---

## 4. Alternative Startup Modes (`scripts/start_stack.sh`)
`start_stack.sh` is a convenience wrapper around `docker-compose.dev.yml`:

| Mode | Services | Notes |
|------|----------|-------|
| `development` | Postgres + Qdrant (optionally Redpanda/Apicurio with `--with-broker`) | Fast to start for local work. |
| `evented_enterprise` / `cloud_managed` | Redpanda, Apicurio, Postgres, Qdrant | Mirrors the evented production setup. |
| `test` | No external services | Unit tests rely on in-memory stores. |

Example usage:
```bash
./scripts/start_stack.sh development --with-broker
```
Follow up with `docker compose up -d api consumer` to launch the application containers against those services.

---

## 5. Configuration Checklist
Key environment variables (see `docs/CONFIGURATION.md` for the full list):
- `MEMORY_MODE` – selects backend wiring.
- `SOMA_MEMORY_NAMESPACE` – logical namespace for the API instance.
- `POSTGRES_URL` – DSN for canonical storage.
- `QDRANT_HOST` / `QDRANT_PORT` (or `qdrant.path` in config) – vector store.
- `KAFKA_BOOTSTRAP_SERVERS` – broker location for event publishing.
- `EVENTING_ENABLED` – set to `false` to disable Kafka emission when Redpanda is absent.
- `SOMA_API_TOKEN` – optional bearer token required by the FastAPI dependencies.
- `SOMA_RATE_LIMIT_MAX` / `SOMA_RATE_LIMIT_WINDOW_SECONDS` – rate limiter budget and window for API endpoints (defaults 60 requests per 60 s).

When running the CLI or FastAPI in-process, you can pass a dictionary to `create_memory_system` to override the same settings:
```python
create_memory_system(
   MemoryMode.EVENTED_ENTERPRISE,
   "namespace",
   config={
      "redis": {"host": "redis", "port": 6379},
      "postgres": {"url": os.environ["POSTGRES_URL"]},
      "qdrant": {"host": "qdrant", "port": 6333},
      "eventing": {"enabled": os.getenv("EVENTING_ENABLED", "true").lower() in ("1", "true", "yes")},
   },
)

Important: keep `UVICORN_PORT=9595` in `.env` (or override the Helm value `env.UVICORN_PORT`) so the API binds to the canonical port used by CI and helper scripts.
```

---

## 6. Testing & Validation
- **Unit tests** – `pytest -q` (no services required).
- **Hybrid store integration** – `pytest -q tests/test_postgres_redis_hybrid_store.py` spins up containers via Testcontainers.
- **Static checks** – `ruff check .`, `black --check .`, `bandit`, and `mypy` mirror the GitHub Actions pipeline.
- **Documentation build** – `mkdocs build` (requires `mkdocs` and `mkdocs-material`).

The FastAPI example regenerates `openapi.json` in the repository root during startup; keep that file committed so docs and CI stay in sync.

---

## 7. Kubernetes Deployment
The Helm chart at `helm/` provisions the full topology (API, consumer, Postgres, Redis, Qdrant, Redpanda). Key values:
- `image.repository` / `image.tag` – override container images.
- `env.*` – configure the API service (mirrors `.env`).
- `consumer.enabled` – toggle the background worker deployment.
- `postgres`, `redis`, `qdrant`, `redpanda` – enable/disable embedded dependencies or point to managed services.

Install (or upgrade) the stack like so:
```bash
kind load docker-image somatechlat/soma-memory-api:dev-local-20251002 \
   --name soma-fractal-memory  # skip on managed clusters

helm upgrade --install soma-memory ./helm \
   --namespace soma-memory \
   --create-namespace \
   --wait --timeout=600s
```

Override the image coordinates and pull policy when deploying to a shared cluster:
```bash
helm upgrade --install soma-memory ./helm \
   --namespace soma-memory \
   --create-namespace \
   --set image.repository=somatechlat/soma-memory-api \
   --set image.tag=v2.1.0 \
   --set image.pullPolicy=IfNotPresent \
   --wait --timeout=600s
```

Add `--values helm/values-production.yaml` (plus `postgres/qdrant/redis/redpanda.persistence` overrides) to enable durable PVCs. Tear down the release with `helm uninstall soma-memory -n soma-memory`.

---

## 8. Clean-Up Matrix
| Goal | Command |
|------|---------|
| Stop containers, keep data | `docker compose down` |
| Stop + delete data volumes | `docker compose down -v` |
| Remove local Qdrant file | `rm -rf qdrant.db` |
| Reset `.env` | Re-copy from `.env.example` |

---

*For detailed configuration keys see `docs/CONFIGURATION.md`. For API surface documentation refer to `docs/api.md`.*

## Production readiness

For a prescriptive production readiness and deployment checklist, see
`docs/PRODUCTION_READINESS.md` which contains build, Helm deployment, schema
compatibility notes, testing guidance and operational best-practices.
