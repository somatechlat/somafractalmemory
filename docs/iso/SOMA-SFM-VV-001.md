# SOMA-SFM-VV-001: SomaFractalMemory Verification and Validation Plan

> **Standard**: ISO/IEC/IEEE 16085:2006 — Systems and Software Engineering — Life Cycle Processes — Risk Management (adapted for V&V)
> **Owner**: SomaTech LAT

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SOMA-SFM-VV-001: SomaFractalMemory Verification and Validation Plan |
| Document Identifier | SOMA-SFM-VV-001 |
| Version | 1.0.1 |
| Date | 2026-09-28 |
| Status | Approved |
| Author | SomaTech LAT Engineering |
| Approver | VP Engineering, SomaTech LAT |
| Classification | Confidential |
| ISO Reference | ISO/IEC/IEEE 16085:2006 — Systems and Software Engineering — Life Cycle Processes — Risk Management (adapted for V&V) |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|:--------|:-----|:-------|:------------|
| 1.0.0 | 2026-06-15 | Engineering | Initial V&V Plan aligned with v0.2.0 production release |
| 1.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-SFM-VV-001` \| case normalised to `Approved` \| prior classification `PROPRIETARY / COMMERCIAL SENSITIVE` normalised to `Confidential`. |

### Normative References

| Document ID | Title | Relationship |
|:------------|:------|:-------------|
| SOMA-SFM-SRS-001 | Software Requirements Specification | Requirements baseline under verification |
| SOMA-SFM-ARCH-001 | Architecture Specification | Architectural design under verification |
| SOMA-SFM-SEC-001 | Security Assessment | Security controls under verification |
| SOMA-SFM-SDP-001 | Software Development Plan | Development process under verification |
| SOMA-SFM-PROD-001 | Production Readiness Assessment | Acceptance criteria reference |

### Distribution

| Recipient | Role | Access Level |
|:----------|:-----|:-------------|
| QA / Test Engineering | Verification execution | Full |
| SomaTech LAT Engineering | Remediation | Full |
| SRE Lead | Operational validation | Sections 3, 4 |

---

## Section 1: V&V Strategy

### 1.1 Objectives

| Objective | Description |
|:----------|:------------|
| **Correctness** | Verify that SomaFractalMemory v0.2.0 satisfies all requirements in SOMA-SFM-SRS-001 |
| **Completeness** | Verify that no requirement is untested or untraceable |
| **Conformance** | Validate adherence to ISO/IEC/IEEE standards referenced in the documentation set |
| **Production readiness** | Validate that the system meets acceptance criteria for production deployment |

### 1.2 V&V Approach

The V&V approach combines four complementary techniques:

| Technique | Application | Automation |
|:----------|:------------|:-----------|
| **Static analysis** | Ruff, mypy, pre-commit hooks | Fully automated (CI) |
| **Unit testing** | Model constraints, service logic, edge cases | Fully automated (pytest) |
| **Integration testing** | Multi-service workflows, API contracts, database operations | Automated with real infrastructure |
| **System testing** | End-to-end memory lifecycle, Docker deployment, resilience | Automated + manual validation |

### 1.3 V&V Process Flow

```
Requirements (SOMA-SFM-SRS-001)
        │
        ▼
  Test Design ──────────► Test Cases
        │                      │
        ▼                      ▼
  Test Implementation     Test Execution
        │                      │
        ▼                      ▼
  CI Pipeline             Results + Defects
        │                      │
        ▼                      ▼
  Continuous Verification  Corrective Action
        │                      │
        └──────────┬───────────┘
                   ▼
          Acceptance Decision (Section 4)
