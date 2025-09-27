# Configuration Reference# Configuration Guide



This document enumerates all configuration options used by **SomaFractalMemory**. Options are read from environment variables (via `os.getenv`) or from a Dynaconf configuration file (`config.yaml`). Values are optional; defaults are shown where applicable.This project uses **Dynaconf** and environment variables (prefix `SOMA_`) for configuration. You can:

- Provide a `config.yaml` alongside your app

---- Override values via environment variables

- Pass a `config` dict to `create_memory_system()` in code

## Core Settings (environment variables)

## Top‑Level Keys (Dynaconf section names)

| Variable | Default | Description |

|----------|---------|-------------|| Section | Sub‑keys | Env‑var prefix | Description |

| `SOMA_NAMESPACE` | *Provided namespace argument* | Namespace prefix for all keys stored in KV, vector, and graph back‑ends. ||---------|----------|----------------|-------------|

| `SOMA_MAX_MEMORY_SIZE` | `100000` | Maximum number of memories before eviction policy runs. || `redis` | `host`, `port`, `db`, `testing`, `enabled` | `SOMA_REDIS__*` | Redis client options. `testing` forces `fakeredis`. `enabled` (default **true**) toggles the optional Redis cache in `DEVELOPMENT` mode. |

| `SOMA_PRUNING_INTERVAL_SECONDS` | `600` | Interval (seconds) for background pruning/decay thread. || `qdrant` | `path`, `url`, `host`, `location` | `SOMA_QDRANT__*` | Qdrant client options. `path` selects a local on‑disk store; `url`/`host`/`location` are for remote deployments. |

| `SOMA_VECTOR_DIM` | `768` | Dimensionality of embedding vectors. || `postgres` | `url`, `sslmode`, `sslrootcert`, `sslcert`, `sslkey` | `POSTGRES_*` (no `SOMA_` prefix – read directly by `psycopg2`) | PostgreSQL connection. TLS settings are optional; see **TLS / SASL Configuration** below. |

| `SOMA_MODEL_NAME` | `microsoft/codebert-base` | HuggingFace model name for text embedding (fallback to hash‑based embeddings if unavailable). || `memory_enterprise` | `vector_dim`, `pruning_interval_seconds`, `decay_thresholds_seconds`, `decayable_keys_by_level`, `decay_enabled`, `reconcile_enabled`, `max_memory_size`, `encryption_key` | `SOMA_*` (individual vars) | Core memory‑system tuning. |

| `SOMA_API_TOKEN` | – | API token used by example scripts (not required for core library). || `external_prediction` | `api_key`, `endpoint` | `SOMA_EXTERNAL_PREDICTION__*` | If present, the factory uses `ExternalPredictionProvider` instead of the default/no‑op provider. |

| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker URL for event publishing. || `eventing` | `enabled` | `SOMA_EVENTING__ENABLED` | When **true** (default) the core publishes a `memory.events` Kafka message after each successful `store_memory`. |

| `KAFKA_SECURITY_PROTOCOL` | `PLAINTEXT` | Kafka security protocol (e.g., `SSL`, `SASL_SSL`). || `langfuse` | `public`, `secret`, `host` | `SOMA_LANGFUSE_*` | Langfuse observability integration. |

| `KAFKA_SSL_CA_LOCATION` | – | Path to CA certificate for TLS connections. || `model` | `name` | `SOMA_MODEL_NAME` | HuggingFace model name for embeddings (fallback to hash‑based vectors if unavailable). |

| `KAFKA_SASL_MECHANISM` | `PLAIN` | SASL mechanism if using SASL authentication. |

| `KAFKA_SASL_USERNAME` | *(empty)* | SASL username. |## Detailed Sub‑sections

### Observability helpers
- `OTEL_TRACES_EXPORTER` – Defaults to `otlp`. Set to `none` when no collector is available in development.
- `OTEL_EXPORTER_OTLP_ENDPOINT` – HTTP(s) endpoint for the OTLP exporter when traces are enabled.

