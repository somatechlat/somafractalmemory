# Production Readiness Gap Report

This document captures the current gaps between the repository’s state and a production‑ready deployment, with concrete remediation actions, locations to change, and acceptance criteria. It complements `docs/PRODUCTION_READINESS.md` (checklist) and references Make-based canonical entrypoints.

Updated: 2025‑10‑12

---

## Summary table

| Area | Current state (where) | Gap/Risk | Impact | Severity | Actions to close (what/where) |
|---|---|---|---|---|---|
| API auth & security | Bearer token enforced globally (somafractalmemory/http_api.py; docs refreshed) | Roles/tenants still missing; CORS allowlist manual | Data exposure/misuse if token leaked | Medium | Integrate role-aware auth, central secret rotation, and structured CORS policy. Extend tests for multi-tenant flows. |
| TLS (edge and backends) | Ingress TLS enforced; production values mount Postgres/Kafka/Qdrant certs + env (`tls.mounts`) | Issuance/rotation automation and validation flows outstanding | Interception risk | High | Wire cert-manager/ACM automation, document rotation playbook, and add CI validation (e.g., smoke tests hitting HTTPS backends). |
| Secrets management | Helm renders Secret or ExternalSecret; runbook updated with rotation + reloader guidance (`docs/ops/SECRET_MANAGEMENT.md`); Vault path standardized to `secret/data/shared-infra/soma-memory/<env>` | Runtime values still include dev defaults; AWS backup secret/service account not provisioned yet | Compliance | Medium | Flip to external secrets (`externalSecret.*`), disable inline secret, install Reloader (or GitOps equivalent), provision `soma-memory-backup-aws`, and capture rotation evidence in change tickets. |
| Persistence & backups | PVCs disabled by default in dev; production values enable premium-rwo; S3 backup CronJobs for Postgres/Qdrant added | Restore workflow untested; S3 bucket/retention ownership unclear | Durability | High | Wire PVCs to managed storage, configure bucket policies, run the CronJobs in staging, and document a full restore drill (Postgres pg_restore + Qdrant snapshot upload). |
| DB schema/migrations | Alembic baseline committed (`kv_store`, `memory_events`) | No automated cutover; CI gate missing | Integrity | Medium | Embed `make db-upgrade` in deployment flow, add CI check for `alembic current`, and document rollback steps. |
| Kafka resilience | Single broker; no DLQ/Schema Registry | Message loss, schema breakage | Reliability | High | Use managed Kafka or 3‑broker; add DLQ topic + consumer; (optional) Schema Registry; lag dashboards/alerts. |
| Network policies | Optional deny-by-default NetworkPolicy via values | Ingress/egress rules must be tailored per environment; RBAC audit outstanding | Security | Medium | Enable `networkPolicy.enabled`, restrict to required namespaces/IPs, and document RBAC posture. |
| Pod security | Default pod/container contexts enforce non-root + RuntimeDefault seccomp | Sidecars/stateful dependencies still run with upstream defaults; image digests unpinned | Security | Low | Keep non-root contexts, extend to stateful sets or forked charts, and pin signed images. |
| Autoscaling | HPAs templated for API & consumer (prod values enable them) | Metrics/thresholds require load-test tuning | Availability | Low | Run load tests, adjust HPA targets, and align CPU/memory requests with observed usage. |
| Observability | ServiceMonitor + scrape annotations available; `scripts/sharedinfra-health.sh` produces namespace snapshots; chart includes optional `PrometheusRule` | Prometheus alert tuning and longer-term SLO views pending | MTTR | Medium | Enable ServiceMonitor in each env, turn on `prometheusRule.enabled`, tune thresholds (p95, 5xx, consumer lag), capture query evidence, and attach health script outputs in sprint evidence (Grafana optional). |
| Rate limiting/WAF | Env knobs; no edge/WAF | Abuse risk | Security | Med | Default rate limits; put behind Ingress/WAF; IP allowlists as needed. |
| CI quality gates | Security scans non‑blocking; heavy tests skipped | Issues may slip | Governance | Med | Split PR vs nightly: nightly blocks on HIGH/CRITICAL and runs Kind+Helm e2e. |
| Config governance | Multiple sources (env + optional settings) | Drift/confusion | Operability | Med | Log startup config (redacted); validate env via pydantic‑settings; central schema doc. |
| Retention/PII | No standard retention policy | Unbounded growth, privacy | Med | TTL/archival and deletion workflows; redact sensitive logs. |
| Capacity planning | Benchmarks present; no capacity plan | Unknown headroom | Low | Baseline under expected QPS; tune resources; add load tests (nightly). |
| gRPC service | Async gRPC noted; not wired in Helm | Divergence or dead code | Low | Either wire a Deployment/Service in Helm or scope out for prod. |

