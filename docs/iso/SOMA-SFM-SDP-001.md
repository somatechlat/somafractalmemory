# SOMA-SFM-SDP-001: SomaFractalMemory Software Development Plan

> **Standard**: ISO/IEC 12207:2017 — Systems and Software — Software Life Cycle Processes
> **Owner**: SomaTech LAT

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SOMA-SFM-SDP-001: SomaFractalMemory Software Development Plan |
| Document Identifier | SOMA-SFM-SDP-001 |
| Version | 1.0.1 |
| Date | 2026-09-28 |
| Status | Approved |
| Author | SomaTech LAT Engineering |
| Approver | VP Engineering, SomaTech LAT |
| Classification | Confidential |
| ISO Reference | ISO/IEC 12207:2017 — Systems and Software — Software Life Cycle Processes |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|:--------|:-----|:-------|:------------|
| 1.0.0 | 2026-06-15 | Engineering | Initial SDP aligned with v0.2.0 production release |
| 1.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-SFM-SDP-001` \| case normalised to `Approved` \| prior classification `PROPRIETARY / COMMERCIAL SENSITIVE` normalised to `Confidential`. |

### Normative References

| Document ID | Title | Relationship |
|:------------|:------|:-------------|
| SOMA-SFM-ARCH-001 | SomaFractalMemory Architecture Specification | Architecture baseline |
| SOMA-SFM-EXEC-001 | SomaFractalMemory Project Execution Plan | Phase definitions and task sequencing |
| SOMA-SFM-SEC-001 | SomaFractalMemory Security Assessment | Security development requirements |
| SOMA-SFM-SRS-001 | SomaFractalMemory Software Requirements Specification | Requirements baseline |

---

## Section 1: Lifecycle Model

### 1.1 Process Model

SomaFractalMemory follows an **iterative lifecycle model** with four distinct phases, as defined in SOMA-SFM-EXEC-001:

```
Phase A              Phase B              Phase C              Phase D
Documentation &      Integration          Enhancement          Validation
Compliance           Support
────────────────────────────────────────────────────────────────────────►
Weeks 1-4            Weeks 3-7            Weeks 8-12           Weeks 14-16
```

| Phase | Name | Duration | Objective | Key Deliverables |
|:------|:-----|:---------|:----------|:-----------------|
| **A** | Documentation & Compliance | Weeks 1–4 | Finalize ISO docs, fix security findings | ISO documentation, auth fix, `.env` cleanup |
| **B** | Integration Support | Weeks 3–7 | Verify cross-component integration | SomaAgent01 integration, SomaBrain auth, backward compatibility |
| **C** | Enhancement | Weeks 8–12 | Improve quality, performance, test coverage | Embedding model evaluation, 20+ tests, load testing, Helm validation |
| **D** | Validation | Weeks 14–16 | Full system validation and sign-off | AAAS integration test, compatibility matrix verification, data integrity |

### 1.2 Gate Reviews

Each phase concludes with a **gate review** signed off by the project manager:

| Gate | Phase | Criteria |
|:-----|:------|:---------|
| Gate A | Documentation & Compliance | All ISO docs reviewed; security findings resolved |
| Gate B | Integration Support | Cross-component integration verified; no breaking changes |
| Gate C | Enhancement | 20+ test files; performance baseline established; Helm charts validated |
| Gate D | Validation | Full AAAS stack operational; compatibility matrix verified; production approval |

### 1.3 Iteration Policy

Phases overlap where dependencies allow (e.g., Phase B starts during Phase A). Each phase may spawn sub-iterations for rework discovered during gate reviews.

---

## Section 2: Development Processes

### 2.1 VIBE Coding Rules

SomaFractalMemory is developed under the **VIBE (Validated, Integrated, Bounded, Engineering-grade)** coding standard. The following rules are mandatory:

| Rule ID | Rule | Enforcement |
|:--------|:-----|:------------|
| VIBE-01 | Django ORM only — zero SQLAlchemy imports | Pre-commit grep, CI |
| VIBE-02 | Django Ninja only — zero FastAPI imports | Pre-commit grep, CI |
| VIBE-03 | Zero `TODO`, `FIXME`, `HACK`, `XXX` markers in production code | Pre-commit grep, CI |
| VIBE-04 | All public functions must have type annotations | mypy strict mode |
| VIBE-05 | All public classes and functions must have docstrings | Ruff (D rules) |
| VIBE-06 | Structured logging via `structlog` only — no bare `print()` | Code review |
| VIBE-07 | Error messages use `ErrorCode` enum with i18n support | Code review |
| VIBE-08 | No host path volume mounts in standalone Docker Compose | Infrastructure review |

### 2.2 Framework Stack

| Layer | Technology | Version | Rationale |
|:------|:-----------|:--------|:----------|
| Web Framework | Django | 5.0+ | ORM, migrations, admin, middleware ecosystem |
| API Framework | Django Ninja | 1.x | OpenAPI 3.0 auto-schema, type-safe routing |
| ASGI Server | Uvicorn | Latest | Production-grade async server |
| Database | PostgreSQL | 15+ | ArrayField, JSONField, recursive CTE support |
| Vector Store | Milvus | 2.3+ | Scalable ANN search, IVF_FLAT index |
| Cache | Redis | 7.0+ | Low-latency cache, rate limiting backend |
| Secrets | HashiCorp Vault | 1.13+ | KV v2 engine, dynamic secrets |
| Policy Engine | OPA | 0.54+ | Externalized authorization decisions |

### 2.3 Coding Conventions

| Convention | Standard |
|:-----------|:---------|
| Code style | Black (line length 88) |
| Import sorting | Ruff (isort-compatible) |
| Type checking | mypy (strict mode) |
| Naming | PEP 8 (snake_case functions, PascalCase classes) |
| Docstrings | Google style |
| Max function length | 50 lines (guideline) |
| Max file length | 500 lines (guideline) |

### 2.4 Branch Strategy

| Branch | Purpose | Merge Policy |
|:-------|:--------|:-------------|
| `main` | Production-ready code | PR with 1 approval, CI green |
| `develop` | Integration branch | PR with 1 approval, CI green |
| `feature/*` | Feature development | PR into `develop` |
| `fix/*` | Bug fixes | PR into `develop` or `main` (hotfix) |
| `release/*` | Release preparation | PR into `main` with gate review |

---

## Section 3: Tools

### 3.1 Development Environment

| Tool | Version | Purpose |
|:-----|:--------|:--------|
| Python | 3.12+ | Runtime |
| Poetry / pip | Latest | Dependency management |
| Docker | 24+ | Containerization |
| Docker Compose | 2.x | Local development stack |
| Helm | 3.x | Kubernetes deployment |

### 3.2 Code Quality Tools

| Tool | Version | Configuration | Purpose |
|:-----|:--------|:--------------|:--------|
| Black | 24.x | `pyproject.toml` | Code formatting |
| Ruff | 0.4+ | `pyproject.toml` | Linting, import sorting |
| mypy | 1.x | `pyproject.toml` (strict) | Static type checking |
| pre-commit | 3.x | `.pre-commit-config.yaml` | Git hook management |
| pytest | 8.x | `pyproject.toml` | Test runner |
| Hypothesis | 6.x | Property-based testing | Generative test cases |

### 3.3 Infrastructure Tools

| Tool | Purpose |
|:-----|:---------|
| Docker + Docker Compose | Standalone development stack (PostgreSQL, Milvus, Redis, Vault, OPA) |
| Helm Charts | Kubernetes deployment (local-dev, prod-ha profiles) |
| testcontainers | Ephemeral infrastructure for integration tests |
| GitHub Actions | CI/CD pipeline (lint, type check, test, build) |
| Prometheus + Grafana | Metrics collection and dashboards |

### 3.4 Dependency Policy

| Policy | Detail |
|:-------|:-------|
| Pinned versions | All production dependencies pinned in `pyproject.toml` |
| Security scanning | `pip-audit` or equivalent in CI |
| Update frequency | Monthly dependency review |
| License compliance | MIT / BSD / Apache 2.0 only |

---

## Section 4: Configuration Management

### 4.1 Version Control

| Aspect | Policy |
|:-------|:-------|
| VCS | Git (GitHub) |
| Versioning | Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`) |
| Current version | 0.2.0 |
| Changelog | `CHANGELOG.md` — every release documented |
| Tagging | `v{MAJOR}.{MINOR}.{PATCH}` (e.g., `v0.2.0`) |

### 4.2 Pre-Commit Hooks

From `.pre-commit-config.yaml`:

| Hook | Trigger | Action |
|:-----|:--------|:-------|
| `black` | `pre-commit` | Format code |
| `ruff` | `pre-commit` | Lint and auto-fix |
| `ruff --select I` | `pre-commit` | Sort imports |
| VIBE grep | `pre-commit` | Reject `TODO`, `FIXME`, `HACK`, `XXX`, `SQLAlchemy`, `FastAPI` patterns |

### 4.3 Release Process

| Step | Action | Owner |
|:-----|:-------|:------|
| 1 | Create `release/*` branch from `develop` | Engineering |
| 2 | Update `CHANGELOG.md` with release notes | Engineering |
| 3 | Bump version in `pyproject.toml` | Engineering |
| 4 | Run full test suite (CI green) | CI |
| 5 | Gate review (if applicable) | PM |
| 6 | Merge to `main` via PR | Engineering |
| 7 | Tag `v{version}` and build Docker image | CI |
| 8 | Push to container registry | CI |

### 4.4 Change Control

| Change Type | Approval | Documentation |
|:------------|:---------|:--------------|
| Bug fix | Engineering lead | PR description + test |
| Feature | Engineering lead + PM | PR description + test + SRS update if needed |
| Architecture change | Architecture Review Board | SOMA-SFM-ARCH-001 update |
| Security change | Security lead | SOMA-SFM-SEC-001 update |
| API breaking change | VP Engineering | Compatibility matrix update, deprecation notice |

---

## Section 5: Testing Strategy

### 5.1 Test Pyramid

```
                    ┌───────────┐
                    │  E2E (2)  │
                   ┌┴───────────┴┐
                   │ Integration  │
                   │    (6)       │
                  ┌┴─────────────┴┐
                  │   Unit (4)     │
                  │ + Resilience(2)│
                  └────────────────┘
```

### 5.2 Test Inventory (14 Files)

| # | File | Category | Coverage Area |
|:--|:-----|:---------|:-------------|
| 1 | `tests/unit/test_models.py` | Unit | ORM model constraints, field validation |
| 2 | `tests/test_sanity_service.py` | Unit | Service layer smoke tests |
| 3 | `tests/test_type_ignore_docs.py` | Unit | Type annotation compliance |
| 4 | `tests/test_exception_logging.py` | Unit | Structured error logging verification |
| 5 | `tests/test_http_api_coord_validation.py` | Integration | HTTP API coordinate validation, auth headers |
| 6 | `tests/test_deep_integration.py` | Integration | Multi-step workflows (store → search → graph → delete) |
| 7 | `tests/test_live_integration.py` | Integration | Live infrastructure integration (PostgreSQL, Milvus, Redis) |
| 8 | `tests/test_end_to_end_memory.py` | E2E | Full memory lifecycle (store → retrieve → search → delete) |
| 9 | `tests/proofs/test_docker_proof.py` | E2E | Docker deployment validation, health probes |
| 10 | `tests/verify_sfm_resilience_e2e.py` | Resilience | Graceful degradation, Milvus fallback, circuit breaker |
| 11 | `tests/conftest.py` | Fixtures | Shared pytest fixtures and configuration |
| 12 | `tests/run_10_cycle_audit.sh` | Script | 10-cycle audit loop for stability verification |
| 13 | `scripts/verify_openapi.py` | Verification | OpenAPI schema validation |
| 14 | `scripts/verify_api_live.py` | Verification | Live API endpoint verification |

### 5.3 Testing Requirements

| Requirement | Standard |
|:------------|:---------|
| Framework | pytest + Hypothesis |
| Infrastructure | Real PostgreSQL, Milvus, Redis (via Docker or testcontainers) |
| Mocking | Minimal — prefer real infrastructure over mocks |
| Coverage target | 80% line coverage on service layer |
| CI execution | All tests run on every PR |
| Flaky tests | Zero tolerance — must be fixed or quarantined |

### 5.4 Test Environments

| Environment | Infrastructure | Purpose |
|:------------|:---------------|:--------|
| Local | Docker Compose (standalone stack) | Developer testing |
| CI | GitHub Actions + Docker services | Automated test suite |
| Staging | Kubernetes (Helm local-dev) | Pre-production validation |
| Production | Kubernetes (Helm prod-ha) | Smoke tests, monitoring |

---

## Section 6: Review and Audit Schedule

### 6.1 Review Types

| Review | Frequency | Participants | Purpose |
|:-------|:----------|:-------------|:--------|
| Code review | Every PR | Engineering team | Quality gate before merge |
| Architecture review | Quarterly | Architecture Review Board | Design consistency, debt assessment |
| Security review | Quarterly | Security team | Threat model update, vulnerability assessment |
| ISO compliance audit | Annually | QA Lead + External auditor | Verify adherence to ISO standards |
| Risk register review | Quarterly | Risk Management Lead | Update risk ratings, mitigation progress |

### 6.2 Audit Schedule (2026–2027)

| Date | Audit Type | Scope | Auditor |
|:-----|:-----------|:------|:--------|
| 2026-06-15 | ISO baseline audit | All ISO docs, v0.2.0 codebase | Internal |
| 2026-09-15 | Quarterly risk review | SOMA-SFM-RISK-001 | Risk Management Lead |
| 2026-12-15 | Quarterly risk review + architecture review | SOMA-SFM-RISK-001, SOMA-SFM-ARCH-001 | Architecture Review Board |
| 2027-03-15 | Security review | SOMA-SFM-SEC-001 | Security team |
| 2027-06-15 | Annual ISO compliance audit | All ISO docs | QA Lead + External |

### 6.3 Non-Conformance Handling

Non-conformances discovered during reviews or audits shall be documented using the process defined in SOMA-SFM-QMS-001 Section 6. Each non-conformance receives:

1. A unique ID (NCR-SFM-XXX)
2. Severity classification (Critical / Major / Minor)
3. Root cause analysis
4. Corrective action with owner and target date
5. Verification of corrective action effectiveness

---

*End of SOMA-SFM-SDP-001 v1.0.0*
