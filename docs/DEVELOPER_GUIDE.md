# SomaFractalMemory – Developer & User Guide

## Table of Contents
- [Project Overview](#project-overview)
- [Architecture Overview](#architecture-overview)
- [Docker Compose Setup](#docker-compose-setup)
- [Environment Configuration (`.env`)](#environment-configuration-env)
- [Running the Stack (Development Mode)](#running-the-stack-development-mode)
- [CLI Helper (`configure.sh`)](#cli-helper-configuresh)
- [API Usage](#api-usage)
- [Testing](#testing)
- [Cleaning Up & Data Persistence](#cleaning-up--data-persistence)
- [FAQ & Troubleshooting](#faq--troubleshooting)

---

## Project Overview
`SomaFractalMemory` is a modular, agent‑centric memory system written in Python. It provides:
- **Hybrid storage**: Redis (cache), PostgreSQL (canonical KV), Qdrant (vector similarity).
- **Event streaming** via Redpanda (Kafka‑compatible) for enterprise‑grade pipelines.
- **FastAPI** HTTP API exposing store/recall, graph operations, and admin functionality.
- **Dynamic configuration** – switch between `development`, `test`, `evented_enterprise`, and `cloud_managed` modes without losing data.

The repository contains:
- Core library (`somafractalmemory/`)
- Example FastAPI app (`examples/api.py`)
- Docker configuration (`docker-compose.yml`, `Dockerfile`)
- Documentation (`docs/`)
- Test suite (`tests/`)

---

## Architecture Overview
For a high‑level diagram see `docs/ARCHITECTURE.md`. In short:
```
+-------------------+   +-------------------+   +-------------------+
|   FastAPI API    | → |   OpenAPI JSON    | ← |   MkDocs site    |
+-------------------+   +-------------------+   +-------------------+
|   Docker Compose  | → |   start_stack.sh  |
+-------------------+   +-------------------+
```
**Key components**
| Service | Image | Role |
|---|---|---|
| `redis` | `redis:7` | In‑memory KV cache with AOF persistence |
| `qdrant` | `qdrant/qdrant:latest` | Vector similarity store |
| `postgres` | `postgres:15-alpine` | Relational KV store (used in enterprise modes) |
| `redpanda` | `redpandadata/redpanda:latest` | Kafka‑compatible event broker |
| `api` | Built from local `Dockerfile` | FastAPI server exposing the memory API |
| `consumer` | Same image as `api` | Background worker consuming `memory.events` |
---

## Docker Compose Setup
All services are defined in `docker-compose.yml`.  The file **does not expose** the Redis port to the host (to avoid port conflicts) and PostgreSQL is bound to host port **5433**.

### 1. Create the environment file
```bash
cp .env.example .env   # edit if you need custom values
```
The default `.env` contains:
```
MEMORY_MODE=development
REDIS_HOST=redis
REDIS_PORT=6379
POSTGRES_URL=postgresql://postgres:postgres@postgres:5433/somamemory
QDRANT_HOST=qdrant
QDRANT_PORT=6333
KAFKA_BOOTSTRAP_SERVERS=redpanda:9092
EVENTING_ENABLED=true
```
### 2. Build the Docker images (only needed after code changes)
```bash
docker compose build
```
### 3. Start the stack in detached mode
```bash
docker compose up -d
```
All containers will start and attach to a shared Docker network, allowing them to reach each other via the service names defined in the compose file.

### 4. Verify the stack
```bash
docker compose ps
```
You should see the backing services (`soma_redis`, `soma_qdrant`, `soma_postgres`, `soma_redpanda`) plus the API / consumer containers with **Status: Up**.

---

## Environment Configuration (`.env`)
The FastAPI app loads **every** variable from the shared `.env` (thanks to `env_file: .env` entries for each service).  Changing a value and restarting the `api` service is enough – the other containers keep their data.

| Variable | Description | Typical values |
|---|---|---|
| `MEMORY_MODE` | Determines which backend mix is used. Options: `development`, `test`, `evented_enterprise`, `cloud_managed`. | `development` |
| `REDIS_HOST` / `REDIS_PORT` | Hostname and port of the Redis cache (service name `redis`). | `redis` / `6379` |
| `POSTGRES_URL` | Full DSN for PostgreSQL. Note the host is `postgres` and the port is **5433** on the host side. | `postgresql://postgres:postgres@postgres:5433/somamemory` |
| `QDRANT_HOST` / `QDRANT_PORT` | Hostname and port of the Qdrant vector store. | `qdrant` / `6333` |
| `KAFKA_BOOTSTRAP_SERVERS` | Address of the Redpanda broker. | `redpanda:9092` |
| `EVENTING_ENABLED` | Toggle event publishing. Set to `false` in pure test mode. | `true` |

---

## Running the Stack (Development Mode)
Development mode (`MEMORY_MODE=development`) uses Redis + Qdrant only – PostgreSQL is still started but not required.

```bash
# 1️⃣ Ensure .env is set to development
sed -i '' 's/^MEMORY_MODE=.*/MEMORY_MODE=development/' .env

# 2️⃣ (Re)build and start
docker compose up -d --build
```
The API is now reachable at **http://localhost:9595**.

---

## Managing the stack
Use the helper script to start the full suite of services for development parity:
```bash
./scripts/start_stack.sh evented_enterprise
docker compose up -d api consumer
```
Edit `.env` as needed (for example to change `MEMORY_MODE`) and rerun the commands above so the containers restart with the new configuration.

### Optional sandbox API
For stress tests, start the sandbox instance on port 8888:
```bash
docker compose up -d test_api
```
Stop it with `docker compose rm -sf test_api` when you’re done.

### Kubernetes stack
Use Helm to spin up the full production-like stack inside a cluster:
```bash
helm install sfm ./helm \
  --set image.repository="somatechlat/somafractalmemory" \
  --set image.tag="2.0"
```
The chart provisions Postgres, Redis, Qdrant, and Redpanda alongside the API and consumer. Customize behaviour with `values.yaml` (e.g., disable persistence or supply external service endpoints). Tear everything down via `helm uninstall sfm`.

### Performance knobs
- `SOMA_RATE_LIMIT_MAX` (default `5000`) controls per-endpoint throttling.
- `UVICORN_WORKERS` and `UVICORN_TIMEOUT_GRACEFUL` let you scale request throughput—set them in `.env` or pass via Helm/Docker Compose.

---

## API Usage
The FastAPI server exposes a rich set of endpoints (see `examples/api.py`).  The most important groups are:
- **Memory operations** – `/store`, `/recall`, `/recall_batch`, `/store_bulk`, etc.
- **Graph operations** – `/link`, `/neighbors`, `/shortest_path`.
- **System** – `/stats`, `/health`, `/metrics`.
- **Admin** – `/export_memories`, `/import_memories`, `/delete_many`.

All endpoints are documented automatically in the OpenAPI spec (`openapi.json`) generated on startup.  You can view Swagger UI at **http://localhost:9595/docs**.

---

## Testing
Run the full test suite with:
```bash
pytest -q
```
The tests use the **in‑memory** implementations (no Docker needed) and therefore run quickly.  They also verify that the Docker‑compose file parses.

---

## Cleaning Up & Data Persistence
All stateful services use **named Docker volumes**:
- `redis_data`
- `qdrant_storage`
- `postgres_data`
- `redpanda_data`
These survive container recreation and `docker compose down`.  To wipe everything (useful for a fresh start) run:
```bash
docker compose down -v
```
Be aware that this permanently deletes all stored memories.

---

## FAQ & Troubleshooting
**Q: Port 5432 is already in use.**
- The compose file maps PostgreSQL to host port **5433**. Update your `.env` accordingly (the default already does this).

**Q: Redis refuses to start because the port is taken.**
- The Redis service no longer publishes a host port. It is reachable only inside the Docker network via the service name `redis`.

**Q: After changing a variable the API does not reflect the new value.**
- Edit `.env`, then rerun `./scripts/start_stack.sh evented_enterprise` followed by `docker compose up -d api dev_api consumer` so the containers pick up the new values.

**Q: How do I add a new service (e.g., a custom vector store)?**
- Add the service definition to `docker-compose.yml`.
- Add a corresponding entry in `.env.example`.
- Extend `factory.create_memory_system` to recognise a new mode or configuration block.

### Tracing in development
OpenTelemetry tracing is enabled by default. Provide `OTEL_EXPORTER_OTLP_ENDPOINT` if you run a collector, or disable it locally with `OTEL_TRACES_EXPORTER=none` to avoid connection errors in the logs.

---

# End of Guide

For any further questions, open an issue on the repository or consult the detailed architecture diagram in `docs/ARCHITECTURE.md`.
