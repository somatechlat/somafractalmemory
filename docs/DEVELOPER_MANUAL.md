# Soma Fractal Memory - Developer User Manual

---

## 1. Introduction
*This section will provide a high-level overview of the project's vision, goals, and core concepts.*

## 2. System Architecture
*This section will offer a deep dive into the system's design, complete with detailed diagrams.*

### 2.1. Core Components

The Soma Fractal Memory system is designed with a clean, decoupled architecture, following the principles of Dependency Inversion and Dependency Injection.

- **`SomaFractalMemoryEnterprise`**: This is the central class of the system, located in `somafractalmemory/core.py`. It contains the core business logic for all memory operations but is completely decoupled from any specific storage technology. It operates entirely on the abstract interfaces defined in `somafractalmemory/interfaces/`.

- **Storage Interfaces**: These are the abstract base classes that define the contract for the storage layer:
    - `IKeyValueStore`: Defines the methods for a key-value store.
    - `IVectorStore`: Defines the methods for a vector store.
    - `IGraphStore`: Defines the methods for a graph store.

- **Storage Implementations**: These are the concrete implementations of the storage interfaces:
    - `PostgresRedisHybridStore`: Implements `IKeyValueStore` using PostgreSQL and Redis.
    - `QdrantVectorStore`: Implements `IVectorStore` using Qdrant.

- **`factory.py` (Dependency Injection Container)**: The `create_memory_system` function in `somafractalmemory/factory.py` acts as a pure Dependency Injection (DI) container. Its sole responsibility is to instantiate the concrete storage implementations and "inject" them into the `SomaFractalMemoryEnterprise` constructor. This decouples the core logic from the creation of its dependencies.

### 2.2. System Architecture Diagram

The following diagram provides a high-level overview of the system's architecture and the interactions between its components.

```mermaid
flowchart LR
   subgraph "Client Layer"
      CLI[CLI]
      FastAPI[FastAPI]
      gRPC[gRPC Server]
   end

   subgraph "Core System"
      Factory(create_memory_system)
      Core[SomaFractalMemoryEnterprise]
      FastCore[Fast Core Cache]
   end

   subgraph "Storage Layer"
      HybridStore[PostgresRedisHybridStore]
      Postgres[(Postgres)]
      Redis[(Redis)]
      Qdrant[(Qdrant)]
   end

   subgraph "Eventing Layer"
      Kafka[(Kafka broker)]
      Consumer[Worker Consumers]
   end

   ClientLayer --> Factory
   Factory --> Core
   Core --> HybridStore
   Core --> Qdrant
   Core --> FastCore
   HybridStore --> Postgres
   HybridStore --> Redis
   Core -- publishes events --> Kafka
   Consumer -- consumes events --> Kafka
   Consumer -- writes to --> HybridStore
   Consumer -- indexes --> Qdrant
```

### 2.3. Data Flow for `store` Operations

The following sequence diagram illustrates the process of storing a new memory in the system.

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Core as SomaFractalMemoryEnterprise
    participant HybridStore as PostgresRedisHybridStore
    participant Qdrant
    participant Kafka

    Client->>API: POST /store (memory data)
    API->>Core: store_memory(data)
    Core->>HybridStore: set(key, value)
    HybridStore->>Postgres: INSERT/UPDATE
    HybridStore->>Redis: SET (cache)
    Core->>Qdrant: upsert(vector, payload)
    Core->>Kafka: publish("memory.events", event)
```

### 2.4. Data Flow for `recall` Operations

The following sequence diagram illustrates the process of recalling a memory from the system.

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Core as SomaFractalMemoryEnterprise
    participant Qdrant
    participant HybridStore as PostgresRedisHybridStore

    Client->>API: POST /recall (query)
    API->>Core: recall(query)
    Core->>Qdrant: search(query_vector)
    Qdrant-->>Core: search_results
    Core->>HybridStore: get(key)
    HybridStore-->>Core: memory_payload
    Core-->>API: formatted_results
    API-->>Client: search_results
```

