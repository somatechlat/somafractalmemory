# Canonical Roadmap – No‑Fallback, Full‑Infra on Every Startup

> **STATUS: COMPLETE** (Updated 2025-12-16)
>
> This roadmap has been fully implemented. Key changes:
> - Qdrant removed → Milvus is the ONLY vector backend
> - InMemory fallbacks removed → fail-fast on missing infrastructure
> - PostgreSQL is the canonical KV store
> - Redis is cache-only (no fallback to Redis for KV)
> - Health checks cover all backends (KV, Vector, Graph)

**Goal**: From now on, never use a local mock or fallback. On every startup—regardless of mode—the whole stack (PostgreSQL KV, Milvus vector, Redis cache, Prometheus metrics, OpenTelemetry tracing, Alembic migrations, health‑checks) must be started and the service must **fail fast** if any required component is unavailable.

---

## 1️⃣ Startup & Bootstrap Layer
| ✅ Existing | ❌ Missing | 🛠️ Action |
|---|---|---|
| `docker-compose.yml` defines services `postgres`, `qdrant`, `redis`, `api`. | No **bootstrap script** that guarantees migrations, collection creation, and health‑checks **before** the FastAPI server starts. | **Create** `scripts/bootstrap.sh` (executable) and set `CMD ["/bootstrap.sh"]` in the `Dockerfile`. The script must:
- Run `alembic upgrade head` (fail fast on error).
- Poll PostgreSQL, Qdrant, Redis with exponential back‑off until reachable.
- Call a new helper `ensure_qdrant_collection()` (see Vector Store section).
- Export `POSTGRES_DSN`, `QDRANT_URL`, `REDIS_URL` into env vars for the app.
- Only then exec `uvicorn somafractalmemory.http_api:app …`.
|
| `somafractalmemory/core.py` loads settings once (`_settings = load_settings()`). | Settings are **read** but never validated that required back‑ends are reachable. | **Add** `validate_infrastructure()` in `core.py` (called from `bootstrap.sh` via `python -c "from somafractalmemory.core import validate_infrastructure; validate_infrastructure()"`). It should:
- Attempt a lightweight `kv_store.health_check()`.
- Attempt `vector_store.health_check()`.
- Raise `RuntimeError` with clear message if any check fails.
|
| `common/config/settings.py` provides defaults and feature flags (e.g., `async_metrics_enabled`). | No explicit **required‑service flags** (e.g., `require_postgres = True`). | **Extend** the Pydantic Settings model with `require_postgres`, `require_qdrant`, `require_redis` (default `True`). All downstream code must read these flags and abort if false. |

## 2️⃣ Vector Store (Qdrant) Guarantees
| ✅ Existing | ❌ Missing | 🛠️ Action |
|---|---|---|
| `somafractalmemory.core` uses `self.vector_store.setup(...)` and `self.vector_store.search`. | No **collection existence** check; `vector_store` may auto‑create a collection on first upsert (fallback behavior). | **Add** `ensure_qdrant_collection()` in `somafractalmemory/utils/qdrant_helper.py` that:
- Calls Qdrant HTTP `GET /collections/{name}`.
- If 404, creates collection with size from settings (`vector_dim`).
- Raises on any non‑2xx response.
Invoke from bootstrap script **after** migrations.
|
| `http_api.delete_memory` already catches `VectorStoreError`. | No **metric** for vector‑store health. | **Add** `api_vector_store_up` gauge in `http_api.py` (incremented in health endpoint). |
| `memory_stats()` already queries Qdrant for collection stats but silently swallows errors. | Errors are ignored → could mask missing collection. | **Wrap** Qdrant calls in `try/except` that logs and re‑raises `VectorStoreError`. This propagates to the health check. |

## 3️⃣ KV Store (PostgreSQL) Guarantees
| ✅ Existing | ❌ Missing | 🛠️ Action |
|---|---|---|
| Alembic migration `20251012_0001_initial_schema.py` creates `memories` table (but **not applied**). | No automatic migration on container start. | Already covered by bootstrap script (`alembic upgrade head`). |
| `core.memory_stats()` attempts a Postgres query using `SQL` and `Identifier`. | The query uses the wrong wildcard (`%` vs `*`) causing zero rows. | **Fix** the pattern to `LIKE %:data` (already corrected in the latest code). Verify by running `docker exec somafractalmemory_postgres psql …` after migration. |
| `kv_store.health_check()` exists on the interface. | No explicit **connection test** before the API starts. | In `validate_infrastructure()` (see Startup) call `kv_store.health_check()` and raise if False. |
| `settings.force_hash_embeddings` can bypass the model, but **does not affect persistence**. | No setting to *force* PostgreSQL usage (currently code may fall back to in‑memory store). | **Update** `Factory.create_kv_store()` to raise `RuntimeError` if `settings.require_postgres` is `True` and the store is not a `PostgresKeyValueStore`. Remove any in‑memory fallback paths. |

