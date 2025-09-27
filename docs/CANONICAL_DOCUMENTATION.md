# Canonical Documentation for SomaFractalMemory

This document is the operational source of truth for developers and operators. It consolidates the steps required to run the stack locally, configure services, and keep documentation builds up to date.

---

## 1. Prepare the Environment
1. Copy the shared environment file:
   ```bash
   cp .env.example .env
   ```
2. (Optional) Create a Python virtual environment and install the package in editable mode:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```
3. Adjust `.env` to match the target mode (`MEMORY_MODE`, ports, credentials). The file is consumed by every Docker service via `env_file: .env` in `docker-compose.yml`.

---

## 2. Build and Run the Stack
1. **Build images** after code changes:
   ```bash
   docker compose build
   ```
2. **Start everything** (Redis, Postgres, Qdrant, Redpanda, API, consumer, sandbox API):
   ```bash
   docker compose up -d
   ```
3. **Access endpoints**:
   * API: <http://localhost:9595>
   * Sandbox API (`test_api`): <http://localhost:8888>
   * Prometheus metrics: `/metrics`
   * Swagger UI: `/docs`
4. **Stop services** while preserving data:
   ```bash
   docker compose down
   ```
5. **Wipe volumes** when you need a clean slate:
   ```bash
   docker compose down -v
   ```

Named volumes created by the compose file: `redis_data`, `qdrant_storage`, `postgres_data`, `redpanda_data`.

---

## 3. Alternative Startup Modes (`scripts/start_stack.sh`)
`start_stack.sh` is a convenience wrapper around `docker-compose.dev.yml`:

| Mode | Services | Notes |
|------|----------|-------|
| `development` | Postgres + Qdrant (optionally Redpanda/Apicurio with `--with-broker`) | Fast to start for local work. |
| `evented_enterprise` / `cloud_managed` | Redpanda, Apicurio, Postgres, Qdrant | Mirrors the evented production setup. |
| `test` | No external services | Unit tests rely on in-memory stores. |

Example usage:
```bash
./scripts/start_stack.sh development --with-broker
```
Follow up with `docker compose up -d api consumer` to launch the application containers against those services.

---

## 4. Configuration Checklist
Key environment variables (see `docs/CONFIGURATION.md` for the full list):
- `MEMORY_MODE` – selects backend wiring.
- `POSTGRES_URL` – DSN for canonical storage.
- `QDRANT_HOST` / `QDRANT_PORT` (or `qdrant.path` in config) – vector store.
- `KAFKA_BOOTSTRAP_SERVERS` – broker location for event publishing.
- `EVENTING_ENABLED` – toggle Kafka emission for local-only development.
- `SOMA_RATE_LIMIT_MAX` – throttle for API endpoints.

When running the CLI or FastAPI in-process, you can pass a dictionary to `create_memory_system` to override the same settings:
```python
create_memory_system(
    MemoryMode.EVENTED_ENTERPRISE,
    "namespace",
    config={
        "redis": {"host": "redis", "port": 6379},
        "postgres": {"url": os.environ["POSTGRES_URL"]},
        "qdrant": {"host": "qdrant", "port": 6333},
        "eventing": {"enabled": True},
    },
)
> Important: ensure `UVICORN_PORT=9595` is set in your `.env` (or override the
> Helm chart value `env.UVICORN_PORT`) so that the API always binds to the
> canonical port used by examples and CI.
```

---

## 5. Testing & Validation
- **Unit tests** – `pytest -q` (no services required).
- **Hybrid store integration** – `pytest -q tests/test_postgres_redis_hybrid_store.py` spins up containers via Testcontainers.
- **Static checks** – `ruff check .`, `black --check .`, `bandit`, and `mypy` mirror the GitHub Actions pipeline.
- **Documentation build** – `mkdocs build` (requires `mkdocs` and `mkdocs-material`).

The FastAPI example regenerates `openapi.json` in the repository root during startup; keep that file committed so docs and CI stay in sync.

---

## 6. Kubernetes Deployment
The Helm chart at `helm/` provisions the full topology (API, consumer, Postgres, Redis, Qdrant, Redpanda). Key values:
- `image.repository` / `image.tag` – override container images.
- `env.*` – configure the API service (mirrors `.env`).
- `consumer.enabled` – toggle the background worker deployment.
- `postgres`, `redis`, `qdrant`, `redpanda` – enable/disable embedded dependencies or point to managed services.

Install and remove as follows:
```bash
helm install sfm ./helm
helm uninstall sfm
```

---

## 7. Clean-Up Matrix
| Goal | Command |
|------|---------|
| Stop containers, keep data | `docker compose down` |
| Stop + delete data volumes | `docker compose down -v` |
| Remove local Qdrant file | `rm -rf qdrant.db` |
| Reset `.env` | Re-copy from `.env.example` |

---

*For detailed configuration keys see `docs/CONFIGURATION.md`. For API surface documentation refer to `docs/api.md`.*

## Production readiness

For a prescriptive production readiness and deployment checklist, see
`docs/PRODUCTION_READINESS.md` which contains build, Helm deployment, schema
compatibility notes, testing guidance and operational best-practices.