### 2.5. "Fast Core" In-Memory Cache
The "Fast Core" is an optional, in-process cache that provides ultra-low-latency recall for the most frequently accessed memories. It is implemented as a set of contiguous NumPy arrays that store vectors, importance scores, timestamps, and payloads. When enabled, the Fast Core is populated with memories as they are stored, and it is used to accelerate recall operations by avoiding the overhead of network requests to the vector store.

## 3. Getting Started

This section provides a step-by-step guide to setting up a local development environment for Soma Fractal Memory.

### 3.1. Prerequisites
Before you begin, ensure you have the following tools installed on your system:
- Docker
- Docker Compose
- Python 3.10+
- `curl`

### 3.2. Environment Setup
1.  **Clone the repository**:
    ```bash
    git clone https://github.com/somatechlat/somafractalmemory.git
    cd somafractalmemory
    ```

2.  **Install Python dependencies**:
    This project uses `pip` to manage Python dependencies. To install the project's dependencies, run:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install pre-commit hooks**:
    To ensure your code adheres to the project's style guidelines, install the pre-commit hooks:
    ```bash
    pre-commit install
    ```

## 4. Development Workflows

This section covers the common tasks you will perform during development.

### 4.1. Running the Application
The recommended way to run the full application stack is with Docker Compose:
```bash
make compose-up
```
This will start all the necessary services. By default, the services will be exposed on their standard ports. If you need to avoid port conflicts, you can set environment variables before running the command:
```bash
export POSTGRES_HOST_PORT=5434
make compose-up
```

### 4.2. Using the CLI
The project includes a command-line interface (CLI) for interacting with the memory system. To see the available commands, run:
```bash
soma --help
```

### 4.3. Running Tests
To run the test suite, use the following command:
```bash
pytest
```
To run the tests against a real infrastructure stack (instead of in-memory test doubles), set the `USE_REAL_INFRA=1` environment variable:
```bash
USE_REAL_INFRA=1 pytest
```

### 4.4. Static Analysis
To run the static analysis tools (linting, type checking, etc.), use the following commands:
- **Ruff (linting)**: `ruff check .`
- **Black (formatting)**: `black .`
- **MyPy (type checking)**: `mypy somafractalmemory`

## 5. Deployment Guide

This section provides a comprehensive guide to deploying the Soma Fractal Memory application.

### 5.1. Local Deployment with Docker Compose
For local development and testing, the project uses Docker Compose to manage the application stack. The configuration is defined in the `docker-compose.yml` file.

**To start the application:**
```bash
make compose-up
```

**To stop the application:**
```bash
make compose-down
```

### 5.2. Kubernetes Deployment with Helm
For deploying to Kubernetes, the project includes a Helm chart in the `helm/` directory. The chart supports two deployment profiles:

- **`local-dev`**: A lightweight configuration for local Kubernetes clusters.
- **`prod-ha`**: A high-availability configuration for production environments.

**To deploy for local development:**
```bash
make helm-install-local-dev
```

**To deploy for production:**
```bash
make helm-install-prod-ha
```

### 5.3. Kubernetes Deployment Diagram

The following diagram illustrates the architecture of the Kubernetes deployment.

```mermaid
graph TD
    subgraph "Kubernetes Cluster"
        subgraph "Namespace: somafractalmemory"
            Deployment --> ReplicaSet
            ReplicaSet --> Pod1[Pod: API Server]
            ReplicaSet --> Pod2[Pod: API Server]
            ReplicaSet --> Pod3[Pod: API Server]

            StatefulSet_Postgres[StatefulSet: Postgres] --> Pod_Postgres[Pod: Postgres]
            StatefulSet_Redis[StatefulSet: Redis] --> Pod_Redis[Pod: Redis]
            StatefulSet_Qdrant[StatefulSet: Qdrant] --> Pod_Qdrant[Pod: Qdrant]
            StatefulSet_Kafka[StatefulSet: Kafka] --> Pod_Kafka[Pod: Kafka]

            Service_API[Service: API] --> Pod1
            Service_API --> Pod2
            Service_API --> Pod3

            Service_Postgres[Service: Postgres] --> Pod_Postgres
            Service_Redis[Service: Redis] --> Pod_Redis
            Service_Qdrant[Service: Qdrant] --> Pod_Qdrant
            Service_Kafka[Service: Kafka] --> Pod_Kafka

            Pod_Postgres --> PVC_Postgres[PersistentVolumeClaim]
            Pod_Redis --> PVC_Redis[PersistentVolumeClaim]
            Pod_Qdrant --> PVC_Qdrant[PersistentVolumeClaim]
            Pod_Kafka --> PVC_Kafka[PersistentVolumeClaim]
        end
    end

    Ingress[Ingress Controller] --> Service_API
    Client --> Ingress
```