### API throttling
- `SOMA_RATE_LIMIT_MAX` – Maximum requests per minute per endpoint (default `1000`). Increase for load tests.

| `KAFKA_SASL_PASSWORD` | *(empty)* | SASL password. |

| `KAFKA_MEMORY_EVENTS_TOPIC` | `memory.events` | Kafka topic name for memory events. |### Redis

| `KAFKA_CONSUMER_GROUP` | `soma-consumer-group` | Consumer group identifier for event consumers. |```yaml

| `CONSUMER_METRICS_PORT` | `8001` | Prometheus metrics port for consumer processes. |redis:

| `QDRANT_URL` | `http://localhost:6333` | Base URL for Qdrant vector store. |  host: localhost          # SOMA_REDIS__HOST

| `QDRANT_COLLECTION` | *namespace* | Collection name (defaults to the memory namespace). |  port: 6379               # SOMA_REDIS__PORT

| `QDRANT_TLS` | `false` | Enable TLS for Qdrant connections. |  db: 0                    # SOMA_REDIS__DB

| `QDRANT_TLS_CERT` | – | Path to client certificate for Qdrant TLS. |  testing: false           # SOMA_REDIS__TESTING – use FakeRedis when true (CI)

| `POSTGRES_URL` | – | PostgreSQL connection URL (e.g., `postgresql://user:pass@host/db`). |  enabled: true            # SOMA_REDIS__ENABLED – toggle cache usage in DEVELOPMENT mode

| `POSTGRES_SSL_MODE` | – | SSL mode for PostgreSQL (`require`, `verify-ca`, etc.). |```

| `POSTGRES_SSL_ROOT_CERT` | – | Path to root CA certificate for PostgreSQL. |

| `POSTGRES_SSL_CERT` | – | Path to client certificate for PostgreSQL. |### Qdrant

| `POSTGRES_SSL_KEY` | – | Path to client private key for PostgreSQL. |```yaml

| `MEMORY_VECTOR_DIM` | `768` | Alias for `SOMA_VECTOR_DIM` used by workers. |qdrant:

| `SOMA_ENTERPRISE_TESTING` | `0` | If set to `1`/`true`, enables deterministic test mode for enterprise examples. |  path: ./qdrant.db        # SOMA_QDRANT__PATH – local on‑disk store

  # or remote configuration

---  url: http://qdrant:6333   # SOMA_QDRANT__URL

  # host / location alternatives are also supported

## Dynaconf Settings (in `config.yaml` or other Dynaconf files)```



| Setting | Default | Description |### PostgreSQL (TLS)

|----------|---------|-------------|```yaml

| `langfuse_public` | `pk-lf-123` | Public key for Langfuse observability integration. |postgres:

| `langfuse_secret` | `sk-lf-456` | Secret key for Langfuse. |  url: postgresql://soma:soma@localhost:5432/soma

| `langfuse_host` | `http://localhost:3000` | Host URL for Langfuse server. |  sslmode: require          # POSTGRES_SSL_MODE – disable/require/verify-ca/verify-full

| `eventing.enabled` | `true` (development) / `false` (test) | Toggle Kafka event publishing. |  sslrootcert: /path/to/ca.pem   # POSTGRES_SSL_ROOT_CERT

| `redis.enabled` | `true` (development) | Enable Redis KV cache. |  sslcert: /path/to/client.pem   # POSTGRES_SSL_CERT

| `redis.host`, `redis.port` | *defaults from Redis client* | Connection details for Redis. |  sslkey: /path/to/client.key   # POSTGRES_SSL_KEY

| `vector.backend` | `qdrant` (if configured) else `inmemory` | Choose vector store backend. |```

| `vector.path` | `:memory:` | Filesystem path for in‑memory Qdrant instance. |

| `memory_enterprise.max_memory_size` | `100000` | Mirrors `SOMA_MAX_MEMORY_SIZE`. |### Memory Enterprise Settings

| `memory_enterprise.pruning_interval_seconds` | `600` | Mirrors `SOMA_PRUNING_INTERVAL_SECONDS`. |```yaml

