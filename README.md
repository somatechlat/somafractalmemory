# Soma Fractal Memory (SFM)

---

## 📖 Overview
**Soma Fractal Memory (SFM)** is a modular, agent-centric memory system written in Python. It exposes a single interface for storing, recalling, and linking **episodic** and **semantic** memories across Redis, PostgreSQL, Qdrant, and Kafka/Redpanda-backed pipelines. The system is designed for AI agents, knowledge-graph pipelines, and any workload that needs fast, context-aware recall of prior events.

---

## 🏗️ Architecture
```
+-------------------+      +-------------------+      +-------------------+
|   FastAPI API    | <-> |   OpenAPI / Docs  | <-> |   CLI (soma)      |
+-------------------+      +-------------------+      +-------------------+
        |                         |                         |
        v                         v                         v
+-------------------+   +-------------------+   +-------------------+
|   Redis Cache     |   |   PostgreSQL KV   |   |   Qdrant Vectors |
+-------------------+   +-------------------+   +-------------------+
        ^                         ^                         ^
        |                         |                         |
+-------------------+   +-------------------+   +-------------------+
|   Kafka Broker    |   |  Worker Consumers |   |  Event Schema    |
+-------------------+   +-------------------+   +-------------------+
```

* **FastAPI (`examples/api.py`)** – HTTP server exposing memory, graph, and admin endpoints plus Prometheus metrics.
* **CLI (`soma` command)** – Thin wrapper around the same factory for scripting and batch jobs.
* **Redis** – Optional low-latency cache and distributed lock store for recent episodic memories.
* **PostgreSQL** – Canonical key-value store for durable JSON payloads.
* **Qdrant** – Approximate nearest-neighbour vector store for semantic embeddings.
* **Kafka** – Event bus carrying `memory.events` for asynchronous processing. (Docker Compose now uses a single Confluent Kafka KRaft broker; earlier revisions shipped Redpanda.)
* **Workers (`scripts/run_consumers.py`)** – Consume events, update Postgres/Qdrant, and expose their own Prometheus metrics.

---

## ⚙️ Settings & Configuration
These are the key environment variables consumed by the API, CLI, and consumer processes. The Docker Compose stack sets them inline in `docker-compose.yml`; copy `.env.example` when you need them available to local scripts or direct process runs.

| Variable | Description | Default / Example |
|----------|-------------|--------------------|
| `MEMORY_MODE` | Selects backend wiring. Options: `development`, `test`, `evented_enterprise`, `cloud_managed`. | `development` |
| `SOMA_MEMORY_NAMESPACE` | Namespace injected into `create_memory_system` (defaults to `api_ns`). | `api_ns` |
| `POSTGRES_URL` | Full DSN for PostgreSQL (used by API, CLI, and workers). | `postgresql://postgres:postgres@postgres:5433/somamemory` |
| `REDIS_URL` / `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` | Redis connection hints; host/port/db win over URL when provided. | `redis://redis:6379/0` |
| `QDRANT_URL` or (`QDRANT_HOST`, `QDRANT_PORT`) | Qdrant endpoint for vector search. | `http://qdrant:6333` |
| `EVENTING_ENABLED` | When set to `false`, disables Kafka publishing by wiring `eventing.enabled=False` in the factory. | `true` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka bootstrap servers consumed by API and consumers. | `kafka:9092` |
| `SOMA_API_TOKEN` | Optional bearer token enforced by the FastAPI dependencies. | *(unset)* |
| `SOMA_RATE_LIMIT_MAX` | Requests per minute per endpoint for the sample API (set `0` to disable throttling). | `60` |
| `SOMA_RATE_LIMIT_WINDOW_SECONDS` | Sliding window (seconds) for the rate limiter buckets. | `60` |
| `UVICORN_PORT` | Exposed port for the API process (kept at `9595` in charts and Compose). | `9595` |
| `UVICORN_WORKERS` / `UVICORN_TIMEOUT_GRACEFUL` / `UVICORN_TIMEOUT_KEEP_ALIVE` | Process tuning knobs honoured by `scripts/docker-entrypoint.sh`. | `4` / `60` / `30` |
| `POSTGRES_POOL_SIZE` | Reserved for future async session pooling (exported in Helm values but currently unused). | *(n/a)* |
| `SKIP_SCHEMA_VALIDATION` / `VECTOR_INDEX_ASYNC` | Present in Helm defaults for forward compatibility; not consumed by the FastAPI example yet. | *(n/a)* |