---

## Remediation plan (what and where)

1) Security and access
- Automate Ingress TLS (cert-manager/ACM), keep production values pointing at managed TLS secrets, and add validation runbooks for backend TLS handshakes.
- Enforce bearer auth on write/admin endpoints; add CORS policy (edit `somafractalmemory/http_api.py`).
- Back secrets with Vault/ExternalSecret (chart now mounts Secret; wire it to rotation pipelines).

Acceptance: All write/admin routes require Authorization; TLS enabled at edge; no secrets in plaintext manifests; unauthorized tests fail as expected.

2) Data durability
- Enable PVCs with appropriate sizes and storageClass (edit `helm/values-production.yaml` and component blocks).
- Add backup/restore Jobs and runbooks for Postgres and Qdrant; document schedules and restore validation.

Acceptance: PVCs Bound; manual backup/restore walkthrough succeeds; persistence across restarts verified.

3) Reliability and scale
- Kafka: adopt managed or 3‑broker stateful set; add DLQ topic and consumer; (optional) Schema Registry; create lag dashboards + alerts.
- Enforce Alembic migrations via the committed baseline; add CI step to assert migration head and capture revision output during deploys.
- Tune HPAs for API and consumer (templates in chart); adjust probes; set connection pool sizes via env.
- Harden NetworkPolicy/PodSecurityContext coverage for stateful dependencies and shared services.

Acceptance: API and consumers autoscale with tuned thresholds; network restricted across workloads; migrations applied cleanly in all envs; DLQ drains.

4) Observability and operations
- Prometheus scrape wired via ServiceMonitor/annotations; focus on alert rules and Prometheus queries for key SLOs (Grafana optional).
- Add alerting rules; centralize structured logging; print redacted startup config summary.

Acceptance: Prometheus targets scrape successfully; alerts fire on threshold breach; logs show config summary with secrets redacted.

5) CI/CD governance
- Split pipelines: PR (lint/format/unit/docs) vs nightly (Kind+Helm e2e + blocking security scans).
- Publish SARIF for code scanning; attach artifacts (helm manifests, images digests) to releases.

Acceptance: PRs fast and deterministic; nightly fails on HIGH/CRITICAL vulns or e2e breakages; badges reflect status.

6) Data management and privacy
- Define data retention/TTL policies; implement archival/deletion; redact sensitive fields in logs.

Acceptance: Retention policy documented; deletes honored end‑to‑end; log scrubs validated with tests.

7) Documentation and runbooks
- Provide a production values example (`helm/values-production.yaml`) with TLS/Secrets/NetworkPolicy/HPAs.
- Add incident runbooks: DB failover, broker outage, Qdrant rebuild, high latency triage.

Acceptance: On‑call can deploy prod with the example values and resolve common incidents following the runbooks.

---

## File change map (where to touch)

- Helm: `helm/templates/ingress.yaml` (new), `helm/templates/*` for NetworkPolicies, Secrets, pod security; `helm/values*.yaml` for prod toggles and sizes.
- API: `somafractalmemory/http_api.py` for auth enforcement, CORS, startup config logging.
- Secrets: `helm/templates/secret.yaml` (new) + values-to-secrets refactor.
- Migrations: new `alembic/` folder; dependencies in `pyproject.toml`; CI step in `.github/workflows/ci.yml`.
- Observability: ServiceMonitor (if Operator) or scrape annotations; dashboards stored under `ops/` or `docs/`.
- Kafka: `helm/templates/redpanda.yaml` (or switch to managed service); consumer DLQ logic in `workers/`.
- Docs: expand `docs/PRODUCTION_READINESS.md`, add runbooks under `docs/ops/`.

---

## References

- Canonical entrypoints: `make setup-dev`, `make setup-dev-k8s`, `make helm-dev-health`, `make settings`.
- Architecture: `docs/ARCHITECTURE.md`.
- Operational source of truth: `docs/CANONICAL_DOCUMENTATION.md`.
- Existing checklist: `docs/PRODUCTION_READINESS.md`.

