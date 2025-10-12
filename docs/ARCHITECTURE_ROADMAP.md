# SomaStack Shared Infra Alignment Roadmap

## Overview
This roadmap keeps SomaFractalMemory aligned with the **SomaStack Shared Infra — Agent Deployment Playbook**. It translates the playbook into concrete engineering sprints, tracks current repository signals, and lists the validation evidence required to declare each sprint complete. The roadmap complements the memory-core plan in `docs/ROADMAP.md` and is the canonical source for SomaStack integration work.

Legend: `[TODO]`, `[ACTIVE]`, `[DONE]`, `[BLOCKED]`.

### Streams at a Glance
| Stream | Scope | Lead Artifacts | Current Signal |
|--------|-------|----------------|----------------|
| Shared Infra Integration | Automation, shared Helm chart, Vault/ExternalSecret wiring, CI/CD promotion, operational runbooks. | `docs/ARCHITECTURE_ROADMAP.md`, playbook (to be added) under `docs/ops/SOMASTACK_SHARED_INFRA_PLAYBOOK.md`, scripts under `scripts/`. | [TODO] `infra/` scaffolding missing; automation scripts not yet authored. |
| Memory Core Evolution | Scoring math, normalization, retention controls, performance gates. | `docs/ROADMAP.md`, code under `somafractalmemory/`. | [REVIEW] Core normalization paths exist, but acceptance tests and gating metrics need audit. |

---

## 1. Alignment Snapshot (repo vs playbook)
| Playbook Section | Current Implementation | Alignment Gap | Status |
|------------------|------------------------|---------------|--------|
| Cluster reset checklist | Manual commands documented; `scripts/reset-sharedinfra-compose.sh` covers Docker only. | Create SomaStack reset script mirroring Section 0 (Helm uninstall, namespace delete, wait, verification). | [TODO] |
| Environment bootstrap | Kind config & automation scripts newly added. | Capture run logs + ensure CI leverages scripts for provisioning. | [ACTIVE] |
| Docker shared infra reset | `scripts/reset-sharedinfra-compose.sh` added for compose cleanups. | Update docs, add Redis/Kafka recovery notes and parity warning. | [DONE] |
| Helm shared infra chart | Core dependencies configured in `infra/helm/soma-infra/`. | Add custom templates/policies and wire remaining services (OPA authz bundles, Grafana dashboards). | [ACTIVE] |
| Vault / ExternalSecret automation | No Vault wiring; runtime depends on env vars. | Introduce Vault policies, ExternalSecret templates, ConfigMap contract, and documentation. | [TODO] |
| App deployment pipeline | GitHub Actions covers tests only; no deploy job; readiness not enforced. | Implement pipeline from Section 4 (build/push image, Helm upgrade, readiness wait). | [TODO] |
| Verification & troubleshooting | Docs mention manual checks; no automated health snapshot or incident bundle. | Add scripts/snippets from Sections 5 and 8; ensure commands live in repo. | [TODO] |
| Operational policies | Policy statements scattered; restart resilience + drift detection absent. | Consolidate policies, add automation hooks, and document enforcement strategy in runbooks. | [TODO] |
| Production readiness gaps (`docs/PRODUCTION_READY_GAP.md`) | High-severity risks (TLS, secrets, auth, PVC/backups, migrations, Kafka HA, network policy) not assigned to sprints. | Fold remediation items into Sprint 2–4 deliverables with evidence requirements. | [ACTIVE] |

---

