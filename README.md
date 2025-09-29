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
|   Redpanda (Kafka)|   |  Worker Consumers |   |  Event Schema    |
+-------------------+   +-------------------+   +-------------------+
```

* **FastAPI (`examples/api.py`)** – HTTP server exposing memory, graph, and admin endpoints plus Prometheus metrics.
* **CLI (`soma` command)** – Thin wrapper around the same factory for scripting and batch jobs.
* **Redis** – Optional low-latency cache and distributed lock store for recent episodic memories.
* **PostgreSQL** – Canonical key-value store for durable JSON payloads.
* **Qdrant** – Approximate nearest-neighbour vector store for semantic embeddings.
* **Redpanda/Kafka** – Event bus carrying `memory.events` for asynchronous processing.
* **Workers (`scripts/run_consumers.py`)** – Consume events, update Postgres/Qdrant, and expose their own Prometheus metrics.

---

## ⚙️ Settings & Configuration
All runtime services share a `.env` file (Docker Compose loads it via `env_file:`). The key variables are:

| Variable | Description | Example |
|----------|-------------|---------|
| `MEMORY_MODE` | Selects backend wiring. Options: `development`, `test`, `evented_enterprise`, `cloud_managed`. | `development` |
| `REDIS_HOST` / `REDIS_PORT` | Redis connection used by the API and workers. | `redis:6379` |
| `POSTGRES_URL` | Full DSN for PostgreSQL. | `postgresql://postgres:postgres@postgres:5433/somamemory` |
| `QDRANT_HOST` / `QDRANT_PORT` | Qdrant host/port. | `qdrant:6333` |
| `KAFKA_BOOTSTRAP_SERVERS` | Redpanda broker URL. | `redpanda:9092` |
| `EVENTING_ENABLED` | Toggle Kafka publishing; automatically disabled in `MemoryMode.TEST`. | `true` |
| `SOMA_RATE_LIMIT_MAX` | Per-endpoint request limit for the API example. | `5000` |
| `UVICORN_WORKERS` / `UVICORN_TIMEOUT_GRACEFUL` | Control FastAPI worker count and graceful shutdown window. | `4` / `60` |

Create an environment file by copying the template shipped with the repo:
```bash
cp .env.example .env
# then edit values as needed
```

Advanced tuning is documented in `docs/CONFIGURATION.md`.

---

## 📦 Installation
### 1️⃣ Python (editable mode)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```
This installs the `somafractalmemory` package and makes the `soma` CLI available on your PATH.

### 2️⃣ Docker Compose (full stack)
```bash
# Build images after local changes
docker compose build

# Start Redis, Postgres, Qdrant, Redpanda, API, and workers
docker compose up -d
```
The API listens on **http://localhost:9595**. A sandbox copy runs on **http://localhost:8888** when the `test_api` service is started.

---

## 🚀 Running & Dynamic Configuration
* **Minimal local services** – Start just Postgres and Qdrant for development:
  ```bash
  ./scripts/start_stack.sh development
  docker compose up -d api
  ```
* **Add Kafka/Redpanda** – Include the broker (and Apicurio registry) by passing `--with-broker` to `start_stack.sh`, or simply run the full compose stack.
* **Full parity stack** – Mirror production wiring with Redpanda and workers:
  ```bash
  ./scripts/start_stack.sh evented_enterprise
  docker compose up -d api consumer
  ```
* **Environment changes** – Edit `.env`, then restart the affected services (`docker compose up -d api consumer`). Containers read configuration on startup.
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
A Helm chart for the full stack (API, consumer, Postgres, Redis, Qdrant, Redpanda) lives in `helm/`:
```bash
helm install sfm ./helm \
  --set image.repository="somatechlat/somafractalmemory" \
  --set image.tag="2.0"

# Tear down when finished
helm uninstall sfm
```
Key chart values map to the same environment variables and feature flags documented above. See `docs/CANONICAL_DOCUMENTATION.md` for an end-to-end walkthrough.

For production deployments and an explicit checklist (build, image push, Helm values, schema compatibility and verification steps) see `docs/PRODUCTION_READINESS.md`.

---

## 📡 API Highlights
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/store` | Persist a memory (coordinate + payload). |
| `POST` | `/remember` | Let the server choose a coordinate when storing. |
| `POST` | `/recall` | Recall top matches for a text query (hybrid semantic search). |
| `POST` | `/recall_batch` | Run multiple recall queries in one call. |
| `POST` | `/store_bulk` | Bulk-ingest memories from a payload list. |
| `POST` | `/recall_with_scores` | Return matches with similarity scores. |
| `POST` | `/recall_with_context` | Context-aware hybrid recall (filters/extra signals). |
| `GET`  | `/range` | Find memories whose coordinates fall within a bounding box. |
| `POST` | `/link` | Create a semantic edge between two coordinates. |
| `GET`  | `/neighbors` | Inspect graph neighbours for a coordinate. |
| `GET`  | `/shortest_path` | Compute the graph shortest path between two coordinates. |
| `GET`  | `/stats` | Return memory counts and backend health. |
| `GET`  | `/metrics` | Prometheus metrics exported by the API. |
| `GET`  | `/health` | Lightweight readiness probe. |
| `GET`  | `/healthz` / `/readyz` | Liveness/readiness checks for Kubernetes. |

Swagger UI is available at **`/docs`**, and the generated spec is published as `openapi.json` in the repo root each time the API boots.

---

## 🧪 Testing & CI
* **Unit tests** – `pytest -q` uses in-memory backends, so no external services are required.
* **Integration** – Dedicated tests (e.g., `tests/test_postgres_redis_hybrid_store.py`) exercise the hybrid store against containerised Postgres/Redis.
* **CI** – GitHub Actions run pytest, Ruff, Black, Bandit, mypy, and build the MkDocs documentation.
* **Pre-commit** – A `.pre-commit-config.yaml` is provided; run `pre-commit install` to mirror the GitHub checks locally.

---

## � Benchmarks (Fast Core vs Legacy Path)
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

## �📈 Observability & Eventing
* **Prometheus metrics** – The API exposes `/metrics`. Consumers expose their own metrics server (default `localhost:8001/metrics`).
* **OpenTelemetry** – Optional instrumentation for psycopg2 and Qdrant initialises at import time. If the OpenTelemetry packages are absent, SFM falls back to no-op stubs.
* **Langfuse** – Integration keys are read from Dynaconf or `config.yaml`; logging is a no-op when Langfuse is unavailable.
* **Kafka events** – `eventing/producer.py` validates each event against `schemas/memory.event.json` before publishing to `memory.events`.

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
* API reference – `docs/api.md`
* Quickstart tutorial – `docs/QUICKSTART.md`

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

*© 2025 SomaTechLat – All rights reserved.*
