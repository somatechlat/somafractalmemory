# Soma Fractal Memory (SFM)

---

## 📖 Overview
**Soma Fractal Memory (SFM)** is a modular, agent‑centric memory system written in Python. It provides a unified interface for storing, recalling, and linking **episodic** and **semantic** memories using a combination of in‑memory caches, relational databases, and vector similarity stores.  The library is designed for AI agents, knowledge‑graph pipelines, and any workload that needs fast, context‑aware retrieval of past events.

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
|   Redpanda (Kafka)|   |   Workers (Consumer)    |
+-------------------+   +-------------------+   +-------------------+
```

* **FastAPI** – HTTP server exposing the memory API (`/store`, `/recall`, `/graph`, …) and Prometheus metrics.
* **CLI (`soma` command)** – Thin wrapper around the same API for local scripts and notebooks.
* **Redis** – Low‑latency cache for recent episodic entries.
* **PostgreSQL** – Durable KV store for canonical memory objects.
* **Qdrant** – Approximate‑nearest‑neighbor vector store for semantic embeddings.
* **Redpanda** – Kafka‑compatible broker that streams `memory.events` to background workers.
* **Worker** – Consumes events, updates Redis / PostgreSQL / Qdrant, and emits optional side‑effects.

---

## ⚙️ Settings & Configuration
All services read a shared ```.env``` file (loaded via Docker‑Compose `env_file:`).  The most important variables are:

| Variable | Description | Example |
|----------|-------------|---------|
| `MEMORY_MODE` | Determines which back‑ends are active. Options: `development`, `test`, `evented_enterprise`, `cloud_managed` | `development` |
| `REDIS_HOST` / `REDIS_PORT` | Connection to the Redis cache. | `redis:6379` |
| `POSTGRES_URL` | Full DSN for PostgreSQL. | `postgresql://postgres:postgres@postgres:5433/somamemory` |
| `QDRANT_HOST` / `QDRANT_PORT` | Host/port for the Qdrant vector store. | `qdrant:6333` |
| `KAFKA_BOOTSTRAP_SERVERS` | Redpanda broker address. | `redpanda:9092` |
| `EVENTING_ENABLED` | Toggle event publishing (useful for pure unit‑test mode). | `true` |

Create the file from the example:
```bash
cp .env.example .env   # edit values as required
```

---

## 📦 Installation
### 1️⃣ Python (editable mode)
```bash
# Create a virtual environment (optional but recommended)
python -m venv .venv && source .venv/bin/activate

# Install the package in editable mode so the CLI is available
pip install -e .
```

### 2️⃣ Docker‑Compose (full stack)
```bash
# Build all images (required after code changes)
docker compose build

# Start the complete stack in the background
docker compose up -d
```
The API will be reachable at **http://localhost:9595**.

---

## 🚀 Running & Dynamic Configuration
* **Full stack (dev parity)** – Start Redis, Postgres, Qdrant, and Redpanda with the provided helper:
```bash
./scripts/start_stack.sh evented_enterprise
```
  Then launch the API and consumer containers:
```bash
docker compose up -d api consumer
```
* **Sandbox API (optional)** – `docker compose up -d test_api` exposes a second instance on `http://localhost:8888` for load or forensic testing.
* **Env changes** – Edit `.env` (e.g. switch `MEMORY_MODE`) and re-run the commands above. The API reads values on startup.
* **Stopping** – Preserve data with named volumes:
```bash
docker compose down   # keep volumes
```
* **Full wipe** (remove all persisted data):
```bash
docker compose down -v
```

> ℹ️ **Tracing in development:** The FastAPI example enables the OTLP exporter by default. In pure dev setups without a collector, set `OTEL_TRACES_EXPORTER=none` in `.env` (or point it at your collector) to avoid noisy connection errors.

---