## 6. Advanced Topics

### 6.1. Configuration Management
The application's configuration is managed through a combination of environment variables and the `common/config/settings.py` file. For a detailed list of all configuration options, please refer to the `docs/CONFIGURATION.md` file.

### 6.2. Observability
The application is instrumented with Prometheus for metrics and OpenTelemetry for tracing.
- **Metrics**: The API server exposes a `/metrics` endpoint for Prometheus scraping.
- **Tracing**: Tracing is enabled for FastAPI, psycopg2, and Redis.

### 6.3. Extending the System
The system is designed to be extensible. You can add new storage backends, vector stores, or graph stores by implementing the interfaces defined in `somafractalmemory/interfaces/`.

## 7. Troubleshooting

- **Port Conflicts**: If you encounter port conflicts when running the Docker Compose stack, you can use the `./scripts/assign_ports_and_start.sh` script to automatically find and assign free ports.

- **Redis Connection Errors**: If you are having trouble connecting to Redis during local development, ensure that the Docker Compose stack is running and that the `REDIS_HOST` and `REDIS_PORT` environment variables are correctly configured.

- **Integration Test Failures**: If the integration tests are failing, ensure that the Docker Compose stack is running and healthy before executing the tests with `USE_REAL_INFRA=1`.

## 8. Configuration Reference

SomaFractalMemory can be configured through three mechanisms, evaluated in the following order:
1. Explicit `config` dictionaries passed to `create_memory_system`.
2. Environment variables (with and without the `SOMA_` prefix).
3. Centralised Pydantic settings file (`config.yaml` or `config.json`) loaded by `common/config/settings.py` via `load_settings`.

Unless stated otherwise, every option is optional and falls back to sensible defaults for local development.

> **Secret management:** Never commit production credentials to `.env` files. Inject `SOMA_API_TOKEN`, Langfuse keys, Fernet encryption keys, and database passwords via your secret manager (AWS Secrets Manager, Google Secret Manager, HashiCorp Vault, etc.) or CI/CD-provisioned Kubernetes/Docker secrets. The samples in this repository are placeholders only.

> **Automatic Port Assignment:** The system includes automatic port conflict detection and resolution. When using `./scripts/assign_ports_and_start.sh` or `make setup-dev`, all infrastructure ports (except the fixed Memory API port 9595) are automatically assigned to avoid conflicts with existing services. Port assignments are written to `.env` and displayed during startup.

---

