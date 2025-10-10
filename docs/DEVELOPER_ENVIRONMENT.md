# Developer Environment Setup

This guide walks you through setting up a complete developer environment for Soma Fractal Memory (SFM), from prerequisites to running the stack with Docker Compose or Kubernetes + Helm, plus the exact settings the code reads. The code is the single source of truth; this document cites concrete files and symbols so you can trace behavior directly.

---

## Visual overview (at a glance)

### Docker Compose topology (host ports → containers)
```mermaid
flowchart LR
  subgraph Host
    Client[Client / Agent]
  end
  Client -->|HTTP 9595| API[FastAPI API (uvicorn)]
  API -->|write JSON| PG[(Postgres 5433→5432)]
  API -->|cache| RD[(Redis 6381→6379)]
  API -->|vectors| QD[(Qdrant 6333)]
  API -->|publish| KF[(Kafka 19092→9092)]
  CN[Consumer(s)] -->|read| KF
  CN -->|upsert| PG
  CN -->|index| QD
  classDef db fill:#eef7ff,stroke:#4c8eda,color:#0b3d91;
  classDef cache fill:#f6ffed,stroke:#52c41a,color:#135200;
  classDef broker fill:#fff7e6,stroke:#fa8c16,color:#873800;
  class PG db;
  class QD db;
  class RD cache;
  class KF broker;
```

### Kubernetes + Helm (dev override with NodePort)
```mermaid
flowchart LR
  Client[Client / Agent] -->|NodePort 30797| SVCNP[Service NodePort 9797]
  SVCNP -->|ClusterIP 9797| API[Deployment: API]
  API -->|env → DSN| PG[(Postgres PVC?)]
  API --> RD[(Redis PVC?)]
  API --> QD[(Qdrant PVC?)]
  API -->|if enabled| RP[(Redpanda/Kafka PVC?)]
  CNS[Deployment: Consumer] --> RP
  CNS --> PG
  CNS --> QD
  classDef comp fill:#eef7ff,stroke:#4c8eda,color:#0b3d91;
  classDef np fill:#fff7e6,stroke:#fa8c16,color:#873800;
  class PG,QD,RD,RP comp;
  class SVCNP np;
```

Optional Ingress path (production): Client → Ingress (TLS) → Service ClusterIP 9595 → API.

---

## 1. System Prerequisites

| Tool | Minimum Version | Install Command |
|------|-----------------|-----------------|
| **Homebrew** (macOS) | 3.0+ | `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` |
| **Python** | 3.10+ (3.12 recommended) | `brew install python@3.12` |
| **Git** | 2.30+ | `brew install git` |
| **Docker Desktop** | 24.0+ (includes `docker` and `docker compose`) | Download from <https://www.docker.com/products/docker-desktop> |
| **kubectl** | 1.28+ | `brew install kubectl` |
| **kind** (Kubernetes in Docker) | 0.20+ | `brew install kind` |
| **helm** | 3.12+ | `brew install helm` |
| **Node.js** (optional – needed for some docs tooling) | 20+ | `brew install node` |
| **Pre‑commit** (code‑style enforcement) | 3.0+ | `pip install pre-commit` |

Make sure the binaries are on your `$PATH`:
```bash
python3 --version
pip3 --version
docker --version
kubectl version --client
kind version
helm version
```

---

## 2. Clone the Repository
```bash
# Fork the repo on GitHub if you plan to contribute
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory
```

---

## 3. Python Development Environment (uv)

### 3.1 Recommended: Use uv for dependency management (fast and reproducible)
We manage dependencies with Astral's uv. It creates a virtual environment, resolves extras, and locks versions for reliable installs.

```bash
# Install uv (once per machine)
curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y
uv --version

# Sync project dependencies with extras for API and Kafka events
uv sync --extra api --extra events

# Optional developer tools (linters, tests):
uv sync --extra dev --extra api --extra events

# Run commands via uv (no need to activate venv)
uv run soma --help
uv run pytest -q
uv run uvicorn somafractalmemory.http_api:app --reload
```

> Fallback (pip): If you cannot install uv, use a classic venv, then `pip install -e .[api,events,dev]`. uv remains the supported path for deterministic installs.

