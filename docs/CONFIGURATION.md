# Configuration Reference

SomaFractalMemory can be configured through three mechanisms, evaluated in the following order:
1. Explicit `config` dictionaries passed to `create_memory_system`.
2. Environment variables (with and without the `SOMA_` prefix).
3. Centralised Pydantic settings file (`config.yaml` or `config.json`) loaded by `common/config/settings.py` via `load_settings`.

Unless stated otherwise, every option is optional and falls back to sensible defaults for local development.

> **Secret management:** Never commit production credentials to `.env` files. Inject `SOMA_API_TOKEN`, Langfuse keys, Fernet encryption keys, and database passwords via your secret manager (AWS Secrets Manager, Google Secret Manager, HashiCorp Vault, etc.) or CI/CD-provisioned Kubernetes/Docker secrets. The samples in this repository are placeholders only.

---

## Core Environment Variables
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
| `UVICORN_WORKERS` | Worker count for the FastAPI container images. | `4` |
| `UVICORN_TIMEOUT_GRACEFUL` | Graceful shutdown timeout for the API. | `60` |
| `UVICORN_TIMEOUT_KEEP_ALIVE` | Keep-alive timeout override. | `120` (Compose default) |
| `SOMA_CORS_ORIGINS` | Comma-separated list of allowed origins for CORS in the FastAPI service. | *(unset → CORS disabled)* |
| `SOMA_API_TOKEN_FILE` | Filesystem path to a file containing the API bearer token (e.g., mounted Kubernetes Secret). Overrides `SOMA_API_TOKEN` when present. | *(unset)* |
| `SOMA_MAX_REQUEST_BODY_MB` | Maximum allowed JSON request size in megabytes; requests exceeding this are rejected. | *(unset → default limit)* |

---

### Kubernetes secrets & TLS defaults
- The Helm chart now provisions a `Secret` when `secret.enabled=true` (default). Populate `secret.data` with connection strings and tokens, or set `secret.existingSecret` to reference a managed secret.
- Sensitive defaults include `POSTGRES_URL` with `?sslmode=require`; ensure your Postgres endpoint presents a trusted certificate or override the value for non-TLS development clusters.
- When the ingress is enabled, TLS is expected (`ingress.tls=true` by default). Provide `ingress.tlsSecretName` or allow cert-manager to issue a certificate that matches the host.

---

## `SOMA_` Prefixed Vars (read inside `SomaFractalMemoryEnterprise`)
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

## Kafka Settings
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

## Dependency Management (uv)
This repository uses Astral’s uv for dependency management to ensure fast and reproducible installs.

- Runtime installs (API + Kafka events):
  - `uv sync --extra api --extra events`
- With developer tooling (pytest, linters):
  - `uv sync --extra dev --extra api --extra events`
- Locking for CI/CD:
  - `uv lock` produces `uv.lock` (note: `uv lock` does not accept `--extra`; select extras at install time via `uv sync --extra ...`).

Docker images use uv inside the container. If `uv.lock` is present at the repo root, builds run `uv sync --frozen`; otherwise, the image build will resolve and create a lock on the fly.

## Qdrant Configuration Options
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

## Redis / Postgres Options
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

## Testing against real infrastructure

- Set `USE_REAL_INFRA=1` to enable tests that bind to running local services (Docker Compose defaults: Postgres 5433, Redis 6381, Qdrant 6333, Kafka 19092). The `conftest.py` helper auto-detects reachable ports and exports them as environment variables for the tests.
- Integration tests verify Qdrant vector presence deterministically using payload filters and will probe across collections to avoid scroll-order flakiness in large datasets.

---

## Centralised Settings File (`config.yaml` or `config.json`)
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

## Observability Flags
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

## Adaptive Importance Normalization

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

## CLI JSON Configuration
The `soma` CLI accepts `--config-json` pointing to a JSON document with the same structure as the `config` dictionary (`redis`, `postgres`, `qdrant`, `eventing`, `memory_enterprise`, etc.). This provides a convenient way to reuse rich configurations outside of Docker.

---

*For operational runbooks see `docs/CANONICAL_DOCUMENTATION.md` and the quickstart guide in `docs/QUICKSTART.md`.*
