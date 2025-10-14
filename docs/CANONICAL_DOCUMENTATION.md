# Canonical Documentation for SomaFractalMemory

This document is the operational source of truth for developers and operators. It consolidates the steps required to run the stack locally, configure services, and keep documentation builds up to date.

---

## 1. Prepare the Environment
1. (Preferred) Use uv for a fast, reproducible environment:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y
   uv sync --extra api --extra events --extra dev
   ```
    Or create a classic venv and install editable:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -e .[api,events,dev]
    ```
2. When running the CLI or scripts directly, set environment variables in your shell (`export`), not via `.env`. Docker Compose inlines container env blocks; adjust `docker-compose.yml` (or an override file) for container settings.

---

## 2. Build and Run the Stack
1. **Canonical entrypoint (Compose)** with automatic port assignment:
   ```bash
   make setup-dev
   # OR directly:
   ./scripts/assign_ports_and_start.sh
   ```
   This will:
   - Automatically detect and resolve port conflicts
   - Assign free ports to infrastructure services
   - Start the complete evented enterprise stack
   - Display final port assignments

2. **Manual deployment** (if you need custom control):
   ```bash
   docker compose --profile core up -d
   ```

3. **Access endpoints**:
   * Memory API: <http://localhost:9595> (fixed)
   * Infrastructure ports: Auto-assigned (displayed at startup)
   * Prometheus metrics: `/metrics`
   * Swagger UI: `/docs`
4. (Tip) Check current port assignments: `cat .env`

5. **Stop services** while preserving data:
   ```bash
   make compose-down
   ```
6. **Wipe volumes** when you need a clean slate:
   ```bash
   make compose-down-v
   ```

Named volumes created by the compose file: `redis_data`, `qdrant_storage`, `postgres_data`, `kafka_data`.

### Troubleshooting: consumer ModuleNotFoundError

Symptom: the consumer container repeatedly restarts with a traceback like:

   ModuleNotFoundError: No module named 'common'

Cause: when the consumer is executed as an entrypoint inside the image, the repository root may not be on Python's `sys.path` prior to local imports. This manifests only when running the consumer from source inside the container (bind-mounted code) or when the image's Python path is not configured.

Resolution (applied in this release):
1. Ensure the project root is appended to `sys.path` at the top of `scripts/run_consumers.py` before any local imports. The repository now contains a small fix which does this automatically.
2. Rebuild and restart the consumer image:

```bash
docker compose build somafractalmemory_kube
docker compose up -d somafractalmemory_kube
```

3. Verify consumer health and metrics (run inside the consumer container):

```bash
docker compose exec somafractalmemory_kube curl -sS http://localhost:8001/metrics | head -n 40
docker compose --profile consumer logs --tail 200 somafractalmemory_kube
```

