# Architecture Alignment Roadmap for SomaFractalMemory

## Overview
This roadmap bridges the current **SomaFractalMemory** codebase with the **revised Soma stack architecture** described in the user's document. It identifies gaps, defines concrete work items, and groups them into 2‑week sprints. The goal is **100 % alignment** with the shared‑infra, gRPC‑first, async‑first, and observability standards.

---

## 1. Gap Analysis (Current vs Target)
| Area | Current State | Target State | Gap |
|------|---------------|--------------|-----|
| **Configuration** | Settings are scattered across `.env`, `common/config/settings.py` with service‑specific overrides. | Single source of truth via `SMFSettings` inheriting from `common/config/settings.py`; all env vars injected from ConfigMap/Secret (Vault). | Need to refactor `somafractalmemory/http_api.py` and other modules to use `SMFSettings`. Remove local `.env` usage.
| **gRPC Port** | gRPC services use ports 50051‑50052; SMF runs on FastAPI HTTP (9595). | SMF exposes **gRPC** on **50053** only; HTTP is optional for health/metrics. | Add gRPC server implementation, generate stubs from `proto/memory.proto`, update clients.
| **Async‑first** | Core modules (`core.py`, `factory.py`, `minimal_core.py`) contain blocking I/O (sync Redis, Postgres). | All I/O should be `async` (asyncpg, aioredis, aiohttp). | Convert blocking functions to `async def`, adjust call sites, update workers.
| **Health & Metrics** | `/healthz` and `/readyz` endpoints exist in FastAPI; metrics via custom exporter. | Unified health endpoints (`/healthz`, `/readyz`) and **Prometheus** metrics exported by shared OpenTelemetry utilities. | Consolidate health endpoints in `http_api.py`, replace custom metrics with `common/utils/trace.py` instrumentation.
| **Shared Infra Usage** | Services reference local Docker‑Compose hosts (e.g., `localhost:6381`). | DNS‑based service discovery (`redis.soma.svc.cluster.local`, etc.) via Helm chart. | Update connection strings to use env vars pointing to DNS names; remove hard‑coded ports.
| **Helm Chart** | No Helm chart for the stack; individual Docker‑Compose files only. | Single `soma‑infra` chart plus per‑service sub‑charts. | Create `infra/helm/charts/soma-infra/` and a sub‑chart for SMF.
| **CI/CD** | GitHub Actions run lint, unit tests, Docker build. | CI must spin up a Kind cluster, install the Helm chart, run integration tests, lint Helm, and publish images. | Extend `.github/workflows/ci.yml` with Helm steps and Kind cluster setup.
| **Observability** | OpenTelemetry tracing via `common/utils/trace.py`; Prometheus metrics custom. | Consistent labels (`service`, `instance`, `env`, `version`), Jaeger exporter, Loki logging, Alertmanager rules. | Ensure all services import the shared tracing config and emit required labels.
| **Feature Flags** | Hard‑coded feature toggles in code. | Centralised in Etcd with Redis cache; updates via Kafka `config.updates`. | Introduce `common/utils/etcd_client.py` and cache layer.

---

## 2. Milestones & Sprint Plan (2‑week sprints)
| Sprint | Focus Area | Key Deliverables |
|-------|------------|------------------|
| **Sprint 1** | **Configuration Centralisation & Vault Integration** | • Refactor `common/config/settings.py` to expose `SMFSettings` with all required fields.\n• Update `http_api.py`, workers, and scripts to read from `SMFSettings`.\n• Add `.env.example` and Helm `values.yaml` snippets for ConfigMap/Secret. |
| **Sprint 2** | **gRPC Definition & Stub Generation** | • Add `proto/memory.proto` (if missing) under `proto/`.\n• Generate Python stubs (`grpc_tools.protoc`).\n• Implement gRPC server in `somafractalmemory/grpc_server.py` listening on **50053**.\n• Migrate internal HTTP calls to gRPC client where applicable. |
| **Sprint 3** | **Async Refactor of Core Modules** | • Convert I/O‑heavy functions in `core.py`, `factory.py`, `minimal_core.py` to `async`.\n• Switch Redis client to `aioredis`, Postgres to `asyncpg`.\n• Update workers (`workers/kv_writer.py`, `workers/vector_indexer.py`) to use `asyncio.create_task`. |
| **Sprint 4** | **Health, Metrics, & Tracing Consolidation** | • Add `/healthz` and `/readyz` endpoints to FastAPI (or gRPC health service).\n• Replace custom metrics with `prometheus_fastapi_instrumentator` and shared OpenTelemetry exporter.\n• Ensure all logs go through `common/utils/logger.py` (JSON). |
| **Sprint 5** | **Helm Chart & Shared‑Infra Integration** | • Create `infra/helm/charts/soma-infra/` chart bundling Auth, OPA, Kafka, Redis, Prometheus/Grafana, Vault, Etcd.\n• Add SMF sub‑chart under `infra/helm/charts/soma-stack/` referencing shared DNS names.\n• Verify `helm upgrade --install` works in a Kind cluster. |
| **Sprint 6** | **CI/CD Extension & Integration Tests** | • Extend GitHub Actions workflow to spin up Kind, install Helm chart, run integration tests.\n• Add Helm lint step, cache gRPC stubs.\n• Publish Docker image with tag `{{ github.sha }}`. |
| **Sprint 7** | **Feature‑Flag & Cache Layer** | • Implement `common/utils/etcd_client.py` and `common/utils/redis_cache.py`.\n• Replace hard‑coded flags with Etcd look‑ups; add background watcher for `config.updates`. |
| **Sprint 8** | **Documentation & Run‑book** | • Update `docs/architecture.md` with new diagram and service count.\n• Add `docs/runbook_smf.md` covering deployment, health checks, rollback.\n• Generate Mermaid diagram (provided in user spec). |

---

## 3. Immediate Next Steps (Start Sprint 1)
1. **Create a new settings module** – `common/config/settings.py` will define `BaseSettings` and `SMFSettings` (inherit). Add fields for:
   - `redis_url`, `postgres_url`, `qdrant_url`, `kafka_bootstrap_servers`
   - `grpc_port: int = 50053`
   - `auth_service_url`, `opa_service_url`, `vault_addr`, `etcd_endpoint`
2. **Update imports** – replace direct env‑var reads in `somafractalmemory/http_api.py` and workers with `from common.config.settings import SMFSettings; settings = SMFSettings()`.
3. **Add placeholder Helm values** – create `infra/helm/values-dev.yaml` containing the DNS names (e.g., `redis.soma.svc.cluster.local:6379`).
4. **Commit the changes** – run lint (`ruff`), format (`black`), and ensure tests still pass.
5. **Create a roadmap file** – `docs/ARCHITECTURE_ROADMAP.md` (this file) and add to the repo.

---

## 4. How to Proceed
- **Ask for confirmation** to create the initial settings module and placeholder Helm values.
- Once approved, I will generate the files and open a PR.
- After the PR is merged, we can move to Sprint 2 (gRPC implementation).

Feel free to adjust sprint priorities or add/remove items. Let me know which artifacts you’d like me to create next (e.g., `common/config/settings.py`, Helm chart skeleton, proto file, etc.).