---

## Module-by-module audit (classes, gaps, remediation)

This section inventories the major modules and classes and lists production checks, observed gaps, and concrete remediation actions. It focuses on correctness, resilience, security, and operability. Use this as an implementation guide alongside the summary table above.

### somafractalmemory/core.py
- Classes: `MemoryType`, `SomaFractalMemoryError`, `SomaFractalMemoryEnterprise`
- Purpose: Business logic for store/recall/graph/bulk, scoring path, decay.
- Production checks:
	- Thread/process safety; bounded memory growth; deterministic embeddings; idempotency of store; transactional boundaries for bulk.
	- Clear error taxonomy mapped to API/gRPC status; structured logs, metrics for hot paths.
- Gaps:
	- Idempotency strategy for `store_memory` and `store_bulk` not formalized (duplicate coords or retry semantics).
	- No explicit backpressure/circuit breaking when backends slow down.
	- Decay thread lifecycle (startup/shutdown) and observability not documented.
- Remediation:
	- Add idempotency keys and upsert semantics; document conflict policy. Emit metrics for queue times and operation durations.
	- Add graceful shutdown hooks; expose decay metrics and control toggles.

### somafractalmemory/factory.py
- Classes: `PostgresRedisHybridStore` (duplicate name also in implementations), `MemoryMode`, factory function(s).
- Purpose: Bind interfaces to concrete stores based on mode; compose hybrid KV.
- Gaps:
	- Class name duplication with `implementations/storage.py` risks drift.
	- Missing validation of config/env; lack of TLS/SSL defaults for DSNs; pool sizes/timeouts not enforced.
- Remediation:
	- Remove duplicate class; centralize hybrid KV in implementations. Validate config via pydantic settings; enforce sslmode and reasonable defaults.

### somafractalmemory/implementations/storage.py
- Classes: `InMemoryVectorStore`, `InMemoryKeyValueStore`, `RedisKeyValueStore`, `PostgresRedisHybridStore`, `QdrantVectorStore`, `PostgresKeyValueStore`.
- Purpose: Concrete storage clients for KV and vectors.
- Checks & gaps:
	- Redis: Add explicit timeouts, retries with backoff, and pipeline usage for bulk ops; document key schema and TTL where applicable.
	- Postgres: Alembic baseline in place; still ensure prepared statements, statement timeouts, connection pool sizing, and autocommit/transaction boundaries are explicit. Reconnect logic exists—verify thread safety and cursor lifecycle. Add read-only health checks that don’t allocate connections under pressure.
	- Qdrant: Ensure collection existence/idempotent schema creation; vector dimension checks; timeouts and retries; handle backpressure when index operations lag; expose index status metrics.
	- Hybrid store: Clarify cache consistency and eviction (write-through vs write-behind); document retry order and fallback when one backend is down.
- Remediation:
	- Enforce Alembic migrations (CI head check, deploy hook); set `statement_timeout` and pool sizes via env. Add retry/backoff wrappers; export metrics per backend op. Add collection bootstrap and schema validation for Qdrant.

### somafractalmemory/implementations/async_storage.py
- Classes: `AsyncRedisKeyValueStore`, `AsyncPostgresKeyValueStore`.
- Gaps:
	- Feature parity with sync stores; explicit timeouts and cancellation; resource cleanup on shutdown.
- Remediation:
	- Align options with sync stores; add async connection pooling, deadlines, and graceful shutdown hooks.

### somafractalmemory/interfaces/*.py
- Classes: `IKeyValueStore`, `IVectorStore`, `IGraphStore`.
- Gaps:
	- Contracts lack detailed error semantics and performance expectations; missing docstrings and type hints for edge cases.
- Remediation:
	- Document required behaviors (idempotency, error mapping, timeouts) and expected complexity. Add strict typing and raise specific errors.

### somafractalmemory/implementations/graph.py and graph_neo4j.py
- Classes: `NetworkXGraphStore`, `Neo4jGraphStore`.
- Gaps:
	- Persistence and consistency model not documented; potential memory growth for NetworkX; Neo4j connection security and transactions unspecified.
- Remediation:
	- Clarify persistence expectations; add limits for in-memory graphs or require external store in production; configure Neo4j TLS/auth and transaction boundaries.

