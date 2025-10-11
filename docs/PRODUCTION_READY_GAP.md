# Production Readiness Gap Report

This document captures the current gaps between the repository’s state and a production‑ready deployment, with concrete remediation actions, locations to change, and acceptance criteria. It complements `docs/PRODUCTION_READINESS.md` (checklist) and references Make-based canonical entrypoints.

Updated: 2025‑10‑10

---

## Summary table

| Area | Current state (where) | Gap/Risk | Impact | Severity | Actions to close (what/where) |
|---|---|---|---|---|---|
| API auth & security | Optional bearer token; not enforced broadly (somafractalmemory/http_api.py; docs) | Weak auth; no roles/tenants; CORS not formalized | Data exposure/misuse | High | Enforce auth on write/admin routes; explicit 401/403 paths; configure CORS. Add tests under `tests/`. |
| TLS (edge and backends) | No Ingress/TLS in Helm; DSNs lack sslmode/tls | Insecure transport to API/Postgres/Qdrant/Kafka | Interception risk | High | Add `helm/templates/ingress.yaml` with TLS; enable in `values-production.yaml`. Add TLS/SASL envs for backends via Secrets. |
| Secrets management | DSNs/tokens in env and values files | Plaintext secrets; no rotation | Compliance | High | Move to Kubernetes Secrets; adopt SOPS/SealedSecrets or cloud KMS; document rotation. |
| Persistence & backups | PVCs disabled by default; Compose volumes; no backups | Data loss on restart; no restore plan | Durability | High | Enable PVCs in prod values; add backup/restore Jobs and runbooks (Postgres pg_dump/restore; Qdrant snapshot). |
| DB schema/migrations | Direct psycopg2, no migrations framework | Drift across envs | Integrity | High | Introduce Alembic with versioned DDL; CI gate to ensure head. |
| Kafka resilience | Single broker; no DLQ/Schema Registry | Message loss, schema breakage | Reliability | High | Use managed Kafka or 3‑broker; add DLQ topic + consumer; (optional) Schema Registry; lag dashboards/alerts. |
| Network policies | None in Helm | Lateral movement possible | Security | High | Add NetworkPolicy (deny‐all then allowlist for API/consumers↔backends). |
| Pod security | securityContext not enforced | Privilege escalation | Security | Med | Set runAsNonRoot, readOnlyRootFilesystem, drop caps in all Deployments. |
| Autoscaling | Probes exist; no HPA | No auto‑scale | Availability | Med | Add HPA for API and consumer; validate probe timings. |
| Observability | Metrics exported; no scrape/alerts | Limited dashboards/alerts | MTTR | Med | Add ServiceMonitor/annotations; Grafana dashboards; alert rules (p95, 5xx, lag). |
| Rate limiting/WAF | Env knobs; no edge/WAF | Abuse risk | Security | Med | Default rate limits; put behind Ingress/WAF; IP allowlists as needed. |
| CI quality gates | Security scans non‑blocking; heavy tests skipped | Issues may slip | Governance | Med | Split PR vs nightly: nightly blocks on HIGH/CRITICAL and runs Kind+Helm e2e. |
| Config governance | Multiple sources (env + optional settings) | Drift/confusion | Operability | Med | Log startup config (redacted); validate env via pydantic‑settings; central schema doc. |
| Retention/PII | No standard retention policy | Unbounded growth, privacy | Med | TTL/archival and deletion workflows; redact sensitive logs. |
| Capacity planning | Benchmarks present; no capacity plan | Unknown headroom | Low | Baseline under expected QPS; tune resources; add load tests (nightly). |
| gRPC service | Async gRPC noted; not wired in Helm | Divergence or dead code | Low | Either wire a Deployment/Service in Helm or scope out for prod. |

---

## Remediation plan (what and where)

1) Security and access
- Add Ingress with TLS termination (new `helm/templates/ingress.yaml`); enable via `helm/values-production.yaml`.
- Enforce bearer auth on write/admin endpoints; add CORS policy (edit `somafractalmemory/http_api.py`).
- Replace plaintext envs with Kubernetes Secrets (new `helm/templates/secret.yaml`, ref via `envFrom` or `secretKeyRef`).

Acceptance: All write/admin routes require Authorization; TLS enabled at edge; no secrets in plaintext manifests; unauthorized tests fail as expected.

2) Data durability
- Enable PVCs with appropriate sizes and storageClass (edit `helm/values-production.yaml` and component blocks).
- Add backup/restore Jobs and runbooks for Postgres and Qdrant; document schedules and restore validation.

Acceptance: PVCs Bound; manual backup/restore walkthrough succeeds; persistence across restarts verified.

3) Reliability and scale
- Kafka: adopt managed or 3‑broker stateful set; add DLQ topic and consumer; (optional) Schema Registry; create lag dashboards + alerts.
- Introduce Alembic migrations; add CI step to assert migration head.
- Add HPA for API and consumer; adjust probes; set connection pool sizes via env.
- Add NetworkPolicy and PodSecurityContext to all pods.

Acceptance: API and consumers autoscale; network restricted; migrations applied cleanly in all envs; DLQ drains.

4) Observability and operations
- Add Prometheus scrape (ServiceMonitor or annotations) and Grafana dashboards (API latency, 5xx rate, consumer lag, DB connections).
- Add alerting rules; centralize structured logging; print redacted startup config summary.

Acceptance: Dashboards render data; alerts fire on threshold breach; logs show config summary with secrets redacted.

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
