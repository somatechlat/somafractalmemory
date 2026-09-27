# SOMA-SFM-QMS-001: SomaFractalMemory Quality Manual

> **Document ID**: SOMA-SFM-QMS-001
> **Version**: 1.0.0
> **Date**: 2026-06-15
> **Classification**: PROPRIETARY / COMMERCIAL SENSITIVE
> **Standard**: ISO 9001:2015 — Quality Management Systems — Requirements
> **Owner**: SomaTech LAT
> **Status**: APPROVED

---

## Document Control

| Field | Value |
|:------|:------|
| Document ID | SOMA-SFM-QMS-001 |
| Version | 1.0.0 |
| Status | APPROVED |
| Classification | PROPRIETARY / COMMERCIAL SENSITIVE |
| Author | SomaTech LAT Engineering |
| Reviewer | Quality Assurance Lead |
| Approver | CTO, SomaTech LAT |

### Revision History

| Version | Date | Author | Description |
|:--------|:-----|:-------|:------------|
| 1.0.0 | 2026-06-15 | Engineering | Initial Quality Manual aligned with v0.2.0 production release |

### Normative References

| Document ID | Title | Relationship |
|:------------|:------|:-------------|
| SOMA-SFM-SRS-001 | Software Requirements Specification | Requirements baseline |
| SOMA-SFM-SDP-001 | Software Development Plan | Development process definition |
| SOMA-SFM-VV-001 | Verification and Validation Plan | V&V process definition |
| SOMA-SFM-AUDIT-001 | Audit Report | Audit findings and compliance status |
| SOMA-SFM-RISK-001 | Risk Register | Risk management context |

---

## Section 1: Quality Policy

### 1.1 Policy Statement

SomaTech LAT is committed to delivering **production-grade, zero-defect software** for the Soma Cognitive Triad. SomaFractalMemory shall be developed and maintained under the following quality principles:

1. **VIBE Compliance**: All code shall adhere to VIBE (Validated, Integrated, Bounded, Engineering-grade) coding rules. No exceptions are permitted without formal deviation approval.
2. **Zero Tech Debt Markers**: Production code shall contain zero `TODO`, `FIXME`, `HACK`, or `XXX` markers. All work items are tracked externally in the project management system.
3. **Type Safety**: All Python code shall pass strict mypy type checking. Public function signatures shall have complete type annotations.
4. **Test-First Mentality**: No requirement shall be considered implemented until it has a corresponding automated test.
5. **Continuous Improvement**: Quality metrics shall be reviewed quarterly, with corrective actions tracked to closure.

### 1.2 VIBE Rules (Quality Mandate)

| Rule | Description | Enforcement |
|:-----|:------------|:------------|
| VIBE-01 | Django ORM only — zero SQLAlchemy | Pre-commit, CI |
| VIBE-02 | Django Ninja only — zero FastAPI | Pre-commit, CI |
| VIBE-03 | Zero TODO/FIXME/HACK/XXX | Pre-commit, CI |
| VIBE-04 | Complete type annotations | mypy strict |
| VIBE-05 | Docstrings on all public APIs | Ruff D-rules |
| VIBE-06 | Structured logging via structlog | Code review |
| VIBE-07 | ErrorCode enum for error messages | Code review |
| VIBE-08 | No host path mounts in Docker | Infrastructure review |

---

## Section 2: Quality Objectives

### 2.1 Measurable Quality Objectives (2026)

| ID | Objective | Target | Current | Status |
|:---|:----------|:-------|:--------|:-------|
| QO-01 | Zero type errors (mypy strict) | 0 | 0 | **MET** |
| QO-02 | Test file count | ≥ 20 | 14 | IN PROGRESS (target v0.3.0) |
| QO-03 | Zero TODO/FIXME markers in production code | 0 | 0 | **MET** |
| QO-04 | Ruff lint errors | 0 | 0 | **MET** |
| QO-05 | Production readiness score | ≥ 80/100 | 87/100 | **MET** |
| QO-06 | Security controls passing | 15/15 | 15/15 | **MET** |
| QO-07 | ISO documentation set complete | 10 docs | 10 docs | **MET** |
| QO-08 | Open Critical/Major non-conformances | 0 | 0 | **MET** |
| QO-09 | Test coverage (service layer) | ≥ 80% | ~80% | **MET** |
| QO-10 | Zero placeholder secrets in production | 0 | 0 | IN PROGRESS (target v0.2.5) |

### 2.2 Objective Review Cycle

| Cycle | Action | Owner |
|:------|:-------|:------|
| Monthly | Update metrics dashboard | QA Lead |
| Quarterly | Review objectives, adjust targets | VP Engineering |
| Annually | Strategic quality review | CTO |

---

## Section 3: Process Map

