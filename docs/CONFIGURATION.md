# Configuration Reference

SomaFractalMemory can be configured through three mechanisms, evaluated in the following order:
1. Explicit `config` dictionaries passed to `create_memory_system`.
2. Environment variables (with and without the `SOMA_` prefix).
3. Dynaconf settings files (e.g., `config.yaml`, based on `config.example.yaml`).

Unless stated otherwise, every option is optional and falls back to sensible defaults for local development.

---

## Core Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| `MEMORY_MODE` | Selects backend wiring (`development`, `test`, `evented_enterprise`, `cloud_managed`). | `development` |
| `REDIS_HOST` / `REDIS_PORT` | Redis connection used by the API and consumers. | `localhost` / `6379` |
| `POSTGRES_URL` | PostgreSQL DSN read by the factory and CLI. | *(unset)* |
| `QDRANT_HOST` / `QDRANT_PORT` | Qdrant endpoint when not using a local file path. | `localhost` / `6333` |
| `KAFKA_BOOTSTRAP_SERVERS` | Broker address for event publishing/consumption. | `localhost:9092` |
| `EVENTING_ENABLED` | Toggle publishing of `memory.events`. Forced to `false` in `MemoryMode.TEST`. | `true` |
| `SOMA_RATE_LIMIT_MAX` | Per-path rate limit used by `examples/api.py`. | `1000` |
| `UVICORN_WORKERS` | Worker count for the FastAPI container images. | `4` |
| `UVICORN_TIMEOUT_GRACEFUL` | Graceful shutdown timeout for the API. | `60` |
| `UVICORN_TIMEOUT_KEEP_ALIVE` | Keep-alive timeout override. | `30` |

---

## `SOMA_` Prefixed Vars (read inside `SomaFractalMemoryEnterprise`)
| Variable | Purpose | Default |
|----------|---------|---------|
| `SOMA_NAMESPACE` | Override namespace argument passed to the factory. | Namespace passed to `create_memory_system`. |
| `SOMA_MAX_MEMORY_SIZE` | Maximum stored memories before eviction logic engages. | `100000` |
| `SOMA_PRUNING_INTERVAL_SECONDS` | Sleep interval for the decay thread. | `600` |
| `SOMA_VECTOR_DIM` | Embedding dimensionality. | `768` |
| `SOMA_MODEL_NAME` | HuggingFace model used for embeddings. | `microsoft/codebert-base` |
| `SOMA_API_TOKEN` | Optional bearer token required by the FastAPI example. | *(unset)* |

Langfuse options read from Dynaconf or the same prefix:
- `SOMA_LANGFUSE_PUBLIC`
- `SOMA_LANGFUSE_SECRET`
- `SOMA_LANGFUSE_HOST`

If Langfuse is not installed these values are ignored.

---

## Kafka / Redpanda Settings
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

---

## Redis / Postgres Options
```python
config = {
    "redis": {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "testing": True,   # use fakeredis
        "enabled": True,   # only relevant in DEVELOPMENT mode
    },
    "postgres": {
        "url": "postgresql://postgres:postgres@postgres:5433/somamemory",
    },
}
```
* When both Redis and Postgres are provided in development or enterprise modes, `PostgresRedisHybridStore` caches writes in Redis while keeping Postgres canonical.
* When only one is configured, the factory falls back to the available backend. In test mode, Redis always runs in fakeredis mode.

TLS-related variables for Postgres are honoured when present:
- `POSTGRES_SSL_MODE`
- `POSTGRES_SSL_ROOT_CERT`
- `POSTGRES_SSL_CERT`
- `POSTGRES_SSL_KEY`

---

## Dynaconf (`config.yaml`)
`SomaFractalMemoryEnterprise` initialises Dynaconf with `envvar_prefix="SOMA"`. A typical `config.yaml` derived from `config.example.yaml` looks like:
```yaml
langfuse_public: "pk-lf-123"
langfuse_secret: "sk-lf-456"
langfuse_host: "http://localhost:3000"

redis:
  testing: true

qdrant:
  path: "./qdrant.db"

eventing:
  bootstrap_servers: "localhost:9092"
  schema_registry_url: "http://localhost:8080"
  topics:
    memory_events: "memory.events"
    memory_audit: "memory.audit"
    memory_dlq: "memory.dlq"

memory_enterprise:
  vector_dim: 768
  pruning_interval_seconds: 60
  decay_thresholds_seconds: [30, 300]
  decayable_keys_by_level:
    - ["scratch", "temp_notes"]
    - ["low_importance"]
```
Dynaconf values are merged with environment variables; any explicit `config` dict passed to the factory overrides both.

---

## Observability Flags
| Variable | Purpose |
|----------|---------|
| `OTEL_TRACES_EXPORTER` | Default `otlp`. Set to `none` to silence exporter errors in development. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Endpoint used when OTLP is enabled. |
| `SOMA_LANGFUSE_*` | Langfuse credentials (see above). |
| `SOMA_RATE_LIMIT_MAX` | Rate limiting for the FastAPI example. |

Metrics are always available through the Prometheus client; no switches are required.

---

## CLI JSON Configuration
The `soma` CLI accepts `--config-json` pointing to a JSON document with the same structure as the `config` dictionary (`redis`, `postgres`, `qdrant`, `eventing`, `memory_enterprise`, etc.). This provides a convenient way to reuse rich configurations outside of Docker.

---

*For operational runbooks see `docs/CANONICAL_DOCUMENTATION.md` and the quickstart guide in `docs/QUICKSTART.md`.*