If the consumer is still failing, inspect the logs for the first exception; network-related errors (Kafka not reachable) will show earlier in the logs and should be addressed by checking `KAFKA_BOOTSTRAP_SERVERS` and the broker container status.


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
make setup-dev-k8s
```

For production-grade persistence, pass the hardened override file and adjust
storage classes for your cluster (see [§ 9 Storage & Persistence Reference](#9-storage--persistence-reference)
for a detailed breakdown of each volume):

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

### 3.4 Expose or verify the API locally
Use the idempotent helper (it runs `kubectl port-forward` via `nohup`, so it
stays in the background and writes logs to `/tmp/port-forward-*.log` instead of
blocking the terminal):

```bash
make helm-dev-health   # NodePort 30797 in the dev slice
# or port-forward the default service port 9595
./scripts/port_forward_api.sh start && curl -s http://127.0.0.1:9595/healthz | jq .
```

Stop the forward with `./scripts/port_forward_api.sh stop`.

### 3.5 Run the clustered CI checks

```bash
make ci-verify-k8s
```

The script waits for the API pod, recreates port-forwards (API, Postgres, Redis,
Qdrant, Kafka), and runs the pytest suite against the live services. If a pod
is missing, the script prints the failing component and exits non-zero.

### 3.6 Persistence checklist
- Ensure every required PVC is `Bound`:
   ```bash
   kubectl get pvc -n soma-memory
   ```
- Verify the broker retains data across restarts by scaling its deployment down
   and back up. If your deployment still uses a `redpanda`-named deployment for
   backward compatibility, patch that; otherwise patch the Kafka deployment.
- For cloud clusters override the `storageClass` values in
   `helm/values-production.yaml` (e.g., `gp3`, `premium-rwo`, `managed-csi`).
- Review [§ 9 Storage & Persistence Reference](#9-storage--persistence-reference) for Docker volume locations,
  Helm flags, and backup strategies.

---

## 4. Startup Mode (`scripts/start_stack.sh`)
`start_stack.sh` now enforces the canonical evented topology and refuses any other mode. It wires Postgres, Qdrant, and (optionally via `--with-broker`) Kafka so local runs mirror production.

Example usage:
```bash
./scripts/start_stack.sh evented_enterprise --with-broker
```
Follow up with `make compose-up` and `make compose-consumer-up` (or the equivalent `docker compose` commands) to launch the application containers against those services.

---

## 5. Configuration Checklist
Key environment variables (see `docs/CONFIGURATION.md` for the full list):
- `MEMORY_MODE` – fixed to `evented_enterprise`; CLI/API will override any other value.
- `SOMA_MEMORY_NAMESPACE` – logical namespace for the API instance.
- `POSTGRES_URL` – DSN for canonical storage.
- `POSTGRES_HOST_PORT` – host port for PostgreSQL (auto-assigned if conflicts detected).
- `REDIS_HOST_PORT` – host port for Redis cache (auto-assigned if conflicts detected).
- `QDRANT_HOST_PORT` – host port for Qdrant vector store (auto-assigned if conflicts detected).
- `KAFKA_HOST_PORT` – host port for Kafka broker (auto-assigned if conflicts detected).
- `KAFKA_OUTSIDE_PORT` – external Kafka port (auto-assigned if conflicts detected).
- `KAFKA_BOOTSTRAP_SERVERS` – broker location for event publishing.
- `EVENTING_ENABLED` – set to `false` to disable Kafka emission when a broker is absent.
- `SOMA_API_TOKEN` – required bearer token enforced by every API surface (set via env or secret mount).
- `SOMA_RATE_LIMIT_MAX` / `SOMA_RATE_LIMIT_WINDOW_SECONDS` – rate limiter budget and window for API endpoints (defaults 60 requests per 60 s).

Production helm deployments should start from `helm/values-production.yaml`, which disables inline secrets, enables the ExternalSecret template, and adds the Reloader annotations so credentials sourced from Vault trigger rollouts automatically.

When running the CLI or FastAPI in-process, you can pass a dictionary to `create_memory_system` to override the same settings while always using `MemoryMode.EVENTED_ENTERPRISE`:
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
- **Documentation build** – `make docs-build` (requires `mkdocs` and `mkdocs-material`), `make docs-serve` to preview locally.

### 6.1 Async gRPC server (new)

This project now provides an asyncio-based gRPC server implementation alongside
the legacy synchronous server. The async server lives at
`somafractalmemory.async_grpc_server` and uses `grpc.aio` with async adapters
for Redis (`redis.asyncio`) and Postgres (`asyncpg`). Qdrant calls currently use
the official (sync) `qdrant-client` wrapped via `asyncio.to_thread`.

Key points:
- Listen port: 50053 (default, container exposure added in `Dockerfile`)
- Handlers: Store, Recall, Delete, Health
- Storage: `AsyncRedisKeyValueStore`, `AsyncPostgresKeyValueStore` in
   `somafractalmemory.implementations.async_storage`
- Tracing: optional OpenTelemetry support; `common/utils/trace.configure_tracer`
   will be used if OTLP packages are installed and configured.

Integration test quick-run (from project root):

```bash
# Start required infra via Docker Compose (if not already running)
docker compose up -d postgres qdrant redis

# Start the async gRPC server locally (in venv)
source .venv/bin/activate
python -m somafractalmemory.async_grpc_server &

# Run the client integration test (Health, Store, Recall, Delete)
python - <<'PY'
import asyncio
from somafractalmemory import memory_pb2, memory_pb2_grpc
import grpc
from google.protobuf import empty_pb2

async def run():
   async with grpc.aio.insecure_channel('localhost:50053') as ch:
            stub = memory_pb2_grpc.MemoryServiceStub(ch)
            print('Health:', (await stub.Health(empty_pb2.Empty())).status)
            coord = memory_pb2.Coordinate(values=[0.1,0.2,0.3])
            mem = memory_pb2.Memory(coord=coord, payload_json='{"ok": true}', memory_type='memories')
            store = await stub.Store(memory_pb2.StoreRequest(memory=mem))
            print('Store ok:', store.ok)
            await asyncio.sleep(0.5)
            r = await stub.Recall(memory_pb2.RetrieveRequest(query=coord, top_k=3))
            print('Recall count:', len(r.memories))
            print('Deleting...')
            await stub.Delete(memory_pb2.DeleteRequest(coord=coord))
            print('Done')

