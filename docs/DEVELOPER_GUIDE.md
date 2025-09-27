# SomaFractalMemory – Developer Guide

This guide is aimed at contributors working directly with the codebase. It complements the canonical operations document with day-to-day workflows, pointers to key modules, and troubleshooting tips grounded in the current implementation.

---

## Table of Contents
- [Project Layout](#project-layout)
- [Bootstrapping a Dev Environment](#bootstrapping-a-dev-environment)
- [Running Services](#running-services)
- [CLI & API Usage](#cli--api-usage)
- [Testing & Static Analysis](#testing--static-analysis)
- [Cleaning Up](#cleaning-up)
- [Troubleshooting](#troubleshooting)

---

## Project Layout
| Path | Purpose |
|------|---------|
| `somafractalmemory/` | Core library (factory, enterprise class, interfaces, implementations, CLI). |
| `examples/api.py` | FastAPI example used for local runs and OpenAPI generation. |
| `eventing/` | Kafka event producer and schema definition. |
| `workers/` | Consumers that reconcile events into Postgres/Qdrant. |
| `scripts/` | Operational helpers (`start_stack.sh`, `run_consumers.py`, etc.). |
| `docs/` | MkDocs source files (kept in sync with the codebase). |
| `tests/` | Unit and integration tests. |

---

## Bootstrapping a Dev Environment
1. Clone the repository and set up a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```
2. Install developer dependencies when needed:
   ```bash
   pip install -r requirements.txt
   ```
3. Install pre-commit hooks (mirrors GitHub Actions):
   ```bash
   pre-commit install
   ```

---

## Running Services
SomaFractalMemory supports two main local workflows:

### Docker Compose (full stack)
```bash
cp .env.example .env
docker compose up -d  # starts Redis, Postgres, Qdrant, Redpanda, API, consumer, test API
```
The API lives at <http://localhost:9595>; Prometheus metrics are exposed at `/metrics`.

### Minimal backends via `start_stack.sh`
```bash
./scripts/start_stack.sh development            # Postgres + Qdrant only
./scripts/start_stack.sh development --with-broker  # + Redpanda + Apicurio
./scripts/start_stack.sh evented_enterprise     # Full evented stack
```
After bringing up the dependencies, launch the API (and optionally the consumer) using `docker compose up -d api consumer`.

---

## CLI & API Usage
### CLI (`soma`)
The CLI wraps `create_memory_system` and exposes commands for storing, recalling, and exporting memories. Example:
```bash
soma --mode development --namespace cli_demo store \
  --coord "1,2,3" \
  --payload '{"task": "triage", "importance": 3}'
```
Supply `--config-json` to point at a JSON file mirroring the `config` dictionary structure (`redis`, `postgres`, `qdrant`, `eventing`, `memory_enterprise`).

### FastAPI Example
Run the example app directly for rapid iteration:
```bash
uvicorn examples.api:app --reload
```
On startup it:
- Creates a development-mode memory system (`redis.testing=True`, Qdrant pointed at the configured host/port).
- Generates `openapi.json` in the repository root.
- Publishes Prometheus metrics and rate limits using environment defaults.

Important endpoints: `/store`, `/recall`, `/remember`, `/store_bulk`, `/link`, `/neighbors`, `/shortest_path`, `/stats`, `/metrics`, `/healthz`, `/readyz`.

---

## Testing & Static Analysis
| Command | What it does |
|---------|---------------|
| `pytest -q` | Runs the unit test suite using in-memory stores. |
| `pytest -q tests/test_postgres_redis_hybrid_store.py` | Exercises the hybrid backend with Testcontainers (requires Docker). |
| `ruff check .` | Linting (mirrors CI). |
| `black --check .` | Formatting check. |
| `bandit -q -r somafractalmemory` | Security scan of the library. |
| `mypy somafractalmemory` | Static type checking. |
| `mkdocs build` | Validates that documentation builds successfully. |

All of the above run automatically in GitHub Actions (`.github/workflows/ci.yml`).

---

## Cleaning Up
- Stop containers and keep data: `docker compose down`
- Stop and purge data volumes: `docker compose down -v`
- Remove the local Qdrant database used by tests or quickstarts: `rm -rf qdrant.db`
- Reset the environment file: re-copy `.env.example`

---

## Troubleshooting
**Postgres port conflicts** – The compose files expose Postgres on `5433`; ensure `.env` references that port when connecting from the host.

**Redis connection errors during development** – If you only need in-memory mode, set `REDIS_HOST=localhost` and `redis.testing=true` in your config to force `fakeredis`.

**Kafka not required** – Set `EVENTING_ENABLED=false` and avoid running the consumer if you only care about synchronous store/recall APIs.

**OpenTelemetry warnings** – When the collector endpoint is absent, set `OTEL_TRACES_EXPORTER=none` to silence connection errors.

---

*Refer back to `docs/CANONICAL_DOCUMENTATION.md` for deployment-focused instructions and `docs/api.md` for method-level details.*