Create an environment file by copying the template shipped with the repo:
```bash
cp .env.example .env
# then edit values as needed
```

Advanced tuning is documented in `docs/CONFIGURATION.md`.

---

## 📦 Installation
### 1️⃣ Python with uv (recommended)
Use Astral’s uv for fast, reproducible installs. No manual venv activation is required—`uv run` handles it.

```bash
# Install uv (once)
curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y
uv --version

# Sync runtime dependencies for API + events (Kafka)
uv sync --extra api --extra events

# Optional: include developer tools
uv sync --extra dev --extra api --extra events

# Verify CLI
uv run soma --help
```

Fallback: Classic venv + pip
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```
The uv path is preferred for reliability and speed.

### 2️⃣ Docker Compose (full stack)
```bash
# Build images after local changes
docker compose build

# Start Redis, Postgres, Qdrant, Kafka (single Confluent broker), API, and workers
docker compose up -d
```
The API listens on **http://localhost:9595**. Start the background consumer with `docker compose --profile consumer up -d somafractalmemory_kube`. A sandbox copy runs on **http://localhost:8888** when the `test_api` service is started.

---

## 🚀 Running & Dynamic Configuration
* **Minimal local services** – Start just Postgres and Qdrant for development:
  ```bash
  ./scripts/start_stack.sh development
  docker compose up -d api
  ```
* **Add Kafka** – Include the broker by passing `--with-broker` to `start_stack.sh` (legacy flag; compose already defines the `kafka` service), or simply run the full compose stack.
* **Full parity stack** – Mirror production wiring with Kafka and workers:
  ```bash
  ./scripts/start_stack.sh evented_enterprise
  docker compose up -d api
  docker compose --profile consumer up -d somafractalmemory_kube
  ```
* **Environment changes** – Adjust the environment block in `docker-compose.yml` (or an override file), then restart the affected services. For example: `docker compose up -d api` and `docker compose --profile consumer up -d somafractalmemory_kube`.
* **Stopping** – Preserve data with named volumes:
  ```bash
  docker compose down
  ```
* **Full wipe (remove volumes)** – Useful for a clean slate:
  ```bash
  docker compose down -v
  ```

> ℹ️  The FastAPI example writes `openapi.json` to the repository root at startup for documentation builds.

---

## ☸️ Kubernetes Deployment
The Helm chart in `helm/` deploys the API, consumer, and all backing services into a namespace (defaults to `soma-memory`). The default `values.yaml` is tuned for local Kind clusters: it pins the application image to `somatechlat/soma-memory-api:dev-local-20251002` and uses `image.pullPolicy=Never` so the node consumes the image you loaded with `kind load`.

```bash
# Load the local image into Kind (skip when pointing at a remote registry)
kind load docker-image somatechlat/soma-memory-api:dev-local-20251002 \
  --name soma-fractal-memory

helm upgrade --install soma-memory ./helm \
  --namespace soma-memory \
  --create-namespace \
  --wait --timeout=600s

kubectl get pods -n soma-memory
```

When deploying to a real cluster, override the image coordinates and pull policy:

```bash
helm upgrade --install soma-memory ./helm \
  --namespace soma-memory \
  --create-namespace \
  --set image.repository=somatechlat/soma-memory-api \
  --set image.tag=v2.1.0 \
  --set image.pullPolicy=IfNotPresent \
  --wait --timeout=600s
```

Durable storage defaults live in `helm/values-production.yaml`. Apply them (and set `storageClass` values) to keep Postgres, Redis, Qdrant, and broker data across pod restarts (Helm values still label the broker section `redpanda` for backward compatibility):

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
```

Expose the API locally with the idempotent helper (wraps `kubectl port-forward` and keeps logs under `/tmp/port-forward-*.log`):

```bash
./scripts/port_forward_api.sh start
curl -s http://127.0.0.1:9595/healthz | jq .
./scripts/port_forward_api.sh stop
```

The chart renders Deployments for the API, consumer, Redis, Qdrant, Postgres, and the Kafka broker (value block still named `redpanda`), plus PVCs when persistence is enabled. Environment variables match the table above; consult `docs/CANONICAL_DOCUMENTATION.md` for the full day-two workflow and `docs/PRODUCTION_READINESS.md` for a production checklist.