### Core Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| `MEMORY_MODE` | Selects backend wiring (only `evented_enterprise`). | `evented_enterprise` |
| `SOMA_MEMORY_NAMESPACE` | Namespace passed to `create_memory_system` by `somafractalmemory/http_api.py`. | `api_ns` |
| `POSTGRES_URL` | PostgreSQL DSN read by the factory, API, CLI, and consumers. | *(unset)* |
| `REDIS_URL` / `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` | Redis connection hints (host/port/db override URL when provided). | `redis://localhost:6379/0` (Compose exposes Redis on host 6381) |
| `QDRANT_URL` or (`QDRANT_HOST`, `QDRANT_PORT`) | Qdrant endpoint when not using a local file path. | `localhost` / `6333` |
| `KAFKA_BOOTSTRAP_SERVERS` | Broker address for event publishing/consumption. | `localhost:19092` (Compose external) |
| `EVENTING_ENABLED` | When set (e.g. `false`), overrides the factory toggle via `config["eventing"]["enabled"]`. | `true` |
| `SOMA_API_TOKEN` | Required bearer token enforced by the FastAPI dependencies (provide via env or secret file). | *(secret; no default)* |
| `SOMA_RATE_LIMIT_MAX` | Redis-backed per-endpoint request budget (minimum 1; set `0` to disable). | `60` |
| `SOMA_RATE_LIMIT_WINDOW_SECONDS` | Sliding window for the limiter (seconds). | `60` |
| `UVICORN_PORT` | API process port (kept at `9595` in charts/Compose). | `9595` |
| `POSTGRES_HOST_PORT` | Host port for PostgreSQL database (auto-assigned if conflicts detected). | `5434` |
| `REDIS_HOST_PORT` | Host port for Redis cache (auto-assigned if conflicts detected). | `6380` |
| `QDRANT_HOST_PORT` | Host port for Qdrant vector store (auto-assigned if conflicts detected). | `6333` |
| `KAFKA_HOST_PORT` | Host port for Kafka broker (auto-assigned if conflicts detected). | `9092` |
| `KAFKA_OUTSIDE_PORT` | External Kafka port for host connections (auto-assigned if conflicts detected). | `19092` |
| `UVICORN_WORKERS` | Worker count for the FastAPI container images. | `4` |
| `UVICORN_TIMEOUT_GRACEFUL` | Graceful shutdown timeout for the API. | `60` |
| `UVICORN_TIMEOUT_KEEP_ALIVE` | Keep-alive timeout override. | `120` (Compose default) |
| `SOMA_CORS_ORIGINS` | Comma-separated list of allowed origins for CORS in the FastAPI service. | *(unset → CORS disabled)* |
| `SOMA_API_TOKEN_FILE` | Filesystem path to a file containing the API bearer token (e.g., mounted Kubernetes Secret). Overrides `SOMA_API_TOKEN` when present. | *(unset)* |
| `SOMA_MAX_REQUEST_BODY_MB` | Maximum allowed JSON request size in megabytes; requests exceeding this are rejected. | *(unset → default limit)* |

---

#### Kubernetes secrets & TLS defaults
- The Helm chart now provisions a `Secret` when `secret.enabled=true` (default). Populate `secret.data` with connection strings and tokens, or set `secret.existingSecret` to reference a managed secret.
- Sensitive defaults include `POSTGRES_URL` with `?sslmode=require`; ensure your Postgres endpoint presents a trusted certificate or override the value for non-TLS development clusters.
- When the ingress is enabled, TLS is expected (`ingress.tls=true` by default). Provide `ingress.tlsSecretName` or allow cert-manager to issue a certificate that matches the host.

---

### `SOMA_` Prefixed Vars (read inside `SomaFractalMemoryEnterprise`)
| Variable | Purpose | Default |
|----------|---------|---------|
| `SOMA_NAMESPACE` | Override namespace argument passed to the factory. | Namespace passed to `create_memory_system`. |
| `SOMA_MAX_MEMORY_SIZE` | Maximum stored memories before eviction logic engages. | `100000` |
| `SOMA_PRUNING_INTERVAL_SECONDS` | Sleep interval for the decay thread. | `600` |
| `SOMA_VECTOR_DIM` | Embedding dimensionality. | `768` |
| `SOMA_MODEL_NAME` | HuggingFace model used for embeddings. | `microsoft/codebert-base` |
| `SOMA_API_TOKEN` | Required bearer token enforced by the FastAPI example. | *(secret; no default)* |
| `SFM_FAST_CORE` | Enable flat in-process contiguous vector slabs (fast path). Accepts `1/true/yes`. | `0` |
| `SOMA_HYBRID_RECALL_DEFAULT` | Make hybrid recall (vector + keyword boosts) the default for `/recall`. Accepts `1/true/yes` to enable or `0/false/no` to disable. | `1` |

Langfuse options (loaded by Pydantic settings via `common/config/settings.py`, env prefix `SOMA_`):
- `SOMA_LANGFUSE_PUBLIC`
- `SOMA_LANGFUSE_SECRET`
- `SOMA_LANGFUSE_HOST`

If Langfuse is not installed these values are ignored.