## 2. Sprint Roadmap (mapped to playbook)
| Sprint | Objective | Playbook Anchors | Primary Deliverables | Status | Notes / Blockers |
|--------|-----------|------------------|----------------------|--------|------------------|
| **Sprint 0 – Readiness Gap Fixes** | Align Docker compose workflow and docs with playbook prerequisites. | §§0, 1.4, 6, 10 | Rename compose reset script, add parity notes, Redis/Kafka recovery steps, onboarding links to playbook. | [ACTIVE] | Script exists but naming and doc updates pending. |
| **Sprint 1 – Kubernetes Baseline** | Reproduce shared infra on Kind with scripted health checks. | §§1.1–1.3, 2.1–2.4 | Kind config, image preload script, deployment helper, Makefile version gates. | [TODO] | Requires new `infra/` tree and CI-proof of readiness. |
| **Sprint 2 – Shared Infra Wiring** | Wire namespaces, Vault, ExternalSecrets, and ConfigMaps. | §§3.1–3.6 | Vault policy templates, ExternalSecret manifests, ConfigMap contract, DB/Kafka automation. | [TODO] | Depends on Sprint 1 Helm install outputs. |
| **Sprint 3 – Observability & CI** | Enforce logging/tracing standards and automate deployment pipeline. | §§3.4–3.5, 4, 5, 8 | Structured logging, tracing integration, GitHub Action deploy job, health snapshot script. | [TODO] | Requires Sprint 2 wiring for end-to-end tests. |
| **Sprint 4 – Go-Live Checklist** | Capture DR rehearsals, access audits, and finalize runbooks for production promotion. | §§5, 6, 7, 9, 11 | DR drill artefacts, namespace audit automation, incident bundle collector, production cutover checklist. | [TODO] | Dependent on earlier sprint artefacts and CI output. |

Store sprint artefacts under `docs/infra/sprints/<sprint-id>/` with command transcripts and validation logs.

---

## 3. Sprint Detail

- Evidence should be stored under `docs/infra/sprints/sprint-<n>/`.

### Sprint 0 – Readiness Gap Fixes `[ACTIVE]`
- [x] Rename `scripts/reset_docker_shared_infra.sh` → `scripts/reset-sharedinfra-compose.sh` and update references in `docs/DEVELOPER_ENVIRONMENT.md`, `README.md`, and `docs/QUICKSTART.md`.
- [x] Document Docker vs SomaStack parity (topology, persistence, feature gaps) in `docs/DEVELOPER_ENVIRONMENT.md` and annotate the gap doc.
- [x] Append Redis/Kafka recovery steps (volume wipe, log capture) to troubleshooting docs.
- [x] Link onboarding guides (`README.md`, `docs/USAGE_GUIDE.md`) directly to the SomaStack playbook and sprint artefact index.
- **Acceptance evidence**: executable script, updated docs, compose smoke-test output stored in `docs/infra/sprints/sprint-0/README.md`.

### Sprint 1 – Kubernetes Baseline `[ACTIVE]`
- [x] Add `infra/kind/soma-kind.yaml` defining control-plane resources.
- [x] Create `scripts/create-kind-soma.sh` that validates tool versions and provisions the cluster.
- [x] Implement `scripts/preload-sharedinfra-images.sh` with the image loop from playbook §1.3 (`docker pull` + `kind load`).
- [x] Author `scripts/deploy-kind-sharedinfra.sh` wrapping Helm install with `--wait` and readiness gate.
- [x] Extend `Makefile` with `sharedinfra-kind` target chaining reset → create cluster → preload → deploy; enforce minimum versions for `kubectl`, `helm`, `kind`, `docker`, `jq`.
- **Acceptance evidence (pending)**: command transcript showing clean install, `kubectl wait --for=condition=ready` success, `helm status sharedinfra -n soma-infra` snapshot added to sprint artefacts.

### Sprint 2 – Shared Infra Wiring `[TODO]`
- [x] Scaffold `infra/helm/soma-infra/` (Chart.yaml, dependencies, base `values.yaml`, overlays for dev/test/staging/prod-lite/prod).
- [x] Configure chart dependencies (Vault, OPA, Prometheus, Grafana) and baseline values for Postgres, Redis, Kafka, Vault.
- [ ] Add shared templates (ConfigMaps, NetworkPolicies) to customize upstream charts and enforce Soma defaults.
- [ ] Add Vault policy templates under `infra/vault/policies/` plus automation script to apply roles/policies.
- [ ] Provide ExternalSecret templates in `infra/external-secrets/` and document usage (including `ENV` export).
- [ ] Update application Helm chart to consume ConfigMap contract and runtime secret references from playbook §3.4–3.5.
- [ ] Move runtime credentials to Kubernetes Secrets/Vault (retire plaintext values) and document rotation path.
- [ ] Automate DB provisioning snippet (psql client) and Kafka topic creation under `scripts/`.
- [ ] Prepare TLS inputs for edge/backends (Ingress cert references, Postgres/Kafka SSL toggles) to unblock production deployment values.
- **Acceptance evidence**: rendered manifests referencing shared DNS, `kubectl describe externalsecret` output, and CLI logs saved in `docs/infra/sprints/sprint-2/`.