## 4️⃣ Cache (Redis) – Keep as Cache Only
| ✅ Existing | ❌ Missing | 🛠️ Action |
|---|---|---|
| `common/utils/redis_cache.py` implements `RedisCache`. | Redis is currently used as a **fallback** for KV when Postgres is unavailable. | **Change** `Factory.create_cache()` to always return `RedisCache` **without** any fallback logic. Keep it as a pure cache (writes are best‑effort, failures logged but do **not** affect API success). |
| Health endpoint currently does not expose Redis status. | No metric for Redis health. | **Add** `api_redis_up` gauge in `http_api.py`. Set in `/healthz`. |

## 5️⃣ Observability – Prometheus & OpenTelemetry
| ✅ Existing | ❌ Missing | 🛠️ Action |
|---|---|---|
| Prometheus counters (`api_requests_total`, `api_responses_total`, `api_delete_success_total`) are defined in `http_api.py`. | No **startup‑phase** metrics for infra health. | **Add** gauges `api_postgres_up`, `api_qdrant_up`, `api_redis_up` (see Cache layer). Update the `/metrics` endpoint to expose them. |
| OpenTelemetry tracer is created in `core.py` (`tracer = trace.get_tracer("soma.core")`). | Tracer is not **initialized** with a proper exporter (e.g., OTLP). | **Create** `otel_setup.py` that configures an OTLP exporter (or stdout exporter for dev) and registers it **before** any spans are created. Import this module from `bootstrap.sh` via `python -c "import somafractalmemory.otel_setup"` or from `core.py` at module load. |
| No **trace** for the bootstrap process. | Missing observability for startup failures. | In `bootstrap.sh`, wrap each step (migration, health‑check, collection creation) with a **manual span** using the OTEL SDK (`with tracer.start_as_current_span("bootstrap.migration"):` etc.). |

## 6️⃣ Health‑Check Endpoint (`/healthz`)
| ✅ Existing | ❌ Missing | 🛠️ Action |
|---|---|---|
| `http_api.health_check()` returns a dict with `kv_store`, `vector_store`, `graph_store` health. | Does **not** include Redis, nor does it surface the new Prometheus gauges. | **Extend** the endpoint to:
- Call `kv_store.health_check()`, `vector_store.health_check()`, `graph_store.health_check()`, `redis_cache.health_check()`.
- Set the corresponding Prometheus gauges (`api_postgres_up`, etc.).
- Return HTTP 200 only if **all required** services are up; otherwise return 503 with a JSON payload indicating which component failed. |

## 7️⃣ Factory Refactor – Remove All Silent Fallbacks
| ✅ Existing | ❌ Missing | 🛠️ Action |
|---|---|---|
| `factory.py` currently builds stores based on environment variables and may fall back to in‑memory implementations. | Fallback logic is still present (`if not pg_store: return InMemoryStore`). | **Rewrite** `Factory` to be *strict*:
- `create_kv_store()` → raise if `settings.require_postgres` and Postgres connection fails.
- `create_vector_store()` → raise if `settings.require_qdrant` and Qdrant collection missing.
- `create_cache()` → always return `RedisCache` (no fallback).
After each `Factory.create_*` call, **assert** the instance type (e.g., `isinstance(kv_store, PostgresKeyValueStore)`). If not, raise `RuntimeError`. |

## 8️⃣ Testing – Ensure New Guarantees Are Covered
| ✅ Existing | ❌ Missing | 🛠️ Action |
|---|---|---|
| Unit tests cover core logic, but none verify that the application aborts when a required service is down. | No integration test for *fail‑fast* behavior. | **Add** `tests/test_startup_requirements.py` that:
- Starts Docker compose with a **missing** service (e.g., only `postgres`).
- Runs the bootstrap script and asserts it exits non‑zero.
- Runs the API and expects a 503 health response when Qdrant is unreachable.
|
| Live integration test (`test_live_integration.py`) already hits real services. | It still passes when the DB is missing because of fallback. | **Update** the test to assert that a missing `memories` table causes the request to fail with `500` and a clear error message. |
| Metrics tests exist for request counters. | No tests for new health gauges. | **Add** a test that calls `/healthz` with all services up and asserts that `api_postgres_up`, `api_qdrant_up`, `api_redis_up` are `1`. Then mock a failure (e.g., stop Qdrant) and assert gauge becomes `0` and endpoint returns `503`. |