### somafractalmemory/eventing/producer.py
- Purpose: Build and publish Kafka events; schema validate.
- Gaps:
	- Delivery semantics (acks, retries, idempotent producer) not enforced; partitioning/keys undefined; error handling lacks DLQ fallback.
- Remediation:
	- Configure acks=all, idempotent producer; choose partition keys; add retry/backoff and DLQ publisher on failure; include trace/context headers.

### workers/vector_indexer.py
- Purpose: Consume events and index vectors.
- Gaps:
	- No poison‑pill handling; backoff strategy unspecified; batch sizing and commit strategy not documented; missing DLQ.
- Remediation:
	- Implement batch processing with max batch/time window, exponential backoff, DLQ on repeated failures, and explicit commit after successful batches; export consumer lag metrics.

### somafractalmemory/http_api.py
- Pydantic models for requests/responses; route handlers; health/stats.
- Gaps:
	- Auth not enforced for mutating/admin endpoints; CORS policy missing; pagination/limits inconsistent; request body size limits unspecified; rate limiting not enforced server‑side; error mapping to consistent HTTP codes.
- Remediation:
	- Add dependency to enforce bearer auth; configure CORS; introduce pagination for list‑like endpoints; set `--limit-concurrency` or middleware for backpressure; define body size limit; add consistent error handlers; redact sensitive fields from logs; expose Prometheus labels for route/method/status.

### somafractalmemory/grpc_server.py and async_grpc_server.py
- Gaps:
	- TLS/mTLS not configured; deadlines/timeouts and auth interceptors absent; health/reflection services may be missing; backpressure/cancel propagation.
- Remediation:
	- Add TLS credentials; interceptors for auth/logging/tracing; implement `grpc.health.v1` health checks and reflection; require client deadlines.

### somafractalmemory/cli.py
- Gaps:
	- Exit codes and error messaging not standardized; no auth flags/secrets sourcing; lack of non‑interactive mode examples.
- Remediation:
	- Normalize exit codes; add `--token/--config` flags; redact sensitive output; improve help text with production examples.

### somafractalmemory/serialization.py
- Gaps:
	- Schema drift risk; lack of versioned payload schema and numeric precision policy.
- Remediation:
	- Introduce version fields; document canonical JSON encoding (e.g., separators, float precision); add tests for compatibility.

### common/config/settings.py and common/utils/*
- Classes: `SMFSettings`, `InfraEndpoints`, etc.
- Gaps:
	- Validate env at startup; secrets handling; precedence rules need to be surfaced in logs; feature flag clients (etcd) need timeouts/TLS.
- Remediation:
	- Use pydantic‑settings validation with strict types; emit redacted startup config; configure clients with TLS/timeouts.

### Providers and embeddings
- `implementations/providers.py`: `TransformersEmbeddingProvider`.
- Gaps:
	- Model pinning, caching, and offline operation; timeout control; resource limits.
- Remediation:
	- Pin model versions; allow offline deterministic hashes; set timeouts; cache artifacts; document CPU/GPU options.

### Tests
- Observation:
	- Good coverage across factory/core and several integration paths; heaviest tests are skipped in PR CI and should run nightly.
- Gaps:
	- Missing tests for auth enforcement, TLS configs, migrations head check, DLQ behavior, and HPA integration metrics.
- Remediation:
	- Add targeted tests per new features above; create an end‑to‑end nightly workflow exercising Kind+Helm with NodePort 30797 and validating `/healthz`, `/stats`, and consumer lag.

---

## Acceptance criteria checklist by module

- API (http_api.py): All mutating routes require bearer token; CORS configured; rate limiting active; 100% of routes return consistent error schema; p95 latency dashboard populated.
- Storage (implementations/storage.py): Statement timeouts and pool sizes enforced; retries/backoff present; Qdrant collections bootstrapped; migrations applied at boot or gated by CI.
- Eventing (producer/workers): Producer configured with acks=all/idempotent; DLQ in place; consumer reports lag; retries bounded with backoff.
- Helm: Ingress with TLS; PVCs enabled with sizes; NetworkPolicy deny‑all + allowlist; PodSecurityContext non‑root; HPA for API/consumer.
- CI: PR pipeline remains green and fast; nightly fails on HIGH/CRITICAL vulnerabilities and e2e failures.