### Sprint 3 – Observability & CI `[TODO]`
- [ ] Replace ad hoc logging with `common/utils/logger.py` JSON logger across API, CLI, and worker entry points.
- [ ] Integrate tracing via `common/utils/trace.py` with settings toggles and document Jaeger configuration.
- [ ] Implement GitHub Actions workflow `deploy-<service>.yml` matching playbook §4 (image build/push, Helm upgrade, readiness wait).
- [ ] Add health snapshot script (`scripts/sharedinfra-health.sh`) aggregating `kubectl get pods`, `repmgr cluster show`, and Kafka offset checks.
- [ ] Ensure `make deploy-kind-full MODE=<mode>` target runs in CI and stores artefacts for inspection.
- [ ] Introduce NetworkPolicy, PodSecurityContext defaults, and initial HPA manifests sourced from production readiness gaps; validate via Kind tests.
- [ ] Enable TLS (Ingress + backend DSNs) and enforce bearer auth / rate limiting in the API chart to close high-severity security items.
- **Acceptance evidence**: CI run URL, structured log sample, Jaeger span capture, health script output archived in sprint artefacts.

### Sprint 4 – Go-Live Checklist `[TODO]`
- [ ] Capture DR rehearsal procedure and logs under `docs/infra/sprints/sprint-4/`.
- [ ] Implement namespace access audit (`scripts/audit-sharedinfra-access.sh`) verifying `soma.sh/allow-shared-infra="true"`.
- [ ] Finalize incident bundle collector script from playbook §8 and document usage.
- [ ] Publish production cutover checklist referencing restart resilience, drift detection, and rollback steps.
- [ ] Confirm observability dashboards and alert rules packaged with the Helm chart.
- [ ] Close remaining production readiness gaps: PVC enablement + backup/restore jobs, Alembic migrations gate, Kafka DLQ + lag monitoring, secrets rotation guidance.
- **Acceptance evidence**: completed cutover checklist, audit logs, dashboard exports, and incident bundle sample stored in sprint artefacts.

---

## 4. Production Readiness Mapping
| Gap (see `docs/PRODUCTION_READY_GAP.md`) | Severity | Assigned Sprint | Planned Remediation | Evidence |
|------------------------------------------|----------|-----------------|---------------------|----------|
| Enforce auth, CORS, rate limits on API | High | Sprint 3 | Update `somafractalmemory/http_api.py`, wire bearer auth + CORS defaults, expose rate-limit configs in Helm. | Authz tests + Helm values diff; CI logs. |
| TLS for Ingress and backend DSNs | High | Sprint 2 (prep), Sprint 3 (enable) | Add TLS secrets/Ingress templates, set `sslmode`/SASL flags for Postgres/Kafka/Redis, document cert management. | Kind deploy with TLS-enabled values; manual curl/grpcurl over TLS. |
| Secrets management via Vault/K8s Secrets | High | Sprint 2 | ExternalSecrets templates, secretRef usage, rotation doc. | `kubectl describe secret` redaction, Vault policy records. |
| Persistence + backups | High | Sprint 4 | Enable PVCs by default; add backup/restore CronJobs + runbook. | PVC status screenshots/logs; backup artifact check. |
| Alembic migrations + DB schema guard | High | Sprint 4 | Introduce Alembic migrations; CI check for head. | Migration repo; CI job output. |
| Kafka HA, DLQ, monitoring | High | Sprint 4 | Extend Helm to support multi-broker + DLQ consumer; add lag dashboards/alerts. | Helm values diff; Grafana screenshot; DLQ test log. |
| NetworkPolicy & Pod security | High | Sprint 3 | Deny-by-default policies; runAsNonRoot, drop capabilities. | Manifest review; `kubectl get networkpolicy`; conformance test. |
| Secrets rotation / compliance documentation | High | Sprint 4 | Publish rotation procedures and compliance statements in runbook. | Doc excerpt; rotation rehearsal log. |