---

## 📡 API Highlights
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/store` | Persist a memory (coordinate + payload). |
| `POST` | `/recall` | Recall top matches for a text query (hybrid semantic + keyword; default). |
| `POST` | `/recall_batch` | Issue multiple recall queries in one call. |
| `POST` | `/store_bulk` | Bulk-ingest memories from a payload list. |
| `POST` | `/recall_with_scores` | Return matches with similarity scores; add `hybrid=true` for hybrid scoring. |
| `POST` | `/recall_with_context` | Context-aware hybrid recall with caller filters. |
| `GET`  | `/range` | Find memories whose coordinates fall within a bounding box. |
| `POST` | `/link` | Create a semantic edge between two coordinates. |
| `GET`  | `/neighbors` | Inspect graph neighbours for a coordinate. |
| `GET`  | `/shortest_path` | Compute the graph shortest path between two coordinates. |
| `GET`  | `/stats` | Return memory counts and backend health. |
| `GET`  | `/metrics` | Prometheus metrics for the API (see Observability). |
| `GET`  | `/health` | Combined health report (without auth). |
| `GET`  | `/healthz` / `/readyz` | Liveness/readiness checks for Kubernetes probes. |
| `GET`  | `/` | Simple banner that links to `/metrics`. |

Swagger UI is available at **`/docs`**, and the generated spec is published as `openapi.json` in the repo root each time the API boots.

For detailed endpoint-by-endpoint usage, parameters, and examples, see `docs/USAGE_GUIDE.md`.

---

## 🧪 Testing & CI
* **Unit tests** – `pytest -q` can use lightweight in-memory/ephemeral paths.
* **Integration & E2E** – Full infra tests (e.g., `tests/test_full_infra_e2e.py`) exercise API → Kafka → consumer → Postgres/Qdrant/Redis with `USE_REAL_INFRA=1`.
* **CI** – GitHub Actions run pytest, Ruff, Black, Bandit, mypy, and build the MkDocs documentation.
* **Pre-commit** – A `.pre-commit-config.yaml` is provided; run `pre-commit install` to mirror the GitHub checks locally.

---

## 🏎️ Benchmarks (Fast Core vs Legacy Path)
The repository ships a lightweight, repeatable smoke benchmark comparing the legacy vector store recall path with the in‑process fast core flat index (`SFM_FAST_CORE=1`).

Run locally (hash embeddings for determinism):
```bash
export SOMA_FORCE_HASH_EMBEDDINGS=1
python benchmarks/fast_core_smoke.py --n 2000 --q 50
```
Output reports p50/p95/p99 latency (in milliseconds) for both paths and the speedup factor. Use this as a relative regression detector—absolute numbers vary by hardware.

Toggling fast core inside code/tests:
```bash
export SFM_FAST_CORE=1  # enable flat slab index
pytest -k fast_core_math -q
```

Math & invariants are defined in `docs/FAST_CORE_MATH.md` (scoring = `max(0, cosine) * importance_norm`).

---

## 🧪 Synthetic runs (real stack, no mocks)
Use the built-in synthetic runner to measure correctness and latency against the live API. It never spins up containers; ensure your stack is running and healthy on 9595 (or pass `--base-url`).

Quick run:
```bash
python scripts/synthetic_real_stack_benchmark.py --N 2000 --Q 400 --top-k 5 --batch-size 200
```

With explicit base and JSON report:
```bash
python scripts/synthetic_real_stack_benchmark.py \
  --base-url http://127.0.0.1:9595 \
  --N 5000 --Q 500 --top-k 5 --out benchmark.json
```

Outputs include: insert throughput, query QPS, latency p50/p90/p95/p99 (ms), Recall@K, and MRR. Authentication is honored when `SOMA_API_TOKEN` is set.

For methodology and troubleshooting, see `docs/CANONICAL_DOCUMENTATION.md#61-synthetic-runs-on-real-servers-no-mocks`.

---

## � Hybrid Recall (Default) and Keyword Search
SFM recalls are hybrid by default: vector similarity is combined with keyword/phrase boosts so exact literals (IDs, tokens, names, quoted phrases) surface above purely semantic neighbors when present.

