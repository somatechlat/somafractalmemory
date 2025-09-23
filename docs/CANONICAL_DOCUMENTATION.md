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
5. Use the admin UI (`/admin`) or the `configure.sh` script to change configuration on‑the‑fly.
- ### Web UI (`/admin`)
- The FastAPI service exposes an admin endpoint at `http://localhost:9595/admin`. It presents a simple HTML form allowing you to edit the `.env` values (e.g., switch `MEMORY_MODE`). Submitting the form writes the new values to `.env` and restarts the `api` container automatically.

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

### CLI Helper (`configure.sh`)
A small Bash script `configure.sh` is provided to modify the `.env` from the command line and restart the API without affecting other services:

```bash
./configure.sh MEMORY_MODE=evented_enterprise
```
The script updates the variable in `.env` and runs:
`docker compose up -d --build api`

## Full Workflow
1. **Create env file**: `cp .env.example .env` and edit if needed.
2. **Build images**: `docker compose build` (already done).
3. **Start stack**: `docker compose up -d`.
4. **Access API**: `http://localhost:9595`.
5. **Change mode**: Use the admin UI or `configure.sh` to switch `MEMORY_MODE`.
6. **Stop stack**: `docker compose down`.

## Cleaning Up
All persistent data is stored in Docker named volumes (`redis_data`, `qdrant_storage`, `postgres_data`, `redpanda_data`). They survive container restarts. To wipe all data, run:
```bash
docker compose down -v
```

---
*This document serves as the single source of truth for developers and operators.*