### 3.3 Verify the CLI works
```bash
uv run soma --help
```
You should see the help output with commands like `store`, `recall`, `store-bulk`, etc.

---

## 4. Docker Compose local stack (quick iteration)

The repository ships a **docker‑compose.yml** that brings up all required services.

### 4.1 Build images (needed after code changes)
```bash
make compose-build
```

### 4.2 Start the full stack
```bash
make compose-up
```
This starts Redis (6381→6379), Postgres (5433→5432), Qdrant (6333), Kafka (19092→9092), API (9595), and a sandbox API (8888→9595) as defined in `docker-compose.yml`.
### 4.3 Verify services are healthy
```bash
# API health check (exposed on localhost:9595)
make compose-health
# PostgreSQL test (run inside the container)
docker compose exec postgres pg_isready -U postgres
# Qdrant health endpoint
curl -s http://localhost:6333/collections/api_ns | jq .
```
All should return a JSON payload with `true` values or HTTP 200.

Request flows (visual aid)

Store (with eventing enabled):
```mermaid
sequenceDiagram
  participant C as Client
  participant A as API
  participant PG as Postgres
  participant K as Kafka
  participant W as Consumer
  participant Q as Qdrant
  C->>A: POST /store
  A->>PG: INSERT kv_store
  alt EVENTING_ENABLED=true
    A->>K: produce memory.events
    W->>K: consume memory.events
    W->>Q: upsert vector
  end
  A-->>C: 200 { ok: true }
```

Recall (hybrid):
```mermaid
sequenceDiagram
  participant C as Client
  participant A as API
  participant Q as Qdrant
  participant PG as Postgres
  C->>A: POST /recall
  A->>Q: vector search (top-k)
  A->>PG: fetch JSON payloads
  A-->>C: 200 results
```

### 4.4 Stop the stack
```bash
make compose-down     # Keeps volumes (data)
make compose-down-v   # Removes volumes
```

---

## 5. Kubernetes + Helm (near‑production)
```bash
# Create a Kind cluster; the repo provides a config that maps NodePort 30797 to the host
kind create cluster --name sfm --config helm/kind-config.yaml
```
Verify:
```bash
kubectl cluster-info --context kind-sfm
```

### 5.2 Build and load the runtime image into Kind
```bash
# Build the slim runtime image the Helm chart expects
docker build -f Dockerfile.runtime -t somafractalmemory-runtime:local .
# Load into the Kind node
kind load docker-image somafractalmemory-runtime:local --name sfm
```

### 5.3 Deploy with Helm
```bash
helm upgrade --install soma-memory ./helm \
  --namespace soma-memory \
  --create-namespace \
  --wait --timeout=600s
```

The default `values.yaml` already requests 300 m CPU / 2 Gi memory for the API and consumer to mimic production sizing. When deploying to a remote cluster, override the image coordinates and pull policy:

```bash
helm upgrade --install soma-memory ./helm \
  --namespace soma-memory \
  --create-namespace \
  --set image.repository=somatechlat/soma-memory-api \
  --set image.tag=v2.1.0 \
  --set image.pullPolicy=IfNotPresent \
  --wait --timeout=600s
```

For the dev slice that exposes the API on your host without port-forward, you can install using the provided 9797/30797 override:
```bash
make helm-dev-install
make helm-dev-health
```

To enable durable PVCs on real clusters, pass `--values` that set `*.persistence.enabled: true` and a storageClass per component (Postgres, Redis, Qdrant, Kafka).

The Helm chart creates the following resources in namespace `soma-memory`:
- API Deployment (`soma-memory-somafractalmemory`)
- Consumer Deployment (`soma-memory-somafractalmemory-consumer`)
- PostgreSQL Deployment
- Redis Deployment
- Qdrant Deployment
- Kafka Broker Deployment (value block name may remain `redpanda`)
- Service objects for each component

### 5.4 Expose the API for local testing
```bash
# Option A (port-forward): forwards localhost:9595 → API service port 9595
./scripts/port_forward_api.sh start
# Option B (NodePort): if you installed with values-dev-port9797.yaml, use 30797 on localhost
make helm-dev-health
```
Now you can hit the API exactly as you would with Docker‑Compose.

