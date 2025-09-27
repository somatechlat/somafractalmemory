# Canonical Documentation for SomaFractalMemory

## Overview
This repository implements a modular agentic memory system with multiple back‑ends (PostgreSQL, Redis, Qdrant, Redpanda) and a FastAPI service. The architecture is described in `docs/ARCHITECTURE.md`.

## Docker Compose Setup
*(see the Docker section in the main `README.md` for a quick start)*
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Build the images:
   ```bash
   docker compose build
   ```
3. Launch the stack:
   ```bash
   docker compose up -d
   ```
   - Services: `redis`, `qdrant`, `postgres`, `redpanda`, `api`, `consumer`.
   - All services load the same `.env` via `env_file: .env` entries.
4. Access the API at `http://localhost:9595`.
5. To change configuration, edit `.env` and re-run the stack commands listed below.

## Configuration
Environment variables control the memory mode and connections. Key variables:
- `MEMORY_MODE` – `development`, `test`, `evented_enterprise`, `cloud_managed`
- `REDIS_HOST`, `REDIS_PORT`
- `POSTGRES_URL`
- `QDRANT_HOST`, `QDRANT_PORT`
- `KAFKA_BOOTSTRAP_SERVERS`
- `EVENTING_ENABLED`

## Running Tests
```bash
pytest -q
```
All tests pass against the in‑memory implementations.

## Documentation
- Architecture details: `docs/ARCHITECTURE.md`
- API reference: `docs/api.md`
- Configuration reference: `docs/CONFIGURATION.md`

## Services Overview

| Service | Image | Purpose |
|---------|-------|---------|
| **redis** | `redis:7` | In‑memory KV cache with AOF persistence. |
| **qdrant** | `qdrant/qdrant:latest` | Vector similarity store for embeddings. |
| **postgres** | `postgres:15-alpine` | Canonical relational store (used in enterprise modes). |
| **redpanda** | `redpandadata/redpanda:latest` | Kafka‑compatible event broker for memory event streaming. |
| **api** | Built from local `Dockerfile` | FastAPI server exposing the memory API. |
| **consumer** | Built from local `Dockerfile` | Background worker consuming `memory.events` and updating stores. |

## Environment Variables

All services read configuration from a shared `.env` file (loaded via `env_file: .env`). Key variables:

- `MEMORY_MODE` – `development`, `test`, `evented_enterprise`, `cloud_managed`.
- `REDIS_HOST` / `REDIS_PORT` – connection to Redis.
- `POSTGRES_URL` – full PostgreSQL DSN (includes port, e.g., `postgresql://postgres:postgres@postgres:5433/somamemory`).
- `QDRANT_HOST` / `QDRANT_PORT` – connection to Qdrant.
- `KAFKA_BOOTSTRAP_SERVERS` – Redpanda broker address.
- `EVENTING_ENABLED` – `true`/`false` to toggle event publishing.

The file `/.env.example` provides a template; copy it to `.env` before starting the stack.

## Dynamic Configuration

### Running the full stack
Launch the backing services that mirror production:

```bash
./scripts/start_stack.sh evented_enterprise
docker compose up -d api consumer
```

When `.env` changes (for example, switching `MEMORY_MODE`), re-run the commands above so the containers pick up the new environment.

### Optional sandbox API
For load testing without touching the primary instance, start the sandbox server:

```bash
docker compose up -d test_api
```
This exposes the API on `http://localhost:8888` while reusing the same backends.

### Kubernetes deployment
Deploy the full stack (API, consumer, Postgres, Redis, Qdrant, Redpanda) using Helm:

```bash
helm install sfm ./helm \
  --set image.repository="somatechlat/somafractalmemory" \
  --set image.tag="2.0"
```

Important values:
- `env` – tweak URLs/feature flags for the API.
- `consumer.enabled` – disable if you only need the API surface.
- `postgres`, `redis`, `qdrant`, `redpanda` – control in-cluster backing services (toggle persistence or override images).
- `probe` – adjust `/healthz` readiness/liveness checks as needed.

Remove the release with `helm uninstall sfm` when the cluster tests are complete.

### Performance tuning
- `SOMA_RATE_LIMIT_MAX` defaults to **5000** requests per minute per endpoint; raise or lower it via `.env`/Helm.
- `UVICORN_WORKERS` (default **4**) and `UVICORN_TIMEOUT_GRACEFUL` (default **60**) control API concurrency; set them in `.env` before launching Docker/Helm.

## Full Workflow
1. **Create env file**: `cp .env.example .env` and edit if needed.
2. **Build images**: `docker compose build` (already done).
3. **Start stack**: `docker compose up -d`.
4. **Access API**: `http://localhost:9595`.
5. **Change mode**: Edit `.env` (e.g. update `MEMORY_MODE`), then rerun the stack commands so containers restart with the new values.
6. **Stop stack**: `docker compose down`.

### Tracing / OTLP exporter
The FastAPI example enables OpenTelemetry tracing. Provide a collector URL via `OTEL_EXPORTER_OTLP_ENDPOINT`, or disable traces in development by setting `OTEL_TRACES_EXPORTER=none` in `.env`.

## Cleaning Up
All persistent data is stored in Docker named volumes (`redis_data`, `qdrant_storage`, `postgres_data`, `redpanda_data`). They survive container restarts. To wipe all data, run:
```bash
docker compose down -v
```

---
*This document serves as the single source of truth for developers and operators.*
