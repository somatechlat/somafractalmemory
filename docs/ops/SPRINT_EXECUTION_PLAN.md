# Enterprise Execution Plan

_Last updated: 2025-10-06_

## Definition of Done

The following acceptance gates apply to every work item merged into `master`:

1. **Code quality** – Ruff, Black, MyPy (no `ignore_errors` overrides on touched modules), and unit tests pass locally and in CI.
2. **Security & supply chain** – `bandit`, `pip-audit`, and container scans report no high/critical findings or documented mitigation.
3. **Observability** – New runtime behaviours emit structured logs and, when relevant, metrics/traces. Dashboards updated when signal shape changes.
4. **Docs & runbooks** – User-facing or operator-impacting changes update README, docs, or runbooks before merge.
5. **Rollback** – Deployment plan identifies rollback steps (Helm and Docker compose) and, when schema changes occur, outlines reversible migrations.

## Baseline Inventory (2025-10-06)

| Area | Current State | Notes |
| --- | --- | --- |
| Packaging | Dual layout (`somafractalmemory/` and `src/somafractalmemory/`), runtime Docker images copy repo twice | Requires consolidation in Sprint 1 |
| Runtime images | `Dockerfile` (dev) installs via `uv` with extra dependencies; `Dockerfile.runtime` excludes `workers/` and `scripts/` | Consumers fail unless bind-mounted |
| Configuration | `.env.example` and docs still reference Redpanda; secrets stored in plaintext env files | To be aligned in Sprint 2 |
| CI | Single job on Python 3.13-dev; sequential lint/test/docs | Needs matrix and caching in Sprint 3 |
| Observability | Prometheus metrics exposed; tracing via console exporter only | Enhanced in Sprint 4 |
| Persistence | Docker volumes defined but not documented; no backup automation | Addressed in Sprint 5 |

## Shared Dashboards & Telemetry

| Dashboard | Location | Owner |
| --- | --- | --- |
| Build health | GitHub Actions summary (`CI`, `pre-commit`) | Platform team |
| Runtime metrics | Prometheus scrape endpoint (API `:9595/metrics`, Consumer `:8001/metrics`) | SRE |
| Delivery tracking | Jira dashboard `SFM Enterprise Readiness` (to be created) | Product Ops |

## Sprint Cadence

- **Sprint length:** 2 weeks (Monday kickoff, Thursday demo, Friday retro)
- **Daily sync:** 15-minute stand-up per pod, plus tri-pod integrator sync at 12:00 UTC
- **Incremental releases:** Merge to `master` auto-deploys to staging; production promoted via approval after passing smoke tests

## Coordination Artifacts

1. **Interface contracts:** Shared Google Doc capturing env variable schema and API changes. Updated before implementing changes.
2. **Risk log:** Maintained in Jira; reviewed during Thursday demos.
3. **Telemetry board:** Grafana dashboard aggregating build, deploy, and runtime SLOs (initial stub linking to Prometheus endpoints).

---

This document seeds Sprint 0 deliverables. Changes to process, DoD, or telemetry should update this file alongside relevant tooling.