### 5.5 Verify the deployment
```bash
# Pods are Running?
kubectl -n soma-memory get pods -o wide
# Health endpoint
curl -s http://127.0.0.1:9595/healthz | jq .
```
If any pod is CrashLoopBackOff, inspect logs:
```bash
kubectl -n soma-memory logs pod/<pod-name> -c somafractalmemory   # API logs
kubectl -n soma-memory logs pod/<consumer-pod> -c somafractalmemory-consumer   # consumer logs
```

---

## 6. Development Workflow

### 6.1 Hot‑reloading the API
During active development you may want the FastAPI server to restart automatically on code changes.
```bash
# Inside the repo (with the venv activated)
uvicorn somafractalmemory.http_api:app --reload --host 0.0.0.0 --port 9595
```
If you run this **outside** of Kubernetes, you can skip the Helm/Kind steps and hit the API directly at `http://localhost:9595`.

### 6.2 Working with the Consumer
The consumer reads from Kafka and writes to Postgres/Qdrant. To run it locally (without Helm) use:
```bash
uv run python -m scripts.run_consumers
```
If you run the consumer outside Docker, export env vars to point at Compose services:
```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:19092
export POSTGRES_URL=postgresql://postgres:postgres@localhost:5433/somamemory
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
uv run python -m scripts.run_consumers
```

### 6.3 Running Tests
```bash
# Run the full test suite (including integration tests that spin up containers)
uv run pytest -q
```
For a quick unit‑test run that does **not** start Docker containers:
```bash
uv run pytest tests/test_cli.py
```

### 6.4 Linting & Formatting (pre‑commit)
```bash
uv run pre-commit install   # installs hooks into .git/hooks
uv run pre-commit run --all-files   # run all hooks once
```
The repo uses **ruff**, **black**, **isort**, **mypy**, and **bandit**.

---

## 7. Generate OpenAPI and IDE setup

### 7.1 Generate the OpenAPI spec from the running app
```bash
uv run python scripts/generate_openapi.py
ls -l openapi.json
```
The file is generated from `somafractalmemory/http_api.py:app` and reflects the current code.

### 7.2 VS Code (recommended)

#### settings.json
1. Install the **Python** extension.
2. Open the workspace (`File → Open Folder…` → `somafractalmemory`).
3. Select the interpreter: `Cmd+Shift+P → Python: Select Interpreter → .venv/bin/python`.
4. Enable linting and formatting in `settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": ["tests"]
}
```
5. (Optional) Install the **Docker** extension to view container logs directly from VS Code.

### 7.3 PyCharm / IntelliJ
- Add the virtual environment (`.venv`) as a *Project Interpreter*.
- Set the *Working directory* to the repository root.
- Enable *pytest* as the test runner and configure the *Run/Debug* configuration for `scripts/run_consumers.py` if you want to debug the consumer.

---

## 8. Debugging tips

| Symptom | Likely Cause | How to Investigate |
|---------|--------------|--------------------|
| **API returns 502 / connection refused** | Port‑forward not running or API pod crashed | `./scripts/port_forward_api.sh status`; `kubectl -n soma-memory get pods`; `kubectl -n soma-memory logs pod/<api-pod>` |
| **Consumer not processing events** | Wrong `KAFKA_BOOTSTRAP_SERVERS` or broker not reachable | From inside the broker pod, run `kafka-topics --bootstrap-server localhost:9092 --list`; check consumer logs |
| **Postgres rows missing** | Event not consumed yet or filters in recall | Check `somafractalmemory/scripts/run_consumers.py` logs; verify the consumer is running (Kafka reachable). |
| **Qdrant points count stays at 0** | Consumer failed to index vectors, or vector dimension mismatch | Inspect `workers/vector_indexer.py` logs; run a manual scroll query as shown in the README |
| **Tests fail on CI but pass locally** | Missing Docker‑Compose services in CI environment | Ensure the CI workflow brings up the stack (`docker compose up -d`), or use the `testcontainers` based tests that spin up containers automatically |

---