## 📡 API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/store` | Store a memory (coordinates + payload). Returns an ID.
| `POST` | `/remember` | Convenience wrapper that lets the server choose coordinates (optional input coord).
| `GET`  | `/recall` | Retrieve the most relevant memory for a text query or vector.
| `POST` | `/recall_batch` | Recall multiple memories in a single request.
| `POST` | `/store_bulk` | Store many memories at once (efficient for ingestion).
| `GET`  | `/graph/neighbors` | Return direct graph neighbours for a given node.
| `GET`  | `/graph/shortest_path` | Compute shortest‑path between two memory nodes.
| `GET`  | `/stats` | Basic statistics (counts per backend, memory usage, etc.).
| `GET`  | `/metrics` | Prometheus metrics (exposed automatically).
| `GET`  | `/health` | Liveness / readiness probe for Kubernetes.

The full OpenAPI spec is generated at **`/openapi.json`** and can be explored via Swagger UI at **`/docs`**.

---

## 🧮 Core Mathematics
SFM relies on two main similarity concepts:

### 1️⃣ Cosine Similarity (semantic vectors)
```python
cosine = (a · b) / (||a|| * ||b||)
```
* `a` and `b` are embedding vectors.
* Returns a value in **[-1, 1]**; higher = more similar.
* Used by Qdrant for nearest‑neighbor search.

### 2️⃣ Euclidean Distance (episodic coordinates)
```python
distance = sqrt( Σ_i (x_i - y_i)^2 )
```
* Coordinates are stored as tuples (e.g., `(x, y, z)`).
* Smaller distance ⇒ more recent / temporally close event.
* Combined with a weighting factor (`α`) to produce a final relevance score:
```python
score = α * (1 - cosine) + (1 - α) * (distance / max_distance)
```
* `α` is configurable via `MemoryMode` – higher for semantic‑heavy use‑cases.

---

## 🧪 Testing & CI
* **Unit tests** – Run with `pytest -q`.  Tests use in‑memory back‑ends and do not require Docker.
* **CI pipeline** – Executes the full test suite, runs `black`, `ruff`, and `pre‑commit` checks.
* **Coverage** – Over 90 % line coverage on core modules.

---

## 🛠️ Development Workflow
1. **Create a feature branch**
   ```bash
   git checkout -b feature/awesome-thing
   ```
2. **Make changes** – The repository ships with a pre‑commit config that automatically formats code.
3. **Run tests & lint**
   ```bash
   pytest -q && pre-commit run --all-files
   ```
4. **Commit & push** – The CI will run on push; merge via pull request.

---

## 🤝 Contributing
* Follow the existing code style (`black` + `ruff`).
* Add unit tests for new functionality.
* Update the documentation (this README) if you change public behavior.
* Open a Pull Request against the `main`/`v2.0` branch.

---

## 📈 Monitoring & Observability
* **Prometheus metrics** – Exported at `/metrics`.  Includes counters for store/recall calls, latency histograms, and a custom 404 counter.
* **OpenTelemetry** – Traces are automatically created for PostgreSQL and Qdrant calls. Provide an OTLP endpoint via `OTEL_EXPORTER_OTLP_ENDPOINT`, or set `OTEL_TRACES_EXPORTER=none` when you do not have a collector running.

---

## 🔧 Extending the System
1. **Add a new vector store** – Implement the `VectorStore` interface in `somafractalmemory/implementations/`.  Register it in `factory.create_memory_system`.
2. **Custom event handling** – Extend `scripts/run_consumers.py` to react to new event types.
3. **Alternative API frameworks** – The core logic lives in `somafractalmemory.core`; you can wrap it with Flask, FastAPI, or any ASGI server.

---

## 📚 Additional Resources
* **Architecture diagram** – See `docs/ARCHITECTURE.md` for a visual overview.
* **API reference** – `docs/api.md` contains autogenerated OpenAPI docs.
* **Configuration reference** – `docs/configuration.md` lists every environment variable.
* **Community** – Open an issue on GitHub or join the `#soma-fractal-memory` channel on the project Discord.

---

## 🏁 Quick Start Example
```python
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType

# Minimal configuration (development mode)
mem = create_memory_system(MemoryMode.DEVELOPMENT, "demo", config={
    "redis": {"testing": True},
    "qdrant": {"path": "./qdrant.db"},
})

# Store and recall a simple episodic memory
mem.store_memory((1.0, 2.0, 3.0), {"task": "write README", "importance": 5}, MemoryType.EPISODIC)
print(mem.recall("write README"))
```

---

*© 2025 somatechlat – All rights reserved.*
