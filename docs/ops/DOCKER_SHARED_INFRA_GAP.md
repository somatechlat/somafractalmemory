# Docker Shared Infra — Gap Assessment and Sprint Plan

Updated: 2025-10-11

This document identifies the gaps between the SomaStack Shared Infra Playbook (Docker section) and this repository’s existing Docker-based local/shared infra, and proposes a staged sprint plan to close them without adding clutter or duplicate workflows.

Goals
- Single source of truth for local Docker workflows (no duplicated compose topologies).
- Deterministic developer experience: one-liners to reset and bring up the stack.
- Clear parity boundaries between Docker (local) and Kubernetes (shared infra).
- Minimal maintenance overhead; reuse existing scripts where possible.

Scope considered
- Compose definitions: `docker-compose.yml`, `docker-compose.test.yml`, `docker-compose.dev.yml`.
- Scripts: `scripts/start_stack.sh`, `scripts/run_consumers.py`, `scripts/run_server.sh`, `scripts/start_all.sh`.
- Documentation: docs pointing to Docker vs. Kubernetes workflows.

Current state (observed)
- Compose files:
  - `docker-compose.yml` defines Redis, Qdrant, Postgres, Kafka (Confluent KRaft), API, and a consumer profile; host ports: Redis 6381, Qdrant 6333, Postgres 5433, Kafka 19092, API 9595.
  - `docker-compose.test.yml` defines a similar stack for testing with different DB names/namespaces and ports (API on 9999), plus Bitnami Kafka.
  - `docker-compose.dev.yml` only contains volume mounts for dev containers (appears to be an override layer; services reference the project tree).
- Scripted entrypoint:
  - `scripts/start_stack.sh` orchestrates minimal vs full stack and supports a legacy `--with-broker` flag; prefers Kafka if present.
- Tests and code paths assume “no mocks” and real backends. Live infra toggles (USE_LIVE_INFRA/USE_REAL_INFRA) are respected in tests.

Gaps and risks
1) Duplicate Kafka flavors across compose files
   - `docker-compose.yml` uses Confluent cp-kafka; `docker-compose.test.yml` uses Bitnami Kafka. Behavior and env var schemas differ.
   - Risk: inconsistent local behavior; harder on-boarding.

2) Fragmented compose usage
   - Presence of `docker-compose.dev.yml` with only volumes suggests a partial override that can confuse `start_stack.sh` detection.
   - Risk: unclear which compose file to use; drift between docs and scripts.

3) Unpinned images for Qdrant/Redis/Postgres in dev compose
   - `latest` used for Qdrant; Redis and Postgres versions differ between files.
   - Risk: non-deterministic upgrades break local workflows.

4) Missing one-command reset for Docker shared infra
   - Playbook references a `reset-sharedinfra-compose.sh`, but no such script exists in this repo.
   - Risk: stale volumes/config cause flakiness after upgrades; no standard reset.

5) Mixed env var contracts
   - API/consumer accept centralized settings fallbacks; compose uses a mixture of URL and host/port vars.
   - Risk: confusion over precedence; harder to troubleshoot.

6) Healthcheck inconsistencies
   - Healthchecks vary by service and sometimes reference `api` container from other services.
   - Risk: misleading container health; longer feedback loops.

7) Docs do not explicitly map compose services to the Shared Infra playbook
   - Lack of quick cross-reference table and parity notes (what Docker stack does vs what Kubernetes provides).

Acceptance criteria (when this gap is closed)
- A single, documented compose workflow for dev and test, with a simple reset script.
- Kafka flavor unified across compose files (choose Confluent cp-kafka or Bitnami and document rationale).
- All images pinned to specific tags with minimal, periodic updates.
- Healthchecks are local and container-scoped; API liveness/readiness stays under API.
- `scripts/start_stack.sh` reliably selects the right compose file and supports minimal/full stacks.
- Documentation clearly states parity boundaries and links to K8s shared infra for full prod-like behaviors.

Sprint plan

Sprint A — Compose hygiene and unification (1–2 days)
- Decide on a single Kafka flavor for compose (recommended: Confluent cp-kafka to match current `docker-compose.yml`).
- Update `docker-compose.test.yml` to use the same flavor and environment schema as `docker-compose.yml`.
- Pin images: `qdrant/qdrant:<known-good>`, `redis:7.2.x`, `postgres:15-alpine`, `confluentinc/cp-kafka:7.6.1`.
- Normalize healthchecks so each service checks itself (no cross-service `curl api` from consumer/test_api).
- Document ports and service names in README/QUICKSTART.

Sprint B — Reset and lifecycle scripts (1 day)
- Add `scripts/reset-sharedinfra-compose.sh` to stop, remove containers, and prune named volumes for Redis/Postgres/Kafka/Qdrant used by this repo.
- Ensure `scripts/start_stack.sh` leverages profiles or service lists for minimal vs full stacks and prints clear status.
- Add `make docker-reset` and `make docker-up[-full]` targets that wrap the scripts.

Sprint C — Env contract and settings parity (1 day)
- Align compose environment variables with centralized settings:
  - Prefer URLs where supported (POSTGRES_URL, QDRANT_URL); keep host/port for clarity but avoid conflicting values.
  - Add comments in compose files noting precedence (env overrides > centralized settings).
- Print a redacted startup config summary in API and consumer logs.

Sprint D — Documentation alignment (0.5–1 day)
- Add a short “Docker vs Kubernetes” parity matrix in `docs/DEVELOPER_ENVIRONMENT.md` (✅ documented in §4.4).
- Cross-link the Shared Infra Playbook; add a small section describing when to use Docker compose vs Kind+Helm.
- Provide troubleshooting tips specific to Docker (port collisions, orphaned volumes).

Optional Sprint E — Local CI smoke (0.5 day)
- Add a GitHub Action to run `docker compose up -d postgres qdrant kafka` and a minimal health smoke (API `/healthz`) to catch image drift.

Concrete edits proposed (non-breaking)
- Unify Kafka flavor in `docker-compose.test.yml` to Confluent cp-kafka with `KAFKA_*` env schema used in `docker-compose.yml`.
- Pin Qdrant: `qdrant/qdrant:v1.9.2` (or the version used in CI if present).
- Add `scripts/reset-sharedinfra-compose.sh` to remove containers and volumes:
  - Volumes: `postgres_data`, `redis_data`, `kafka_data`, `qdrant_storage` (and test equivalents).
- Adjust healthchecks in compose to be self-referential.
- Update `docs/QUICKSTART.md` and `docs/DEVELOPER_ENVIRONMENT.md` with a “Docker shared infra” section including:
  - Reset → Up → Verify commands
  - Port map and service names
  - Caveats vs Kubernetes shared infra

Next steps
- Approve sprint plan; implement Sprint A and B; verify with `pytest` against live compose stack; iterate on C and D.