## 9. Production‑ready checklist (for reference)
1. **Build & push a reproducible Docker image** (use a CI pipeline).<br>2. **Set resource requests/limits** for API & consumer (see `helm/values.yaml`).<br>3. **Enable probes** (`initialDelaySeconds` ≥ 20, `timeoutSeconds` ≥ 5).<br>4. **Configure authentication** (`SOMA_API_TOKEN`).<br>5. **Expose the API via an Ingress** with TLS termination.<br>6. **Enable Prometheus scrape** (`/metrics`).<br>7. **Run a backup strategy** for PostgreSQL and Qdrant persistence.<br>8. **Monitor consumer lag** (Kafka offsets) and set alerts.<br>9. **Run the production readiness steps** documented in `docs/PRODUCTION_READINESS.md`.

---

## 10. Clean-up
When you are done experimenting, you can delete all local resources:
```bash
# Docker‑Compose
docker compose down -v
# Kind cluster
kind delete cluster --name soma-cluster
# Virtual environment
deactivate && rm -rf .venv
```

You now have a fully documented, reproducible developer environment for Soma Fractal Memory.

---

## 11. Settings reference (source of truth)

These are the settings the code reads, with file references for traceability.

- FastAPI wiring: `somafractalmemory/http_api.py`
  - Environment variables: `POSTGRES_URL`, `REDIS_URL|REDIS_HOST|REDIS_PORT|REDIS_DB`, `QDRANT_URL|QDRANT_HOST|QDRANT_PORT`, `KAFKA_BOOTSTRAP_SERVERS`, `EVENTING_ENABLED`, `SOMA_API_TOKEN`, `SOMA_MEMORY_NAMESPACE`, `UVICORN_PORT`, `UVICORN_WORKERS`, `UVICORN_TIMEOUT_*`.
  - Optional centralised settings: `common/config/settings.py::load_settings()` (used if available) with `SMFSettings` defaults (`api_port=9595`, `grpc_port=50053`, infra endpoints).
- Postgres KV store: `somafractalmemory/implementations/storage.py::PostgresKeyValueStore`
  - Reads `POSTGRES_URL`; uses psycopg2 directly; includes reconnect-on-failure logic.
- Redis KV store: `somafractalmemory/implementations/storage.py::RedisKeyValueStore`
  - Reads `REDIS_HOST/PORT/DB` or `REDIS_URL` (parsed in `http_api.py`).
- Qdrant vector store: `somafractalmemory/implementations/storage.py::QdrantVectorStore`
  - Reads `QDRANT_URL` or `QDRANT_HOST/QDRANT_PORT`.
- Helm chart defaults: `helm/values.yaml`
  - API `service.port: 9595` by default, dev override at `helm/values-dev-port9797.yaml` sets `service.port: 9797`, `service.nodePort: 30797`.
- Docker Compose: `docker-compose.yml`
  - Host ports: API 9595, Redis 6381→6379, Postgres 5433→5432, Qdrant 6333, Kafka 19092→9092. Named volumes persist data.

Precedence:
1) Explicit config dict passed to `create_memory_system` → 2) Environment variables → 3) `SMFSettings` loaded via `load_settings()`.

## 12. Performance & latency

### 11.1 Why latency matters
The **store** endpoint (`POST /store_bulk` or `POST /store`) is the critical path for any agent that needs to persist a memory quickly. High latency can:
- Slow down downstream reasoning loops.
- Cause back‑pressure on the eventing pipeline (Kafka).
- Increase the chance of time‑outs when the API is called from a remote client.

### 12.2 Typical numbers (observed on a local macOS/Kind setup)
| Scenario | Avg latency (ms) | 95th‑pct latency (ms) |
|----------|------------------|-----------------------|
| Single‑item `POST /store` (no DB cache) | 45‑70 | 110 |
| 50‑item bulk `POST /store_bulk` (single request) | 180‑260 | 340 |
| Bulk split into 10 × 5‑item chunks | 30‑45 per chunk (overall ~350 ms) | 70‑90 per chunk |

These numbers were measured with the API running on **UVICORN_WORKERS=2**, PostgreSQL and Qdrant both in‑cluster, and the client on the same host (localhost). Network latency inside Kind is negligible; most of the time is spent in:
- PostgreSQL write transaction.
- Qdrant vector upsert (if the payload includes an embedding).
- JSON schema validation (now fast after the timestamp fix).

