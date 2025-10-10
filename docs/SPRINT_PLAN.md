# Sprint Planning – Next Sprint Deltas

> Deprecated: This planning note is superseded by `docs/ARCHITECTURE_ROADMAP.md`. Please use that as the canonical source of truth.

## Goal
Deliver a **production‑ready** release of **SomaFractalMemory** by concentrating on three high‑impact pillars:
1. **Configuration Centralisation** – All service URLs, ports, and credentials flow through the shared `SMFSettings` model.
2. **gRPC Port Standardisation** – Unify every gRPC endpoint on the canonical port **50053**.
3. **Observability & Health** – Provide HTTP/gRPC health probes and full Prometheus metrics.

---

## 1️⃣ Configuration Centralisation
| # | Task | Owner | Acceptance Criteria |
|---|------|-------|--------------------|
| 1 | Refactor `somafractalmemory/http_api.py` to import every external service URL/port from `common.config.settings.SMFSettings` (Redis, Postgres, Qdrant, gRPC). | @dev | No hard‑coded URLs remain; the app starts with only the environment variables defined by `SMFSettings`.
| 2 | Update all `scripts/*.sh` entry‑points to source a generated `.env` file that mirrors `SMFSettings`. | @devops | `docker compose up` works out‑of‑the‑box without manual `-e` overrides.
| 3 | Add a dedicated test suite for `SMFSettings` validation (missing/invalid values raise `pydantic.ValidationError`). | @qa | The test suite fails when any required env var is omitted or malformed.

## 2️⃣ gRPC Port Standardisation (50053)
| # | Task | Owner | Acceptance Criteria |
|---|------|-------|--------------------|
| 1 | Search the entire codebase for any hard‑coded gRPC ports (`5005[0-9]`) and replace them with `settings.grpc_port` (default **50053**). | @dev | No literal `5005x` strings remain in production code.
| 2 | Add `grpc_port: int = 50053` to `SMFSettings` with a clear description in the docstring. | @dev | Clients can read the port from the same settings model.
| 3 | Update all documentation (`docs/ARCHITECTURE.md`, `docs/QUICKSTART.md`, OpenAPI spec) to display the new port. | @doc | Docs, OpenAPI, and README all show `50053`.

## 3️⃣ Observability & Health Checks
| # | Task | Owner | Acceptance Criteria |
|---|------|-------|--------------------|
| 1 | Add `/healthz` and `/readyz` endpoints to the FastAPI app returning **200 OK** when the service is healthy. | @dev | Kubernetes liveness/readiness probes succeed.
| 2 | Implement the standard gRPC health service (`grpc.health.v1.Health`) using `grpc-health-probe`. | @dev | `grpc-health-probe -addr=localhost:50053` returns `SERVING`.
| 3 | Export Prometheus metrics for both HTTP and gRPC via `prometheus_fastapi_instrumentator` and `grpcio-prometheus`. | @dev | `/metrics` endpoint is reachable and contains expected metric families.
| 4 | Extend the CI pipeline (`.github/workflows/ci.yml`) to run integration tests that hit the health endpoints and verify metric exposure. | @ci | CI fails if any health check or metric endpoint returns a non‑200 response.

---

## Timeline (2‑week sprint)
| Day | Focus |
|-----|-------|
| **Mon‑Tue** | Refactor configuration (SMFSettings) and update all scripts. |
| **Wed** | Standardise gRPC port across code, Dockerfiles, and compose files. |
| **Thu** | Implement health endpoints and gRPC health service. |
| **Fri** | Write/extend tests, update docs, run full CI suite. |
| **Mon (next week)** | Review PR, address feedback, merge to `main`. |

---

## Risks & Mitigations
* **Breaking existing deployments** – Guard the new config loading behind a feature flag (`USE_NEW_SETTINGS`) and validate in a staging environment before full rollout.
* **Port conflict in CI** – Allocate a random high‑range port for CI jobs and map it to `50053` inside the container; ensure no other service binds to that port.
* **Missing environment variables** – Provide a comprehensive `.env.example` and enforce CI secret injection; fail fast on missing vars.

---

## Owner Sign‑off
* **Configuration** – @dev
* **gRPC Port** – @dev
* **Observability** – @devops
* **Documentation** – @doc
* **QA** – @qa

---

*When every acceptance criterion is satisfied, we will tag the release as `vX.Y.Z` and push the updated Docker images to the registry.*