### 3.1 Quality Process Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    REQUIREMENTS                               │
│  SOMA-SFM-SRS-001 ──► Review ──► Baseline                    │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT                                │
│  VIBE rules ──► Code ──► Pre-commit hooks ──► PR              │
│                                                    │          │
│                                          Code Review          │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    VERIFICATION                               │
│  CI Pipeline: Ruff ──► mypy ──► pytest ──► Build              │
│  Integration: Docker stack ──► E2E tests                      │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    RELEASE                                    │
│  Gate review ──► Tag ──► Docker build ──► Deploy              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    MONITORING & IMPROVEMENT                   │
│  Prometheus metrics ──► Health probes ──► Audit logs          │
│  Quarterly review ──► Corrective actions ──► Process update   │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Process Ownership

| Process | Owner | Reviewer |
|:--------|:------|:---------|
| Requirements management | Engineering Lead | PM |
| Development (coding + review) | Engineering Team | Engineering Lead |
| Testing and verification | QA Lead | VP Engineering |
| Release management | Engineering Lead | PM |
| Monitoring and operations | SRE Lead | VP Engineering |
| Non-conformance management | QA Lead | CTO |
| Continuous improvement | VP Engineering | CTO |

---

## Section 4: Quality Controls

### 4.1 Automated Quality Gates

| Gate | Tool | Trigger | Action on Failure |
|:-----|:-----|:--------|:------------------|
| Code formatting | Black | Pre-commit, CI | Block commit / fail build |
| Linting | Ruff | Pre-commit, CI | Block commit / fail build |
| Type checking | mypy (strict) | CI | Fail build |
| Tech debt scan | grep (TODO/FIXME/HACK/XXX) | Pre-commit, CI | Block commit / fail build |
| Forbidden imports | grep (SQLAlchemy, FastAPI) | Pre-commit, CI | Block commit / fail build |
| Unit tests | pytest | CI | Fail build |
| Integration tests | pytest + Docker | CI | Fail build |
| Security audit | pip-audit | CI | Fail build |

### 4.2 Manual Quality Controls

| Control | Frequency | Owner | Documentation |
|:--------|:----------|:------|:--------------|
| Code review | Every PR | Engineering team | PR comments |
| Architecture review | Quarterly | Architecture Review Board | SOMA-SFM-ARCH-001 |
| Security review | Quarterly | Security team | SOMA-SFM-SEC-001 |
| ISO compliance audit | Annually | QA Lead + External | SOMA-SFM-AUDIT-001 |
| Risk register review | Quarterly | Risk Management Lead | SOMA-SFM-RISK-001 |
| Gate review (per phase) | Per phase | PM | SOMA-SFM-EXEC-001 |

### 4.3 CI Pipeline Quality Sequence

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Ruff    │───►│  mypy    │───►│  pytest  │───►│  Docker  │───►│  Deploy  │
│  Lint    │    │  Type    │    │  Test    │    │  Build   │    │  (tag)   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │                │               │
     ▼                ▼               ▼
  FAIL → block     FAIL → block    FAIL → block
```

---

## Section 5: Metrics

### 5.1 Current Quality Metrics (v0.2.0)

| Metric | Value | Target | Status |
|:-------|:------|:-------|:-------|
| Python SLOC | ~5,135 | — | Baseline |
| Test files | 14 | 20+ | IN PROGRESS |
| TODO/FIXME markers | 0 | 0 | **PASS** |
| HACK/XXX markers | 0 | 0 | **PASS** |
| SQLAlchemy imports | 0 | 0 | **PASS** |
| FastAPI imports | 0 | 0 | **PASS** |
| Version | 0.2.0 | — | Current |
| Maturity | Production Ready | Production Ready | **PASS** |
| Production readiness score | 87/100 | ≥ 80 | **PASS** |
| Security controls | 15/15 | 15/15 | **PASS** |
| ISO documents | 10 | 10 | **PASS** |
| Non-conformances (Critical) | 0 | 0 | **PASS** |
| Non-conformances (Major) | 0 | 0 | **PASS** |
| Non-conformances (Minor) | 1 | 0 | TRACKED |

### 5.2 Metrics Trending

| Metric | v0.1.0 | v0.2.0 | Trend | v0.3.0 Target |
|:-------|:-------|:-------|:------|:---------------|
| SLOC | ~3,200 | ~5,135 | ↑ Growing with features | ~7,000 |
| Test files | 6 | 14 | ↑ +133% | 20+ |
| TODO/FIXME | 12 | 0 | ↓ Eliminated | 0 |
| Security score | B+ | A- | ↑ Improving | A |
| Readiness score | 62/100 | 87/100 | ↑ +40% | 92/100 |

### 5.3 Metrics Collection

| Metric Source | Tool | Frequency |
|:-------------|:-----|:----------|
| Code quality | Ruff, mypy | Every CI run |
| Test results | pytest + coverage | Every CI run |
| Tech debt | Pre-commit grep | Every commit |
| Security | pip-audit, SOMA-SFM-SEC-001 | Quarterly |
| Performance | Prometheus /metrics | Continuous |
| Availability | /healthz monitoring | Continuous |

---

## Section 6: Non-Conformance

### 6.1 Non-Conformance Process

```
Detection ──► Registration ──► Classification ──► Root Cause ──► Corrective Action ──► Verification
    │              │                │                │                   │                   │
    ▼              ▼                ▼                ▼                   ▼                   ▼