Track progress by marking each row with `[TODO]/[ACTIVE]/[DONE]` as remediation advances. Update `docs/PRODUCTION_READY_GAP.md` when evidence is captured to keep the gap report synchronized.

---

## 4. Memory Core Roadmap Sync
| SFM Core Sprint | Focus | Current Signal (repo) | Status |
|-----------------|-------|-----------------------|--------|
| Sprint 1 – Score pipeline foundation | Normalize vectors, enforce real cosine similarity, initialize importance normalization. | `somafractalmemory/core.py` normalizes embeddings on insert; tests for logistic importance and non-negative clamp absent in `tests/`. | [REVIEW] |
| Sprint 2 – Contiguous slabs & benchmarks | Move to contiguous slabs and capture latency benchmarks. | Storage layer still abstract (`implementations/storage.py`); microbenchmarks not present. | [TODO] |
| Sprint 3 – Decay parameter | Introduce τ half-life and correctness tests. | Decay constants referenced but not wired; regression tests missing. | [TODO] |
| Sprint 4 – Retention score | Implement retention scoring when Gate G1 triggers. | No retention pipeline implemented; gating metrics not captured. | [TODO] |
| Sprint 5 – Hot tier + eviction | Add hot tier metrics and promotion/eviction logic. | Not implemented in current code base. | [TODO] |
| Sprint 6 – Precision / ANN adapters | Offer float16 toggle and ANN adapters with recall guard. | Precision controls and ANN integration absent. | [TODO] |

Action: open audit issues per sprint, align `tests/` coverage with acceptance matrix in `docs/ROADMAP.md`, and track progress alongside shared infra sprints.

---

## 5. Verification & Evidence Map
| Layer | Command / Artifact | Owner Sprint | Expected Evidence |
|-------|--------------------|--------------|-------------------|
| Namespace reset | `scripts/reset-sharedinfra-compose.sh` output + `kubectl get ns` post-reset | Sprint 0 | Namespace `soma-infra` absent prior to reinstall. |
| Kind readiness | `scripts/deploy-kind-sharedinfra.sh` log (`helm` + `kubectl wait`) | Sprint 1 | All pods ready within configured timeout. |
| Vault wiring | `kubectl describe externalsecret <app>-secrets` + Vault policy files | Sprint 2 | Secret synced; policy names match template. |
| Deployment pipeline | GitHub Action run URL + readiness logs | Sprint 3 | Pipeline green with readiness gate success. |
| DR / Incident readiness | Incident bundle archive + namespace audit log | Sprint 4 | Artefacts stored under `docs/infra/sprints/sprint-4/`. |
| Memory core validation | `pytest` output covering score/decay tests | Core Sprints 1–3 | Invariants enforced with deterministic tests. |

---

## 6. Immediate Next Steps
1. Author `docs/ops/SOMASTACK_SHARED_INFRA_PLAYBOOK.md` capturing the canonical instructions verbatim for version control.
2. Complete Sprint 0 tasks (script rename + doc updates) and commit artefacts to `docs/infra/sprints/sprint-0/`.
3. File planning tickets per sprint deliverable and link them to this roadmap.
4. Schedule audit of the memory core implementation to validate Sprint 1 acceptance criteria and unblock subsequent sprints.

Keep this roadmap synchronized with repository changes. Update the status tags (`[TODO]`, `[ACTIVE]`, `[DONE]`, `[BLOCKED]`) as work progresses and attach validation artefacts for every completed sprint.