> **Namespace layering:** `somafractalmemory/http_api.py` reads `SOMA_MEMORY_NAMESPACE` (default `api_ns`) when it builds the factory config. Inside `SomaFractalMemoryEnterprise`, `SOMA_NAMESPACE` still overrides whatever the caller passed—use it for last-mile overrides when embedding the library directly.

---

### Kafka Settings
Environment variables consumed by the producer (`eventing/producer.py`) and consumer (`scripts/run_consumers.py`):

| Variable | Purpose |
|----------|---------|
| `KAFKA_BOOTSTRAP_SERVERS` | Comma-separated broker list. |
| `KAFKA_SECURITY_PROTOCOL` | `PLAINTEXT`, `SSL`, or `SASL_SSL`. |
| `KAFKA_SSL_CA_LOCATION` | Path to CA certificate when using TLS. |
| `KAFKA_SASL_MECHANISM` | SASL mechanism (`PLAIN`, etc.). |
| `KAFKA_SASL_USERNAME` / `KAFKA_SASL_PASSWORD` | SASL credentials. |
| `KAFKA_MEMORY_EVENTS_TOPIC` | Topic name for produced events (default `memory.events`). |
| `KAFKA_CONSUMER_GROUP` | Consumer group id used by the worker (`soma-consumer-group`). |
| `CONSUMER_METRICS_PORT` | HTTP port for the consumer metrics server (`8001`). |

---

### Dependency Management (uv)
This repository uses Astral’s uv for dependency management to ensure fast and reproducible installs.

- Runtime installs (API + Kafka events):
  - `uv sync --extra api --extra events`
- With developer tooling (pytest, linters):
  - `uv sync --extra dev --extra api --extra events`
- Locking for CI/CD:
  - `uv lock` produces `uv.lock` (note: `uv lock` does not accept `--extra`; select extras at install time via `uv sync --extra ...`).

Docker images use uv inside the container. If `uv.lock` is present at the repo root, builds run `uv sync --frozen`; otherwise, the image build will resolve and create a lock on the fly.

### Qdrant Configuration Options
When passing a `config` dict to `create_memory_system`, Qdrant supports:

```python
config = {
    "qdrant": {
        "path": "./qdrant.db",    # local store
        # OR
        "url": "http://localhost:6333",
        "host": "qdrant",
        "port": 6333,
        "location": ":memory:",  # in-memory snapshot
    },
    "vector": {"backend": "qdrant"},
}
```
The factory ensures mutually exclusive use of `path` vs. network connection parameters.

Collections and consumers:
- The API uses the provided namespace as the collection name when wired to Qdrant.
- The vector indexing worker indexes into `$QDRANT_COLLECTION` (default `memory_vectors`), the namespace collection (when provided), and optionally `$QDRANT_EXTRA_COLLECTION` if set.
- Tests and diagnostics may probe multiple collections (`$QDRANT_COLLECTION`, `memory_vectors`, `default`, `api_ns`) using payload filters for deterministic presence checks.

---

### Redis / Postgres Options
```python
config = {
    "redis": {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "testing": True,   # use fakeredis
  "enabled": True,   # enable Redis cache when a host is available
    },
    "postgres": {
  "url": "postgresql://postgres:postgres@postgres:5432/somamemory",
    },
}
```
* When both Redis and Postgres are provided, `PostgresRedisHybridStore` caches writes in Redis while keeping Postgres canonical.
* When only one is configured, the factory falls back to the available backend. In test mode, Redis always runs in fakeredis mode.

When `POSTGRES_URL` is configured, the API and core will attempt to leverage Postgres features (e.g., pg_trgm) when present for faster keyword paths. If permissions are restricted, the system falls back gracefully to KV scanning for `keyword_search` and the keyword phase of hybrid recall.

TLS-related variables for Postgres are honoured when present:
- `POSTGRES_SSL_MODE`
- `POSTGRES_SSL_ROOT_CERT`
- `POSTGRES_SSL_CERT`
- `POSTGRES_SSL_KEY`

To disable Kafka publishing without editing source, set `EVENTING_ENABLED=false` in the environment; the FastAPI wiring will feed `{"eventing": {"enabled": False}}` into the factory.

---