Audit/test    NCR-SFM-XXX     Critical/Major/    5-Why or           Owner + target     Re-test +
finding                      Minor              fishbone            date               sign-off
```

### 6.2 Severity Classification

| Severity | Definition | Response Time | Resolution Time |
|:---------|:-----------|:--------------|:----------------|
| **Critical** | Data loss, security breach, system outage | Immediate | 24 hours |
| **Major** | Feature non-functional, significant quality degradation | 1 business day | 1 sprint |
| **Minor** | Cosmetic, documentation, minor deviation | 1 sprint | Next release |

### 6.3 Current Non-Conformance Register

| NCR ID | Description | Severity | Root Cause | Corrective Action | Owner | Target | Status |
|:-------|:------------|:---------|:-----------|:------------------|:------|:-------|:-------|
| NCR-SFM-001 | SimpleTokenAuth uses `==` instead of `hmac.compare_digest` (auth.py:202) | Minor | Code review oversight | Replace with `hmac.compare_digest` | Security Engineering | v0.2.5 | OPEN |

### 6.4 NCR Metrics

| Metric | Value |
|:-------|:------|
| Total NCRs (all time) | 3 |
| NCRs closed | 2 |
| NCRs open | 1 |
| Critical/Major NCRs open | 0 |
| Average resolution time (Minor) | 2 sprints |

---

## Section 7: Improvement Plan

### 7.1 Continuous Improvement Framework

SomaFractalMemory follows a **Plan-Do-Check-Act (PDCA)** cycle:

| Phase | Activity | Frequency |
|:------|:---------|:----------|
| **Plan** | Identify improvement opportunities from metrics, audits, NCRs | Quarterly |
| **Do** | Implement corrective actions and process changes | Per sprint |
| **Check** | Verify effectiveness through metrics and re-testing | Quarterly |
| **Act** | Standardise successful changes, update documentation | Per release |

### 7.2 Improvement Items

| ID | Item | Category | Priority | Target Version | Owner |
|:---|:-----|:---------|:---------|:---------------|:------|
| IMP-001 | Evaluate and integrate ML embedding model (e.g., `all-MiniLM-L6-v2`) to replace hash-based `HashEmbedder` | Quality / Search | HIGH | v0.3.0 | ML Engineering Lead |
| IMP-002 | Expand test suite from 14 to 20+ files | Testing | HIGH | v0.3.0 | QA Lead |
| IMP-003 | Add performance baseline (p50/p99) benchmarks | Performance | HIGH | v0.2.5 | Performance Lead |
| IMP-004 | Implement load testing suite | Testing | MEDIUM | v0.2.5 | QA Lead |
| IMP-005 | Add Prometheus alerting rules | Operations | MEDIUM | v0.2.5 | SRE Lead |
| IMP-006 | Automate secret rotation via Vault Agent | Security | MEDIUM | v0.3.0 | DevOps Lead |
| IMP-007 | Implement audit log archival policy | Operations | MEDIUM | v0.2.5 | DBA Lead |
| IMP-008 | Add TLS for internal Docker services | Security | MEDIUM | v0.3.0 | Infrastructure Lead |
| IMP-009 | Create operations runbook | Documentation | MEDIUM | v0.2.5 | SRE Lead |
| IMP-010 | Eliminate placeholder secrets in `.env.example` | Security | HIGH | v0.2.5 | DevOps Lead |

### 7.3 Embedding Model Upgrade Evaluation (IMP-001)

The highest-priority improvement item is the replacement of the current `HashEmbedder` with a machine-learning-based embedding model. This is tracked as **RISK-001** in SOMA-SFM-RISK-001.

| Aspect | Current State | Target State |
|:-------|:--------------|:-------------|
| Embedding model | SHA-256 hash-based (deterministic, non-semantic) | Sentence-transformer (e.g., `all-MiniLM-L6-v2`) |
| Semantic quality | No semantic meaning | Meaningful cosine similarity |
| Latency | ~1ms (CPU hash) | ~5-10ms (CPU inference) or ~1ms (GPU) |
| Dependencies | None (stdlib only) | `sentence-transformers`, `torch` |
| Fallback | N/A | Keep hash embedder via `SOMA_FORCE_HASH_EMBEDDINGS=True` |
| Milvus compatibility | 768-dim IVF_FLAT | May need dimension adjustment (384 for MiniLM) |

### 7.4 Improvement Review

| Review | Frequency | Participants | Output |
|:-------|:----------|:-------------|:-------|
| Improvement backlog review | Monthly | QA Lead, VP Engineering | Prioritized IMP list |
| PDCA cycle review | Quarterly | CTO, VP Engineering | Process updates, effectiveness metrics |
| Annual quality review | Annually | CTO, VP Engineering, External | Strategic quality direction |

---

*End of SOMA-SFM-QMS-001 v1.0.0*