asyncio.run(run())
PY
```

If the client returns `Health: ok`, `Store ok: True` and `Recall count: >=1`,
the async codepath is functioning against the dockerized infra.


The FastAPI example serves OpenAPI at `/openapi.json`; if you need to regenerate a committed `openapi.json`, run `uv run python scripts/generate_openapi.py`.

---

## 7. Kubernetes Deployment
The Helm chart at `helm/` provisions the full topology (API, consumer, Postgres, Redis, Qdrant, Kafka). Key values:
- `image.repository` / `image.tag` – override container images.
- `env.*` – configure the API service (mirrors `.env`).
- `consumer.enabled` – toggle the background worker deployment.
- `postgres`, `redis`, `qdrant`, `redpanda` – enable/disable embedded dependencies or point to managed services. The broker block may still be named `redpanda` for backward compatibility even when using a Confluent Kafka image.

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

## 9. Storage & Persistence Reference

Use this section to locate stateful data across Docker Compose, Helm, and the raw Kubernetes manifests, and to plan backups for each environment.

### 9.1 Docker Compose stacks

**Primary stack (`docker-compose.yml`)**

| Service | Docker volume | Container mount | Purpose |
| --- | --- | --- | --- |
| `redis` | `redis_data` | `/data` | Redis append-only file (AOF). |
| `qdrant` | `qdrant_storage` | `/qdrant/storage` | Vector index collections. |
| `postgres` | `postgres_data` | `/var/lib/postgresql/data` | PostgreSQL data directory. |
| `kafka` | `kafka_data` | `/var/lib/kafka/data` | KRaft log segments and metadata. |

- The API and worker containers are stateless; durability lives in the services above.
- Docker manages the volumes; back up with `docker run --rm -v <name>:/data busybox tar -C /data -cf backup.tar .`.

Development & Test overlays

Historically the repo used multiple compose override files (`docker-compose.dev.yml`, `docker-compose.test.yml`) to provide development bind mounts and isolated test infra. Those overlays have been consolidated into the single canonical `docker-compose.yml` using Compose profiles (`dev`, `test`, `core`, `shared`, `consumer`, `monitoring`, `ops`).

Use the `dev` or `test` profiles when you need bind mounts, an isolated test stack, or a different set of services. For example:

```bash
# Start the full development stack (auto-assigned infra ports):
make setup-dev

# Start only the test profile (isolated test infra):
docker compose --profile test up -d

# Start only the development profile (hot-reload mounts):
docker compose --profile dev up -d
```

Named volumes still isolate persistent data for the stack (`postgres_data`, `redis_data`, `qdrant_storage`, `kafka_data`). Use `docker compose down -v` to wipe them when you need a clean slate.

### 9.2 Raw Kubernetes manifests (`k8s/`)

The baseline manifests target single-node Kind clusters with `hostPath` persistent volumes:

| Component | PVC | Host path |
| --- | --- | --- |
| PostgreSQL | `pvc-postgres` | `/var/lib/somafractalmemory/postgres` |
| Redis | `pvc-redis` | `/var/lib/somafractalmemory/redis` |
| Qdrant | `pvc-qdrant` | `/var/lib/somafractalmemory/qdrant` |

These host-local paths survive pod restarts but are node-bound. Backups require copying data from the Kind node (for example, `docker cp <node>:/var/lib/somafractalmemory/postgres ./backup`). Reserve this setup for local testing, not production clusters.

### 9.3 Helm chart (`helm/`)

Persistence toggles live under `*.persistence.enabled`. Defaults keep everything ephemeral (`emptyDir`) in `values.yaml`, while `values-production.yaml` enables PVCs and larger sizes.

| Component | Values key | Default | Production override |
| --- | --- | --- | --- |
| PostgreSQL | `postgres.persistence.enabled` | `false` | `true`, 50 Gi |
| Redis | `redis.persistence.enabled` | `false` | `true`, 20 Gi |
| Qdrant | `qdrant.persistence.enabled` | `false` | `true`, 200 Gi |
| Redpanda/Kafka | `redpanda.persistence.enabled` | `false` | `true`, 200 Gi |

Enable PVCs with:

```bash
helm upgrade --install soma-memory ./helm \
   -n soma-memory \
   --values helm/values-production.yaml \
   --set postgres.persistence.storageClass=fast-ssd \
   --set qdrant.persistence.storageClass=fast-ssd \
   --set redpanda.persistence.storageClass=throughput \
   --wait
```

Templates create PVCs named `<release>-<component>-data` (or `-storage`). Specify storage classes that match your cloud or on-prem tier.

### 9.4 Backup & inspection tips

- **Docker named volumes** – `docker run --rm -v <vol>:/data busybox ls /data` to inspect, `tar` for full backups.
- **HostPath PVs** – exec into pods for logical dumps (`pg_dump`, `redis-cli --rdb`, Qdrant exports) or copy data directly from the host path.
- **Helm PVCs** – rely on storage snapshots or scheduled backup jobs inside the cluster; document `kubectl exec` workflows for Postgres and Qdrant.

### 9.5 Recommended follow-ups

1. **Local dev:** document volume backup commands in onboarding and add a `make clean-volumes` helper to prune stale volumes when resetting the stack.
2. **Production:** deploy with `helm/values-production.yaml`, override storage classes, and ensure a backup policy exists for each PVC.
3. **Testing:** keep test compose volumes isolated; prune them automatically in CI after each run.
4. **Monitoring:** track disk usage across Redis/Postgres/Qdrant/Kafka volumes and alert at 80 % utilization.

---

*For detailed configuration keys see `docs/CONFIGURATION.md`. For API surface documentation refer to `docs/api.md`.*

## Production readiness

For a prescriptive production readiness and deployment checklist, see
`docs/PRODUCTION_READINESS.md` which contains build, Helm deployment, schema
compatibility notes, testing guidance and operational best-practices.