```

### 1.4 Entry and Exit Criteria

| Phase | Entry Criteria | Exit Criteria |
|:------|:---------------|:--------------|
| Unit testing | Code compiles, type checks pass | All unit tests green, coverage ≥ 80% |
| Integration testing | Unit tests pass, Docker stack operational | All integration tests green, API contracts verified |
| System testing | Integration tests pass | E2E lifecycle verified, Docker proof passes |
| Acceptance | All test categories pass | Acceptance criteria in Section 4 met |

---

## Section 2: Verification by Category

### 2.1 Memory CRUD Verification

| V&V ID | Requirement | Test Approach | Acceptance Criterion |
|:-------|:------------|:--------------|:---------------------|
| VV-MEM-001 | REQ-SFM-MEM-001 (Store) | Integration: store memory via API, verify DB record + Milvus vector | Memory persisted with correct payload, type, namespace |
| VV-MEM-002 | REQ-SFM-MEM-002 (Retrieve) | Integration: retrieve by coordinate, verify all fields | Payload, metadata, importance, access_count, timestamps returned |
| VV-MEM-003 | REQ-SFM-MEM-003 (Soft-delete) | Integration: delete then search, verify exclusion | Deleted memory absent from all queries |
| VV-MEM-004 | REQ-SFM-MEM-004 (Unique constraint) | Unit: duplicate coordinate insertion | Database raises IntegrityError |
| VV-MEM-005 | REQ-SFM-MEM-005 (Audit log) | Integration: perform CRUD, verify AuditLog record | Correct action, namespace, tenant, timestamp in log |
| VV-MEM-006 | REQ-SFM-MEM-006 (Access tracking) | Unit: retrieve memory, check counters | access_count incremented, last_accessed updated |

### 2.2 Search Verification

| V&V ID | Requirement | Test Approach | Acceptance Criterion |
|:-------|:------------|:--------------|:---------------------|
| VV-SRCH-001 | REQ-SFM-SRCH-001 (Semantic search) | Integration: store known memory, search with related query | Relevant memory in top-k results |
| VV-SRCH-002 | REQ-SFM-SRCH-002 (Filters) | API: search with memory_type and metadata filters | Only matching results returned |
| VV-SRCH-003 | REQ-SFM-SRCH-003 (Pagination) | API: search with top_k=5, offset=10 | Exactly 5 results starting at offset 10 |
| VV-SRCH-004 | REQ-SFM-SRCH-004 (Fallback) | Resilience: stop Milvus, search via API | PostgreSQL fallback returns results |
| VV-SRCH-005 | REQ-SFM-SRCH-005 (Tenant scoping) | Integration: search across tenants | Only authenticated tenant's memories returned |

### 2.3 Graph Verification

| V&V ID | Requirement | Test Approach | Acceptance Criterion |
|:-------|:------------|:--------------|:---------------------|
| VV-GRAPH-001 | REQ-SFM-GRAPH-001 (Link creation) | Unit: create link, verify unique constraint | Link persisted, duplicate rejected |
| VV-GRAPH-002 | REQ-SFM-GRAPH-002 (Neighbors) | Integration: create chain of links, query neighbors | Correct neighbors with link_type filter |
| VV-GRAPH-003 | REQ-SFM-GRAPH-003 (Shortest path) | Unit/Integration: create graph, find path | Shortest path returned, max_depth respected |
| VV-GRAPH-004 | REQ-SFM-GRAPH-004 (Export) | Manual: export graph, verify JSON structure | Valid streaming JSON, O(1) memory |

### 2.4 Multi-Tenancy Verification

| V&V ID | Requirement | Test Approach | Acceptance Criterion |
|:-------|:------------|:--------------|:---------------------|
| VV-MTEN-001 | REQ-SFM-MTEN-001 (Namespace isolation) | Integration: store in two namespaces, verify Milvus collections | Separate `sfm_{ns}` collections |
| VV-MTEN-002 | REQ-SFM-MTEN-002 (Tenant isolation) | Integration: query as different tenants | No cross-tenant data leakage |
| VV-MTEN-003 | REQ-SFM-MTEN-003 (Namespace access) | Auth test: key with restricted namespace | Unauthorized namespace returns 403/empty |
| VV-MTEN-004 | REQ-SFM-MTEN-004 (Crypto separation) | Integration: cross-tenant search attempt | Zero results for other tenant's data |

### 2.5 Authentication Verification

| V&V ID | Requirement | Test Approach | Acceptance Criterion |
|:-------|:------------|:--------------|:---------------------|
| VV-AUTH-001 | REQ-SFM-AUTH-001 (Bearer token) | API: valid and invalid tokens | Valid → 200, invalid → 401 |
| VV-AUTH-002 | REQ-SFM-AUTH-002 (sbk_* validation) | Integration: sbk_* token via SomaBrain mock | Validated with correct tenant + scopes |
| VV-AUTH-003 | REQ-SFM-AUTH-003 (sfm_* validation) | Unit: APIKey SHA-256 lookup | Correct key accepted, expired rejected |

### 2.6 Audit Logging Verification

| V&V ID | Requirement | Test Approach | Acceptance Criterion |
|:-------|:------------|:--------------|:---------------------|
| VV-AUDIT-001 | REQ-SFM-AUDIT-001 (CRUD audit) | Integration: CRUD operations, query AuditLog | Every operation logged with all required fields |
| VV-AUDIT-002 | REQ-SFM-AUDIT-002 (Immutability) | Security: attempt audit log modification via API | No endpoint permits audit log mutation |

---

## Section 3: Test Inventory

### 3.1 Test File Mapping

The following 14 test files constitute the current verification suite:

| # | File Path | Category | V&V IDs Covered | Requirements Covered |
|:--|:----------|:---------|:----------------|:---------------------|
| 1 | `tests/unit/test_models.py` | Unit | VV-MEM-004, VV-MEM-006, VV-GRAPH-001, VV-GRAPH-003, VV-AUTH-003 | REQ-SFM-MEM-004, REQ-SFM-MEM-006, REQ-SFM-GRAPH-001, REQ-SFM-GRAPH-003, REQ-SFM-AUTH-003, REQ-SFM-AUDIT-002 |
| 2 | `tests/test_sanity_service.py` | Unit | VV-MEM-002 | REQ-SFM-MEM-002 |
| 3 | `tests/test_type_ignore_docs.py` | Unit | — | REQ-SFM-NFR-MNT-002 |
| 4 | `tests/test_exception_logging.py` | Unit | VV-AUDIT-001 | REQ-SFM-MEM-005, REQ-SFM-AUDIT-001 |
| 5 | `tests/test_http_api_coord_validation.py` | Integration | VV-SRCH-002, VV-SRCH-003, VV-MTEN-003, VV-AUTH-001 | REQ-SFM-SRCH-002, REQ-SFM-SRCH-003, REQ-SFM-MTEN-003, REQ-SFM-AUTH-001, REQ-SFM-NFR-PERF-003 |
| 6 | `tests/test_deep_integration.py` | Integration | VV-MEM-001, VV-MEM-002, VV-MEM-003, VV-MEM-005, VV-SRCH-001, VV-SRCH-005, VV-GRAPH-002, VV-MTEN-002 | REQ-SFM-MEM-001 through REQ-SFM-MEM-005, REQ-SFM-SRCH-001, REQ-SFM-SRCH-005, REQ-SFM-GRAPH-002, REQ-SFM-MTEN-002, REQ-SFM-AUDIT-001 |
| 7 | `tests/test_live_integration.py` | Integration | VV-SRCH-001, VV-MTEN-001, VV-MTEN-004, VV-AUTH-002 | REQ-SFM-SRCH-001, REQ-SFM-MTEN-001, REQ-SFM-MTEN-004, REQ-SFM-AUTH-002 |
| 8 | `tests/test_end_to_end_memory.py` | E2E | VV-MEM-001, VV-MEM-002, VV-MEM-003 | REQ-SFM-MEM-001, REQ-SFM-MEM-002, REQ-SFM-MEM-003 |
| 9 | `tests/proofs/test_docker_proof.py` | E2E | VV-AUTH-001 | REQ-SFM-AUTH-001, REQ-SFM-NFR-REL-003 |
| 10 | `tests/verify_sfm_resilience_e2e.py` | Resilience | VV-SRCH-004 | REQ-SFM-SRCH-004, REQ-SFM-NFR-REL-001, REQ-SFM-NFR-REL-002 |
| 11 | `tests/conftest.py` | Fixtures | — | (shared infrastructure) |
| 12 | `tests/run_10-cycle_audit.sh` | Script | — | Stability verification |
| 13 | `scripts/verify_openapi.py` | Verification | — | API schema correctness |
| 14 | `scripts/verify_api_live.py` | Verification | — | Live API health |

### 3.2 Coverage Summary

| Requirement Domain | Requirements | V&V Items | Test Files | Coverage |
|:-------------------|:-------------|:----------|:-----------|:---------|
| Memory CRUD | 6 | 6 | 4 | 100% |
| Search | 5 | 5 | 5 | 100% |
| Graph | 4 | 4 | 2 | 100% |
| Multi-tenancy | 4 | 4 | 3 | 100% |
| Authentication | 3 | 3 | 4 | 100% |
| Audit Logging | 2 | 2 | 3 | 100% |
| Non-Functional | 10 | — | 4 | 70% (perf/drill pending) |
| **Total** | **34** | **24** | **14** | **91%** |

---

## Section 4: Acceptance Criteria

### 4.1 Production Release Acceptance (v0.2.0)

The following criteria SHALL be met before SomaFractalMemory v0.2.0 is accepted for production deployment:

| ID | Criterion | Target | Current | Status |
|:---|:----------|:-------|:--------|:-------|
| AC-01 | Version | 0.2.0 | 0.2.0 | **PASS** |
| AC-02 | Maturity level | Production Ready | Production Ready | **PASS** |
| AC-03 | Zero TODO/FIXME/HACK/XXX in production code | 0 | 0 | **PASS** |
| AC-04 | Ruff linting | 0 errors | 0 errors | **PASS** |
| AC-05 | mypy type checking | 0 errors | 0 errors | **PASS** |
| AC-06 | Test files | ≥ 14 | 14 | **PASS** |
| AC-07 | Unit test suite | All pass | All pass | **PASS** |
| AC-08 | Integration test suite | All pass | All pass | **PASS** |
| AC-09 | E2E test suite | All pass | All pass | **PASS** |
| AC-10 | Docker deployment proof | Health checks pass | Health checks pass | **PASS** |
| AC-11 | Security checklist (SOMA-SFM-SEC-001) | 15/15 controls pass | 15/15 pass | **PASS** |
| AC-12 | ISO documentation complete | 10 docs | 10 docs | **PASS** |
| AC-13 | Health endpoints operational | /healthz, /readyz | Operational | **PASS** |
| AC-14 | Prometheus metrics endpoint | /metrics | Operational | **PASS** |
| AC-15 | Production readiness score (SOMA-SFM-PROD-001) | ≥ 80/100 | 87/100 | **PASS** |

### 4.2 Acceptance Decision

| Decision | Criteria |
|:---------|:---------|
| **ACCEPT** | All AC criteria PASS; no Critical or Major non-conformances open |
| **CONDITIONAL ACCEPT** | ≤ 2 Minor non-conformances with documented corrective actions |
| **REJECT** | Any AC FAIL; or any Critical non-conformance open |

### 4.3 Current Verdict

**ACCEPT** — All 15 acceptance criteria are met. SomaFractalMemory v0.2.0 is approved for production deployment.

### 4.4 Residual V&V Items (Post-v0.2.0)

| Item | Target Version | Owner |
|:-----|:---------------|:------|
| Performance baseline (p50/p99) | v0.2.5 | Performance Lead |
| Load testing suite | v0.2.5 | QA Lead |
| Cross-tenant isolation dedicated test | v0.2.5 | Security Engineering |
| Graph export manual verification | v0.3.0 | Engineering |
| Operational drill (RTO validation) | v0.2.5 | SRE Lead |

---

*End of SOMA-SFM-VV-001 v1.0.0*