### Testing against real infrastructure

- Set `USE_REAL_INFRA=1` to enable tests that bind to running local services (Docker Compose defaults: Postgres 5433, Redis 6381, Qdrant 6333, Kafka 19092). The `conftest.py` helper auto-detects reachable ports and exports them as environment variables for the tests.
- Integration tests verify Qdrant vector presence deterministically using payload filters and will probe across collections to avoid scroll-order flakiness in large datasets.

---

### Centralised Settings File (`config.yaml` or `config.json`)
The service loads Pydantic settings via `common/config/settings.py::load_settings`, which supports JSON or YAML files merged with environment variables (env prefix `SOMA_`). A minimal YAML example:
```yaml
langfuse_public: "pk-lf-123"
langfuse_secret: "sk-lf-456"
langfuse_host: "http://localhost:3000"

redis:
  testing: true

qdrant:
  path: "./qdrant.db"

eventing:
  bootstrap_servers: "localhost:19092"
  topics:
    memory_events: "memory.events"

memory_enterprise:
  vector_dim: 768
  pruning_interval_seconds: 60
  decay_thresholds_seconds: [30, 300]
  decayable_keys_by_level:
    - ["scratch", "temp_notes"]
    - ["low_importance"]
```
Settings file values are merged with environment variables; any explicit `config` dict passed to the factory overrides both.

---

### Observability Flags
| Variable | Purpose |
|----------|---------|
| `OTEL_TRACES_EXPORTER` | Default `otlp`. Set to `none` to silence exporter errors in development. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Endpoint used when OTLP is enabled. |
| `SOMA_LANGFUSE_*` | Langfuse credentials (see above). |
| `SOMA_RATE_LIMIT_MAX` | Redis-backed per-endpoint request budget for the FastAPI example (default `60`). |
| `SOMA_RATE_LIMIT_WINDOW_SECONDS` | Customise the limiter window size if the default 60 s bucket is too coarse. |

Metrics (`api_requests_total`, `api_request_latency_seconds`, `http_404_requests_total`) are emitted via the Prometheus client. Hit at least one endpoint after startup so counters appear on `/metrics`.

Helm defaults also export `POSTGRES_POOL_SIZE`, `SKIP_SCHEMA_VALIDATION`, and `VECTOR_INDEX_ASYNC` for forward compatibility. These variables are currently ignored by the FastAPI example but kept in the chart so future releases can wire them without additional template churn.

---

### Adaptive Importance Normalization

Stored memories may include a raw `importance` (any numeric scale). The system maintains an adaptive normalization to `importance_norm ∈ [0,1]` used directly in similarity scoring (score = cosine_similarity * importance_norm).

Decision tree (executed per insert):
1. Warm‑up (<64 samples): plain min–max scaling using observed running min/max.
2. Stable distribution with moderate tails (R_tail_max ≤ 5 and R_asym ≤ 3): continue plain min–max.
3. Moderate heavy tail (R_tail_max ≤ 15 and R_tail_ext ≤ 8): winsorized scaling – clamp to [q10 − 0.25*(q90−q10), q90 + 0.25*(q90−q10)] then min–max.
4. Extreme tail (otherwise): logistic mapping around median q50 with slope k = ln(9)/(q90−q10) (capped for numerical stability) to compress extremes.

Where:
R_tail_max = (max - q90) / (q90 - q50)
R_tail_ext = (q99 - q90) / (q90 - q50)
R_asym = (q90 - q50) / (q50 - q10)

Quantiles (q10, q50, q90, q99) are recomputed every 64 inserts using a 512‑sample reservoir. The selected method (`minmax`, `winsor`, `logistic`) is stored alongside each memory in `importance_norm` and may be inspected for diagnostics.

This keeps the scoring path branch‑free during recall (a simple multiply) while adapting to distribution shifts without external configuration.

---

### CLI JSON Configuration
The `soma` CLI accepts `--config-json` pointing to a JSON document with the same structure as the `config` dictionary (`redis`, `postgres`, `qdrant`, `eventing`, `memory_enterprise`, etc.). This provides a convenient way to reuse rich configurations outside of Docker.