## 9️⃣ Documentation – Keep the Team Aligned
| ✅ Existing | ❌ Missing | 🛠️ Action |
|---|---|---|
| `docs/technical-manual/` contains deployment instructions. | No clear statement about “no fallback” policy. | **Add** a new section `docs/technical-manual/no-fallback-policy.md` that explains:
- The strict startup sequence.
- How to debug a failed bootstrap (look at logs, trace spans).
- Which environment variables control required services.
|
| `README.md` lists quickstart steps. | Quickstart still suggests running `docker compose up` without the bootstrap. | **Update** the quickstart to instruct users to run `docker compose up -d && docker compose exec api /bootstrap.sh` (or simply rely on the container’s CMD). |
| `Makefile` has a `test` target. | No target for “full‑stack validation”. | **Add** `make validate-infra` that runs the bootstrap script with `--dry-run` (checks connectivity, migrations, collection creation) and exits with status 0 only if everything is ready. |

## 10️⃣ Continuous Integration / Deployment
| ✅ Existing | ❌ Missing | 🛠️ Action |
|---|---|---|
| GitHub Actions run `pytest`. | CI does **not** spin up the full Docker stack. | **Add** a CI job `integration-tests` that:
- Uses `docker compose -f docker-compose.yml up -d --build`.
- Runs `scripts/bootstrap.sh` (fails fast on any error).
- Executes the full test suite (`pytest -q`).
- Stops containers after the run.
|
| No linting on Dockerfiles. | Potential drift between `Dockerfile` and `bootstrap.sh`. | **Add** a lint step (`hadolint Dockerfile`) to CI. |
| No version bump on migration changes. | Alembic migrations could be out‑of‑sync. | **Enforce** that any change to `alembic/versions/*` increments the project version in `pyproject.toml` via a pre‑commit hook. |

---

## 📆 Timeline (Suggested Sprint)
| Sprint | Goal | Deliverables |
|-------|------|--------------|
| **Sprint 1** (1 wk) | **Bootstrap & Validation** | `scripts/bootstrap.sh`, `validate_infrastructure()`, updated `Dockerfile`, health‑check improvements, Prometheus gauges for services. |
| **Sprint 2** (1 wk) | **Vector & KV Guarantees** | `ensure_qdrant_collection()`, `Factory` strict mode, settings flags, updated `core` health checks, OTEL exporter config. |
| **Sprint 3** (1 wk) | **Observability & Metrics** | OTEL spans in bootstrap, new metrics (`api_postgres_up`, etc.), updated `/metrics` endpoint. |
| **Sprint 4** (1 wk) | **Testing & CI** | New integration tests for fail‑fast, CI workflow with full Docker stack, `make validate-infra`. |
| **Sprint 5** (0.5 wk) | **Docs & Release** | Documentation updates, README quickstart, version bump, final regression test run. |

---

## ✅ Acceptance Criteria
1. **Startup** – Running `docker compose up -d` brings up containers **and** the API container automatically executes `bootstrap.sh`. If any required service is unreachable, the container **exits** with a non‑zero status and logs a clear error. No fallback to in‑memory or Redis‑only storage occurs.
2. **Persistence** – After a successful start, creating a memory via the HTTP API stores the record in **PostgreSQL** (`memories` table) **and** in a Qdrant collection. Deleting a memory removes entries from both stores (verified by direct DB query and Qdrant API).
3. **Health Endpoint** – `GET /healthz` returns **200** only when PostgreSQL, Qdrant, and Redis are all reachable; otherwise returns **503** with a JSON payload indicating the failing component(s). Corresponding Prometheus gauges reflect the same state.
4. **Metrics** – Prometheus `/metrics` includes the new gauges (`api_postgres_up`, `api_qdrant_up`, `api_redis_up`) and existing request counters. All metrics are exported from the moment the API starts.
5. **Tracing** – OpenTelemetry trace contains spans for each bootstrap step (migration, health‑check, collection creation) and for all API requests, enabling end‑to‑end observability.
6. **Tests** – The CI pipeline runs unit tests, live integration tests, and the new *startup‑failure* tests. All pass with **100 %** coverage of the new bootstrap logic.
7. **Documentation** – The “No‑Fallback Policy” section clearly explains the strict startup behavior, how to debug failures, and how to configure required services.

---

### 🎯 Bottom Line
By following this roadmap you will:
- **Eliminate every silent fallback** (in‑memory KV, auto‑created Qdrant collections, etc.).
- **Guarantee data persistence** in PostgreSQL and Qdrant on every launch.
- **Provide immediate visibility** of infrastructure health via health endpoint, Prometheus, and OpenTelemetry.
- **Fail fast** when any required component is missing, preventing hidden data loss.
- **Maintain Vibe coding standards** (explicit errors, observability, deterministic behavior).