- Toggle default via environment: `SOMA_HYBRID_RECALL_DEFAULT=1|0` (default `1`).
- Force hybrid per-call (no route changes):
  - `/recall` body flag: `{ "query": "...", "hybrid": true }`
  - `/recall_with_scores?query=...&hybrid=true`
- Matching controls for hybrid and keyword endpoints:
  - `exact=true|false` (default true), `case_sensitive=true|false` (default false)

PostgreSQL JSONB + trigram indexes accelerate substring search when `POSTGRES_URL` is configured. On startup the API attempts to enable `pg_trgm` and create supporting indexes; if permissions are restricted, it falls back to in-memory scanning.

Examples
```bash
# Default recall (hybrid is default)
curl -sS -X POST http://127.0.0.1:9595/recall \
  -H 'Content-Type: application/json' \
  -d '{"query":"amaguaña and baudelaire","top_k":10}' | jq .

# Force hybrid scoring with scores and substring boosts
curl -sS -X POST "http://127.0.0.1:9595/recall_with_scores?query=0xb3a6e0719442594&top_k=10&hybrid=true&exact=false" | jq .

# Exact keyword search (no vectors)
curl -sS -X POST http://127.0.0.1:9595/keyword_search \
  -H 'Content-Type: application/json' \
  -d '{"term":"Aagu1OCoQd","exact":true,"top_k":20}' | jq .
```

---

## �📈 Observability & Eventing
* **Prometheus metrics** – The API exports `api_requests_total`, `api_request_latency_seconds`, and `http_404_requests_total` on `/metrics`. Hit at least one endpoint after startup so counters appear. The consumer process serves `consumer_*` counters on `http://localhost:8001/metrics`.
* **OpenTelemetry** – Optional instrumentation for FastAPI wires in via `opentelemetry-instrumentation-fastapi`. Configure exporters with the standard OTEL environment variables; when the packages are absent, instrumentation is a no-op.
* **Langfuse** – Credentials load from Dynaconf (`config.yaml`) or the `SOMA_LANGFUSE_*` environment variables. Without the package installed, the stub simply drops events.
* **Kafka events** – `eventing/producer.py` validates payloads against `schemas/memory.event.json` before publishing to the `memory.events` topic. Set `EVENTING_ENABLED=false` to disable publishing when running without a broker.

---

## 🔧 Extending the System
1. **New vector store** – Implement `IVectorStore` (see `somafractalmemory/interfaces/storage.py`) and register it in `factory.create_memory_system`.
2. **Alternative KV backends** – Implement `IKeyValueStore` and compose it in the factory; the included `PostgresRedisHybridStore` shows how to layer cache + canonical stores.
3. **Custom workers** – Extend `scripts/run_consumers.py` or add new consumers that subscribe to `memory.events`.
4. **Different API surface** – `somafractalmemory.core.SomaFractalMemoryEnterprise` encapsulates all business logic; wrap it with your own framework if FastAPI does not fit.

---

## 📚 Additional Resources
* Architecture deep dive – `docs/ARCHITECTURE.md`
* Canonical operations guide – `docs/CANONICAL_DOCUMENTATION.md`
* Configuration reference – `docs/CONFIGURATION.md`
* API usage guide – `docs/USAGE_GUIDE.md`
* Quickstart tutorial – `docs/QUICKSTART.md`
* API reference – `docs/api.md`
* Cognitive / adaptive design spec – `docs/COGNITIVE_MEMORY_DESIGN.md`

---

## 🏁 Quick Start (Python)
```python
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType

memory = create_memory_system(
    MemoryMode.DEVELOPMENT,
    "demo",
    config={
        "redis": {"testing": True},
        "qdrant": {"path": "./qdrant.db"},
    },
)

memory.store_memory((1.0, 2.0, 3.0), {"task": "document SFM", "importance": 5}, MemoryType.EPISODIC)
print(memory.recall("document"))
```

---

---
### Migration Note: Redpanda → Confluent Kafka
Earlier revisions used Redpanda for the local single-broker runtime. Due to intermittent async I/O resource exhaustion and crash loops on some development machines, the default Docker Compose broker migrated to a Confluent Kafka single-node KRaft image (`confluentinc/cp-kafka`).

Helm values and service identifiers may still reference `redpanda`; this is a naming artifact only. Reverting to Redpanda requires swapping the image and (optionally) tuning flags—no application code changes are needed because the clients speak the Kafka protocol.

*© 2025 SomaTechLat – All rights reserved.*