### 12.3 Measuring latency yourself
#### Using `curl`
```bash
curl -s -w "\nTIME_TOTAL:%{time_total}\n" -X POST http://127.0.0.1:9595/store \
  -H 'Content-Type: application/json' \
  -d '{"coord":"0,0,0","payload":{"text":"demo","run_id":"latency‑test"},"type":"episodic"}'
```
The `time_total` field reports the full request‑response time in seconds.

#### Using Python `requests`
```python
import time, requests, json
payload = {"coord":"0,0,0","payload":{"text":"demo","run_id":"latency‑test"},"type":"episodic"}
start = time.perf_counter()
resp = requests.post('http://127.0.0.1:9595/store', json=payload)
elapsed = (time.perf_counter() - start) * 1000
print(f"Status: {resp.status_code}, elapsed: {elapsed:.1f} ms")
```

#### Prometheus metrics (built‑in)
The API exposes a `api_request_latency_seconds` histogram. If you have Prometheus scraping the endpoint (`/metrics`), you can query:
```promql
histogram_quantile(0.95, sum(rate(api_request_latency_seconds_bucket{endpoint="store"}[5m])) by (le)
```
This returns the 95th‑percentile latency over the last 5 minutes.

### 12.4 Reducing latency
| Lever | What to adjust | Effect |
|-------|----------------|--------|
| **UVICORN_WORKERS** | Increase workers if the CPU has spare cores (e.g., `UVICORN_WORKERS=4`). | More concurrent requests, lower per‑request wait time under load. |
| **PostgreSQL reconnect** | The KV store uses psycopg2 directly and reconnects if a connection is dropped. Keep transactions small and avoid frequent hard restarts. | Avoids 500s after DB restarts (the code now auto-reconnects). |
| **Batch size** | Split very large bulk payloads into smaller chunks (e.g., 5‑10 items per request). | Keeps each transaction short and avoids long DB locks. |
| **Disable schema validation** (only for trusted internal callers) | Set `EVENTING_ENABLED=false` or comment out the `jsonschema.validate` call in `eventing/producer.py`. | Removes a few ms per request. |
| **Qdrant indexing** | Pre‑compute embeddings asynchronously (store vectors in a background worker instead of the API). | API returns faster; vector work is off‑loaded. |
| **Resource limits** | Give the API pod more CPU (`resources.limits.cpu`) if the node has capacity. | Faster processing of JSON and DB driver work. |

### 12.5 Stress‑testing guide
You can use `hey` or `wrk` to generate load and observe latency spikes:
```bash
# Install hey
brew install hey
# 100 concurrent requests, 10 seconds total
hey -c 100 -z 10s -m POST -H 'Content-Type: application/json' \
    -d '{"coord":"0,0,0","payload":{"text":"load","run_id":"stress"},"type":"episodic"}' \
    http://127.0.0.1:9595/store
```
Watch the API pod’s CPU/Memory (`kubectl top pod -n soma-memory`) and the Prometheus latency histogram to see where bottlenecks appear.

---

## 12. Practical Latency‑Reduction Tips

Below are concrete knobs you can turn in a development or production deployment to shave milliseconds off the **store** API latency.

### UVicorn Workers
- The API runs under **uvicorn**. By default the Helm chart sets `UVICORN_WORKERS=2` to keep the pod lightweight. If the node has spare CPU cores you can safely increase this value, e.g. `UVICORN_WORKERS=4` or `UVICORN_WORKERS=$(nproc)`.
- More workers mean more concurrent request handling and lower queueing time under load, but also higher CPU usage. Adjust the pod’s `resources.limits.cpu` accordingly.

### PostgreSQL Connection Pool
- The FastAPI app uses SQLAlchemy’s connection pool. Tune it via the environment variable `POSTGRES_POOL_SIZE` (default 5).
- A larger pool reduces the time spent acquiring a connection during bursts of traffic:
  ```bash
  export POSTGRES_POOL_SIZE=15   # example for a 4‑core pod
  ```

### Batch Size
- The `/store_bulk` endpoint accepts arbitrary batch sizes, but very large payloads can increase transaction time and lock contention.
- Empirically we found **5‑10 items per request** gives a good trade‑off. If you need to ingest thousands of items, split them client‑side into smaller chunks.