| `memory_enterprise.decay_thresholds_seconds` | `[]` | List of age thresholds (seconds) for decay. |memory_enterprise:

| `memory_enterprise.decayable_keys_by_level` | `[]` | Keys to drop at each decay level. |  vector_dim: 768                     # SOMA_VECTOR_DIM

| `memory_enterprise.decay_enabled` | `true` | Enable/disable decay logic. |  pruning_interval_seconds: 600       # SOMA_PRUNING_INTERVAL_SECONDS

| `memory_enterprise.reconcile_enabled` | `true` | Enable WAL reconciliation. |  decay_thresholds_seconds: [30, 300]

| `external_prediction.api_key` | – | API key for external prediction provider (if used). |  decayable_keys_by_level: [["scratch"], ["low_importance"]]

| `external_prediction.endpoint` | – | HTTP endpoint for external prediction service. |  decay_enabled: true                 # SOMA_DECAY_ENABLED

  reconcile_enabled: true             # SOMA_RECONCILE_ENABLED

---  max_memory_size: 100000            # SOMA_MAX_MEMORY_SIZE

  encryption_key: <base64‑key>        # optional, used to encrypt `task` and `code`

## How to Override```



- **Environment variables** take precedence over Dynaconf values.### External Prediction Provider

- For local development, create a `config.example.yaml` (already provided) and copy it to `config.yaml`.```yaml

- When deploying via Docker/Kubernetes, inject the required variables as secrets or ConfigMaps.external_prediction:

  api_key: your_api_key

---  endpoint: https://api.example.com/predict

```

For a complete list of all variables, see the source code in `somafractalmemory/core.py`, `somafractalmemory/implementations/storage.py`, and the Kafka producer in `eventing/producer.py`.If this block is present, `create_memory_system` will instantiate `ExternalPredictionProvider`.


### Event Publishing
```yaml
eventing:
  enabled: true   # SOMA_EVENTING__ENABLED – set false to skip Kafka emission
```
The Kafka producer reads the following **KAFKA_*** environment variables (see `eventing/producer.py`):
- `KAFKA_BOOTSTRAP_SERVERS` (required)
- `KAFKA_SECURITY_PROTOCOL` (default `PLAINTEXT`)
- `KAFKA_SSL_CA_LOCATION`
- `KAFKA_SASL_MECHANISM`
- `KAFKA_SASL_USERNAME`
- `KAFKA_SASL_PASSWORD`

### TLS / SASL Configuration (for external services)
| Service | Env vars | Purpose |
|---------|----------|---------|
| **PostgreSQL** | `POSTGRES_SSL_MODE`, `POSTGRES_SSL_ROOT_CERT`, `POSTGRES_SSL_CERT`, `POSTGRES_SSL_KEY` | Secure DB connections. |
| **Qdrant** | `QDRANT_TLS`, `QDRANT_TLS_CERT` | Enable TLS for remote Qdrant. |
| **Kafka** | `KAFKA_SECURITY_PROTOCOL`, `KAFKA_SSL_CA_LOCATION`, `KAFKA_SASL_MECHANISM`, `KAFKA_SASL_USERNAME`, `KAFKA_SASL_PASSWORD` | Secure Kafka communication. |

## Precedence Order
1. **Explicit `config` dict** passed to `create_memory_system`
2. **Environment variables** (`SOMA_*`, `POSTGRES_*`, `KAFKA_*`)
3. **`config.yaml`** loaded by Dynaconf (if present)

## Example `config.yaml`
See `config.example.yaml` for a ready‑to‑copy template that includes all sections above.

---

*The documentation above reflects the current codebase (v2.0). All keys are actively read by the factory or the relevant component.*
