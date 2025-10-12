# SomaFractalMemory – Developer Guide

This guide is aimed at contributors working directly with the codebase. It complements the canonical operations document with day-to-day workflows, pointers to key modules, and troubleshooting tips grounded in the current implementation.

---

## Table of Contents
- [Project Layout](#project-layout)
- [Bootstrapping a Dev Environment](#bootstrapping-a-dev-environment)
- [Running Services](#running-services)
- [CLI & API Usage](#cli--api-usage)
- [Testing & Static Analysis](#testing--static-analysis)
- [Cleaning Up](#cleaning-up)
- [Troubleshooting](#troubleshooting)

---

## Project Layout
| Path | Purpose |
|------|---------|
| `somafractalmemory/` | Core library (factory, enterprise class, interfaces, implementations, CLI). |
| `somafractalmemory/http_api.py` | FastAPI service used for local runs and OpenAPI generation. |
| `eventing/` | Kafka event producer and schema definition. |
| `workers/` | Consumers that reconcile events into Postgres/Qdrant. |
| `scripts/` | Operational helpers (`start_stack.sh`, `run_consumers.py`, etc.). |
| `docs/` | MkDocs source files (kept in sync with the codebase). |
| `tests/` | Unit and integration tests. |

---

## Bootstrapping a Dev Environment

1. **Verify prerequisites** – ensure `docker`, `docker compose`, `python3`, and `curl` are on your `PATH`:
   ```bash
   docker --version
   docker compose version
   python3 --version
   curl --version
   ```
   If any command is missing, follow the installation guidance in `docs/DEVELOPER_ENVIRONMENT.md` before continuing.

2. **Clone and enter the repository**:
   ```bash
   git clone https://github.com/somatechlat/somafractalmemory.git
   cd somafractalmemory
   ```

3. **Create an isolated Python toolchain** – we default to Astral’s `uv` for reproducible installs:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y
   uv sync --extra api --extra events --extra dev
   ```
   `uv sync` resolves and installs all project extras (API, eventing, developer tooling) into `.venv`. Use `uv run …` to execute commands without “activating” the environment manually.

   Fallback (classic venv + pip):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .[api,events,dev]
   ```

4. **Install git hooks** to mirror CI checks locally:
   ```bash
   uv run pre-commit install
   ```

---

## Running Services

SomaFractalMemory exposes two local workflows: the **full Docker Compose stack** and a **scripted lightweight stack**. Most contributors should start with Docker Compose, which mirrors CI and integration test expectations. For shared Kubernetes infra onboarding, follow the canonical playbook appended to `docs/ROADMAP.md` (Docker images and local validation first, then Kubernetes bootstrap and app wire‑up).

Quick path using Make:
- `make help` – discover available targets
- `make prereqs` – verify Docker/Helm/Kind tooling
- `make compose-build && make compose-up` – build and start the local stack
- `make compose-health` – wait for `/healthz`
- `make compose-logs` – tail the API logs
- `make compose-consumer-up` – start the consumer profile
- `make settings` – print detected ports and Helm dev NodePort
- `make runtime-build && make kind-up && make kind-load && make helm-dev-install` – dev Helm slice on NodePort 30797

### Full Stack Topology
```mermaid
flowchart LR
  Client[Client / Agent] -->|HTTP 9595| API[FastAPI Service]
  API -->|write| Postgres[(Postgres)]
  API -->|cache| Redis[(Redis)]
  API -->|vector upsert| Qdrant[(Qdrant)]
  API -->|publish events| Kafka[(Kafka)]
  Consumer[Consumer Worker] -->|read| Kafka
  Consumer -->|reconcile| Postgres
  Consumer -->|index| Qdrant
```

### Docker Compose (evented enterprise stack)

Follow these steps every time you want a clean local cluster:

1. **Build or refresh images** (only required after changing Python code or dependencies):
   ```bash
   docker compose build
   ```

2. **Start the core services** (API, Kafka, Postgres, Redis, Qdrant):
   ```bash
   make compose-up
   ```

3. **Tail logs until the API reports ready** – this waits for Kafka and database connectivity before proceeding:
   ```bash
   make compose-logs
   ```
   Look for `Application startup complete.`. Press `Ctrl+C` to stop tailing; containers keep running.

4. **(Optional) Start the consumer profile** if you need asynchronous reconciliation:
   ```bash
   make compose-consumer-up
   ```

5. **Validate the cluster**:
   ```bash
   make compose-health
   curl -s http://localhost:9595/readyz | jq .
   docker compose exec postgres pg_isready -U postgres
   curl -s http://localhost:6333/metrics >/dev/null
   ```
   A `true` response from `/healthz` and `/readyz` confirms API readiness. `pg_isready` should reply `accepting connections`.

6. **Stop services when finished**:
   ```bash
   make compose-down             # keep volumes
   make compose-down-v           # remove volumes/data
   ```

Fixed host ports (aligns with test fixtures and examples):
- API: `http://localhost:9595`
- Postgres: `localhost:5433`
- Redis: `localhost:6381`
- Qdrant: `localhost:6333`
- Kafka (external listener): `localhost:19092`

Declarative configuration lives in `docker-compose.yml`. Override values ad hoc with `docker compose up -d api -e MEMORY_MODE=development` or by creating a `.env` file; environment variables take precedence over defaults baked into the compose file.

### Kubernetes via Helm (dev and prod)

For day-to-day dev against Kubernetes, use the bundled Helm chart (`helm/`). The canonical API port is 9595. For the current dev slice we also ship a values file that runs the API on 9797 and exposes it via a NodePort mapped to 30797 on your host.

- Default values: `helm/values.yaml` (ClusterIP on 9595 inside the cluster)
- Dev override: `helm/values-dev-port9797.yaml` (API 9797, service.type NodePort, nodePort 30797, eventing disabled)

Quick start on Kind (example):
```bash
# Create Kind, build runtime, load image, install Helm dev release
make kind-up
make runtime-build
make kind-load
make helm-dev-install

# Verify health via NodePort on the host
make helm-dev-health
```

Notes:
- To expose the default 9595 without NodePort, use `kubectl port-forward svc/<release>-somafractalmemory 9595:9595` or the helper script `./scripts/port_forward_api.sh`.
- To use an ingress instead, set `ingress.enabled=true` and provide an ingress class and host in values; see the chart comments in `helm/values.yaml`.

### Data persistence (volumes)

- Docker Compose: volumes are declared for Postgres (`postgres_data`), Redis (`redis_data` with AOF enabled), Qdrant (`qdrant_storage`), and Kafka (`kafka_data`). They persist across `docker compose down` and are only removed with `docker compose down -v`.
- Kubernetes/Helm: by default the chart disables persistence for local convenience. For durable local runs, either:
   - enable persistence in values (recommended for real clusters):
      ```yaml
      postgres.persistence:
         enabled: true
         size: 10Gi
         storageClass: standard
      redis.persistence:
         enabled: true
         size: 5Gi
      qdrant.persistence:
         enabled: true
         size: 10Gi
      redpanda.persistence:
         enabled: true
         size: 10Gi
      ```
   - or apply the static hostPath PVs/PVCs under `k8s/pvcs.yaml` for Kind-only local development.

Backups and disaster recovery are out of scope for local dev. For production, use managed Postgres/Qdrant/Kafka or provision stateful sets with replicated storage, scheduled backups, and tested restore procedures (see Production Readiness).

### Minimal backends via `start_stack.sh`

Use this path when you only need the API plus storage without Kafka:
```bash
./scripts/start_stack.sh development                 # Postgres + Qdrant
./scripts/start_stack.sh development --with-broker   # Adds Kafka
./scripts/start_stack.sh evented_enterprise          # Full parity with compose
```
The script prints connection strings for each component. After it completes, run the example API with auto‑reload:
```bash
uv run uvicorn somafractalmemory.http_api:app --reload --host 0.0.0.0 --port 9595
```

---

## CLI & API Usage
### CLI (`soma`)
The CLI wraps `create_memory_system` and exposes commands for storing, recalling, and exporting memories. Example:
```bash
soma --mode development --namespace cli_demo store \
  --coord "1,2,3" \
  --payload '{"task": "triage", "importance": 3}'
```
Supply `--config-json` to point at a JSON file mirroring the `config` dictionary structure (`redis`, `postgres`, `qdrant`, `eventing`, `memory_enterprise`).

### FastAPI Example
Run the example app directly for rapid iteration:
```bash
uvicorn somafractalmemory.http_api:app --reload
```
On startup it:
- Creates a development-mode memory system (`redis.testing=True`, Qdrant pointed at the configured host/port).
- Generates `openapi.json` in the repository root.
- Publishes Prometheus metrics and rate limits using environment defaults.

Important endpoints: `/store`, `/recall`, `/remember`, `/store_bulk`, `/link`, `/neighbors`, `/shortest_path`, `/stats`, `/metrics`, `/healthz`, `/readyz`.

---

## Testing & Static Analysis
| Command | What it does |
|---------|---------------|
| `uv run pytest -q` | Runs the fast suite (unit + lightweight integration) – in-memory / fakeredis paths where applicable. |
| `USE_REAL_INFRA=1 uv run pytest -q` | Runs the full suite against the live Docker Compose services (Kafka, Postgres, Redis, Qdrant). |
| `uv run pytest -m integration -q` | Run only tests marked as requiring real infra (ensure `USE_REAL_INFRA=1` and stack is up). |
| `uv run pytest tests/test_full_stack_enterprise_round_trip.py -q` | End‑to‑end persistence test (KV + vector + WAL absence + locks). |
| `uv run pytest tests/test_kafka_event_flow.py -q -m integration` | Verifies Kafka events are emitted & consumable (EVENTED_ENTERPRISE). |
| `uv run ruff check .` | Linting (mirrors CI). |
| `uv run black --check .` | Formatting check. |
| `uv run bandit -q -r somafractalmemory` | Security scan of the library. |
| `uv run mypy somafractalmemory` | Static type checking. |
| `uv run mkdocs build` | Validates that documentation builds successfully. |

### Real Infra Test Mode
Setting `USE_REAL_INFRA=1` signals fixtures to bind directly to the running Docker Compose services instead of launching ephemeral testcontainers. Export it once in your shell to keep the behaviour consistent:
```bash
export USE_REAL_INFRA=1
```
Unset the variable to fall back to testcontainers (requires Docker socket access). The suite filters most third‑party deprecation warnings automatically.

### Runtime vs Development Images
The default `Dockerfile` is development-oriented (includes tests, docs, build toolchain). For
Kubernetes/Helm or slimmer production packaging use the multi-stage runtime image:
```bash
docker build -f Dockerfile.runtime -t somafractalmemory-runtime:local .
```
Helm `values.yaml` can then reference `somafractalmemory-runtime` for both API and consumer components.

All of the above run automatically in GitHub Actions (`.github/workflows/ci.yml`).

---

## Cleaning Up
- Stop containers and keep data: `docker compose down`
- Stop and purge data volumes: `docker compose down -v`
- Remove the local Qdrant database used by tests or quickstarts: `rm -rf qdrant.db`
- Reset the environment file: re-copy `.env.example`

---

## Troubleshooting
**Postgres port conflicts** – The compose files expose Postgres on `5433`; ensure `.env` references that port when connecting from the host.

**Redis connection errors during development** – If you only need in-memory mode, set `REDIS_HOST=localhost` and `redis.testing=true` in your config to force `fakeredis`.

**Kafka optional for some modes** – Set `EVENTING_ENABLED=false` and avoid running the consumer if you only need synchronous store/recall APIs. For full enterprise coverage (vector + event reconciliation) leave it enabled.

**NodePort vs. port-forward** – When using the dev Helm values on Kind, access the API at `http://127.0.0.1:30797` (service port 9797). In other clusters, prefer an ingress with TLS for external access.

**Integration tests use existing services** – With `USE_REAL_INFRA=1`, tests reuse the running Postgres/Redis/Qdrant/Kafka instead of spinning up disposable containers; ensure compose stack is healthy before running.

**OpenTelemetry warnings** – When the collector endpoint is absent, set `OTEL_TRACES_EXPORTER=none` to silence connection errors.

---

*Refer back to `docs/CANONICAL_DOCUMENTATION.md` for deployment-focused instructions and `docs/api.md` for method-level details.*