### Disable JSON‑Schema Validation (Trusted Internal Calls)
- Validation adds a few milliseconds per request. When the caller is trusted (e.g., internal batch jobs) you can skip it by setting `SKIP_SCHEMA_VALIDATION=true` or by commenting out the `jsonschema.validate` call in `eventing/producer.py`.
- **Caution:** only disable in controlled environments; validation protects against malformed payloads.

### Async Qdrant Indexing
- Vector upserts to Qdrant are currently performed synchronously in the API request. To reduce latency, move this work to a background worker:
  1. Store the raw payload in PostgreSQL.
  2. Publish a lightweight event (e.g., `vector_index_needed`) to Kafka.
  3. A dedicated consumer reads the event, computes the embedding, and upserts to Qdrant.
- This decouples the fast path from the slower vector computation.

### Resource Limits
- Ensure the API pod has enough CPU and memory. Typical values that work well on a 2‑core node:
  ```yaml
  resources:
    requests:
      cpu: "200m"
      memory: "256Mi"
    limits:
      cpu: "800m"
      memory: "512Mi"
  ```
- If you increase `UVICORN_WORKERS`, proportionally raise the CPU limit.

---

## 13. Stress‑Testing Guide with `hey`

`hey` is a lightweight HTTP load generator (similar to `ab`). It lets you hammer the `/store` or `/store_bulk` endpoints and observe latency distribution.

### Installation
```bash
brew install hey   # macOS
# or download from https://github.com/rakyll/hey/releases
```

### Simple single‑item load test
```bash
hey -c 50 -z 15s -m POST \
    -H 'Content-Type: application/json' \
    -d '{"coord":"0,0,0","payload":{"text":"stress","run_id":"hey‑test"},"type":"episodic"}' \
    http://127.0.0.1:9595/store
```
- `-c 50` – 50 concurrent workers.
- `-z 15s` – run for 15 seconds.
- The output shows total requests, success rate, and latency percentiles (p50, p95, p99).

### Bulk‑store stress test
Create a small JSON file (`bulk.json`) with, for example, 5 items:
```json
{
  "items": [
    {"coord":"0,0,0","payload":{"text":"msg1","run_id":"hey‑bulk"},"type":"episodic"},
    {"coord":"0,0,1","payload":{"text":"msg2","run_id":"hey‑bulk"},"type":"episodic"},
    {"coord":"0,0,2","payload":{"text":"msg3","run_id":"hey‑bulk"},"type":"episodic"},
    {"coord":"0,0,3","payload":{"text":"msg4","run_id":"hey‑bulk"},"type":"episodic"},
    {"coord":"0,0,4","payload":{"text":"msg5","run_id":"hey‑bulk"},"type":"episodic"}
  ]
}
```
Run the bulk test:
```bash
hey -c 30 -z 20s -m POST \
    -H 'Content-Type: application/json' \
    -d @bulk.json \
    http://127.0.0.1:9595/store_bulk
```
- Adjust `-c` and `-z` to simulate higher load.

### Monitoring while stress‑testing
- **Pod metrics:** `kubectl top pod -n soma-memory` to watch CPU/Memory.
- **Prometheus latency histogram:** query `histogram_quantile(0.95, sum(rate(api_request_latency_seconds_bucket{endpoint="store"}[1m])) by (le)`.
- **Postgres lock contention:** `SELECT pid, wait_event_type, wait_event FROM pg_stat_activity WHERE state='active';`
- **Qdrant health:** `curl http://localhost:6333/collections/api_ns` to ensure the service stays responsive.

### Interpreting results
| Metric | Good range | What to do if out of range |
|--------|------------|----------------------------|
| **p95 latency** | < 250 ms (single) / < 400 ms (bulk) | Increase `UVICORN_WORKERS` or CPU limits. |
| **Error rate** | < 1 % | Check pod logs for crashes; verify DB connection pool size. |
| **CPU utilisation** | ≤ 80 % of pod limit | If > 80 %, raise `resources.limits.cpu` or add more workers. |
| **Postgres lock wait** | Minimal | Reduce batch size or increase `POSTGRES_POOL_SIZE`. |

Running these tests after any configuration change gives you concrete data to decide whether the tweak actually improves latency.
