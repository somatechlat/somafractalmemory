# SOMA-SFM-SRS-001: SomaFractalMemory Software Requirements Specification

> **Standard**: ISO/IEC/IEEE 29148:2018 — Systems and Software Engineering — Life Cycle Processes — Requirements Engineering
> **Owner**: SomaTech LAT

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SOMA-SFM-SRS-001: SomaFractalMemory Software Requirements Specification |
| Document Identifier | SOMA-SFM-SRS-001 |
| Version | 1.0.1 |
| Date | 2026-09-28 |
| Status | Approved |
| Author | SomaTech LAT Engineering |
| Approver | CTO, SomaTech LAT |
| Classification | Confidential |
| ISO Reference | ISO/IEC/IEEE 29148:2018 — Systems and Software Engineering — Life Cycle Processes — Requirements Engineering |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|:--------|:-----|:-------|:------------|
| 1.0.0 | 2026-06-15 | Engineering | Initial SRS aligned with v0.2.0 production release |
| 1.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-SFM-SRS-001` \| case normalised to `Approved` \| prior classification `PROPRIETARY / COMMERCIAL SENSITIVE` normalised to `Confidential`. |

### Normative References

| Document ID | Title | Relationship |
|:------------|:------|:-------------|
| SOMA-SFM-ARCH-001 | SomaFractalMemory Architecture Specification | Architectural context for all requirements |
| SOMA-SFM-SEC-001 | SomaFractalMemory Security Assessment | Security constraints and controls |
| SOMA-SFM-RISK-001 | SomaFractalMemory Risk Register | Known risks affecting requirements |
| SRS-SOMAFRACTALMEMORY-MASTER | SomaFractalMemory Master Technical Specification | Authoritative technical reference |

### Distribution

| Recipient | Role | Access Level |
|:----------|:-----|:-------------|
| SomaTech LAT Engineering | Implementation | Full |
| SomaBrain Team | Integration | Sections 2, 4 |
| SomaAgent01 Team | Integration | Sections 2, 4 |
| QA / Test Engineering | Verification | Full |

---

## Section 1: Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the complete set of functional and non-functional requirements for **SomaFractalMemory (SFM)**, the distributed long-term memory service of the **Soma Cognitive Triad**. It is written in compliance with ISO/IEC/IEEE 29148:2018 and serves as the authoritative requirements baseline for development, testing, and acceptance.

### 1.2 System Overview

| Attribute | Value |
|:----------|:------|
| System Name | SomaFractalMemory |
| Version | 0.2.0 |
| Maturity | Production Ready |
| Codebase | ~5,135 lines of Python |
| Framework | Django 5.0+ / Django Ninja |
| Standalone Port | 10101 |
| AAAS Port | 63901 |

### 1.3 Scope

This SRS covers the following functional domains:

- **Memory CRUD**: Coordinate-based storage, retrieval, update, and soft-delete of memories
- **Semantic Search**: Vector-based similarity search with filtering and pagination
- **Graph Operations**: Typed, weighted links between memories with neighbor queries and shortest-path traversal
- **Multi-Tenancy**: Namespace and tenant isolation with cryptographic boundaries
- **Authentication**: Bearer token, HMAC, and SomaBrain token validation
- **Audit Logging**: Immutable operation log for every CRUD and search action

### 1.4 Definitions and Acronyms

| Term | Definition |
|:-----|:-----------|
| SFM | SomaFractalMemory |
| Coordinate | A tuple of floats (e.g., `(1.0, 2.0, 3.0)`) serving as a fractal memory address |
| Namespace | Logical grouping of memories with isolated Milvus collections |
| Tenant | An organisational unit whose data is cryptographically separated |
| AAAS | Agent-as-a-Service (integrated deployment mode) |
| OPA | Open Policy Agent (external authorization engine) |

---

## Section 2: Functional Requirements

### 2.1 Memory CRUD — REQ-SFM-MEM

| Req ID | Requirement | Priority | Verification |
|:-------|:------------|:---------|:-------------|
| REQ-SFM-MEM-001 | The system SHALL store a memory identified by a fractal coordinate, payload (JSON), memory type (`episodic` or `semantic`), namespace, and tenant. A `Memory` record and corresponding Milvus vector embedding SHALL be created atomically. | MUST | Integration test |
| REQ-SFM-MEM-002 | The system SHALL retrieve a stored memory by its coordinate, namespace, and tenant. The response SHALL include the payload, metadata, importance score, access count, and timestamps. | MUST | Unit test, E2E test |
| REQ-SFM-MEM-003 | The system SHALL soft-delete a memory by setting `is_deleted = True` and recording `deleted_at`. Soft-deleted memories SHALL NOT be returned by any read or search operation. | MUST | Integration test |
| REQ-SFM-MEM-004 | The system SHALL enforce a unique constraint on `(namespace, tenant, coordinate_key)` to prevent duplicate memories at the same coordinate within a namespace/tenant scope. | MUST | Unit test (model constraint) |
| REQ-SFM-MEM-005 | Every memory store, retrieve, delete, and search operation SHALL create an entry in the `AuditLog` table (`sfm_audit_log`) recording the action, namespace, coordinate, tenant, user ID, IP address, operation details, and timestamp. | MUST | Audit test |
| REQ-SFM-MEM-006 | The system SHALL increment `access_count` and update `last_accessed` on each successful memory retrieval. | MUST | Unit test |

### 2.2 Search — REQ-SFM-SRCH

| Req ID | Requirement | Priority | Verification |
|:-------|:------------|:---------|:-------------|
| REQ-SFM-SRCH-001 | The system SHALL perform semantic search by generating a 768-dimensional embedding vector from the query text and performing a cosine-similarity search against the Milvus collection for the target namespace. | MUST | Integration test |
| REQ-SFM-SRCH-002 | The system SHALL support filtering search results by `memory_type` (episodic/semantic) and arbitrary key-value metadata filters. | MUST | API test |
| REQ-SFM-SRCH-003 | The system SHALL support pagination via `top_k` (limit) and `offset` parameters. Default `top_k` SHALL be 10, maximum 100. | MUST | API test |
| REQ-SFM-SRCH-004 | The system SHALL provide a fallback to PostgreSQL GIN-indexed JSONB payload search when Milvus is unavailable or returns no results. | MUST | Resilience test |
| REQ-SFM-SRCH-005 | Search results SHALL exclude soft-deleted memories and SHALL be scoped to the authenticated tenant's namespace. | MUST | Integration test |

### 2.3 Graph Operations — REQ-SFM-GRAPH

| Req ID | Requirement | Priority | Verification |
|:-------|:------------|:---------|:-------------|
| REQ-SFM-GRAPH-001 | The system SHALL create a directed, typed, weighted graph link between two memory coordinates. The link SHALL be uniquely identified by `(namespace, tenant, from_coordinate_key, to_coordinate_key, link_type)`. | MUST | Unit test |
| REQ-SFM-GRAPH-002 | The system SHALL retrieve all neighbor links for a given coordinate, supporting optional `link_type` filter and pagination via `limit` and `offset`. | MUST | Integration test |
| REQ-SFM-GRAPH-003 | The system SHALL compute the shortest path between two coordinates using a PostgreSQL recursive CTE with configurable `max_depth` (default 5) and cycle detection. | MUST | Unit test, graph test |
| REQ-SFM-GRAPH-004 | The system SHALL export the entire graph as a streaming JSON file with O(1) memory footprint for production-scale graphs. | SHOULD | Manual verification |

### 2.4 Multi-Tenancy — REQ-SFM-MTEN

| Req ID | Requirement | Priority | Verification |
|:-------|:------------|:---------|:-------------|
| REQ-SFM-MTEN-001 | The system SHALL isolate memory data by namespace. Each namespace SHALL have its own Milvus collection named `sfm_{namespace}`. | MUST | Integration test |
| REQ-SFM-MTEN-002 | The system SHALL isolate data by tenant. All ORM queries SHALL include a `WHERE tenant = ...` clause. The `tenant` value SHALL be derived exclusively from the authentication context, never from request headers. | MUST | Tenant isolation test |
| REQ-SFM-MTEN-003 | The system SHALL enforce namespace access control via `allowed_namespaces` per API key. Keys with `allowed_namespaces = ["*"]` SHALL have unrestricted access. | MUST | Auth test |
| REQ-SFM-MTEN-004 | The system SHALL provide cryptographic namespace separation such that data stored under one tenant SHALL NOT be discoverable or accessible by another tenant through any API endpoint. | MUST | Cross-tenant isolation test |

### 2.5 Authentication — REQ-SFM-AUTH

| Req ID | Requirement | Priority | Verification |
|:-------|:------------|:---------|:-------------|
| REQ-SFM-AUTH-001 | The system SHALL authenticate API requests using Bearer token authentication. In Standalone mode, the token SHALL be validated using `hmac.compare_digest` (constant-time comparison) against `SOMA_API_TOKEN`. | MUST | Security test |
| REQ-SFM-AUTH-002 | The system SHALL validate `sbk_*` prefixed tokens by making an HTTP GET request to SomaBrain at `{SOMABRAIN_URL}/api/v1/auth/verify` with a 3-second timeout. The response SHALL include `tenant_slug`, `tenant_id`, `api_key_id`, `scopes`, and `is_test`. | MUST | Integration test |
| REQ-SFM-AUTH-003 | The system SHALL validate `sfm_*` prefixed tokens by computing a SHA-256 hash and looking up the corresponding `APIKey` record. Expired keys SHALL be rejected. `APIKey` records SHALL never store plaintext keys. | MUST | Unit test |

### 2.6 Audit Logging — REQ-SFM-AUDIT

| Req ID | Requirement | Priority | Verification |
|:-------|:------------|:---------|:-------------|
| REQ-SFM-AUDIT-001 | Every CRUD operation (store, retrieve, soft-delete) and search operation SHALL generate an `AuditLog` record containing: action type, namespace, coordinate_key, tenant, user_id, ip_address, details (JSON), and timestamp. | MUST | Audit test |
| REQ-SFM-AUDIT-002 | Audit log records SHALL be append-only. No API endpoint SHALL permit modification or deletion of audit log entries. | MUST | Security test |

---

## Section 3: Non-Functional Requirements

### 3.1 Performance

| Req ID | Requirement | Target | Verification |
|:-------|:------------|:-------|:-------------|
| REQ-SFM-NFR-PERF-001 | Memory store and retrieve operations SHALL complete in under 50ms (p50) under normal load. | < 50ms p50 | Performance baseline |
| REQ-SFM-NFR-PERF-002 | Semantic search operations SHALL complete in under 200ms (p99) for collections up to 1M vectors. | < 200ms p99 | Load test |
| REQ-SFM-NFR-PERF-003 | The system SHALL support configurable rate limiting via `SOMA_RATE_LIMIT_MAX` and `SOMA_RATE_LIMIT_WINDOW` environment variables. | Configurable | API test |

### 3.2 Reliability

| Req ID | Requirement | Target | Verification |
|:-------|:------------|:-------|:-------------|
| REQ-SFM-NFR-REL-001 | The system SHALL implement a circuit breaker for external service calls (SomaBrain auth, Milvus) with configurable failure threshold and reset interval. | Configurable | Resilience test |
| REQ-SFM-NFR-REL-002 | The system SHALL degrade gracefully when Milvus is unavailable by falling back to PostgreSQL-based search. | No data loss | Resilience test |
| REQ-SFM-NFR-REL-003 | The system SHALL support health probes (`/healthz`, `/readyz`) for Kubernetes liveness and readiness checks. Liveness SHALL return HTTP 503 if any backend is unhealthy. | 503 on failure | Health test |

### 3.3 Availability

| Req ID | Requirement | Target | Verification |
|:-------|:------------|:-------|:-------------|
| REQ-SFM-NFR-AVL-001 | The system SHALL achieve 99.5% availability measured by `/healthz` success rate. | 99.5% | Monitoring |
| REQ-SFM-NFR-AVL-002 | The system SHALL support horizontal scaling via Kubernetes (Helm chart with configurable replica count). Minimum 3 replicas for HA. | ≥ 3 replicas | Helm validation |
| REQ-SFM-NFR-AVL-003 | Recovery Time Objective (RTO) SHALL be under 15 minutes (container restart + health check). | < 15 min | Operational drill |

### 3.4 Maintainability

| Req ID | Requirement | Target | Verification |
|:-------|:------------|:-------|:-------------|
| REQ-SFM-NFR-MNT-001 | The codebase SHALL contain zero `TODO`, `FIXME`, `HACK`, or `XXX` markers in production code. | 0 markers | Static analysis |
| REQ-SFM-NFR-MNT-002 | All Python code SHALL pass Ruff linting and mypy type checking with zero errors. | 0 errors | CI pipeline |
| REQ-SFM-NFR-MNT-003 | All code SHALL have type annotations on public function signatures. | 100% | mypy enforcement |

---

## Section 4: Interface Requirements

### 4.1 External System Interfaces

| System | Interface | Protocol | Direction | Auth | Detail |
|:-------|:----------|:---------|:----------|:-----|:-------|
| SomaBrain | Auth verification | HTTP GET `/api/v1/auth/verify` | Inbound request | `sbk_*` Bearer token | 3s timeout, returns tenant + scopes |
| SomaAgent01 | Memory API consumer | REST (HTTP) | Inbound request | `sbk_*` or `sfm_*` Bearer | Store, search, graph operations |

### 4.2 Storage Backend Interfaces

| Backend | Interface | Protocol | Port (Standalone) | Port (AAAS) | Purpose |
|:--------|:----------|:---------|:-------------------|:------------|:--------|
| PostgreSQL 15+ | Django ORM | TCP | 10432 | 5432 | Metadata, graph links, audit log |
| Milvus 2.3+ | `pymilvus` gRPC | gRPC | 10530 | 19530 | Vector embeddings, similarity search |
| Redis 7.0+ | Django cache backend | TCP | 10379 | 6379 | Session cache, rate limiting |
| HashiCorp Vault 1.13 | `hvac` HTTP client | HTTP | 10200 | 8200 | Secrets (DB creds, Redis creds) |
| OPA 0.54 | HTTP policy evaluation | HTTP | 10818 | 8181 | Authorization policy decisions |

### 4.3 API Interface Summary

| Endpoint Group | Mount Path | Auth Required | Description |
|:---------------|:-----------|:--------------|:------------|
| Memory CRUD | `/memories` | Yes | Store, retrieve, delete memories |
| Search | `/memories/search` | Yes | Semantic and filtered search |
| Graph | `/graph` | Yes | Link, neighbors, shortest path |
| Health | `/healthz`, `/readyz` | No | Liveness and readiness probes |
| Health (detailed) | `/health` | Yes | Per-service health with tenant stats |
| Metrics | `/metrics` | No | Prometheus-format metrics |
| OpenAPI Schema | `/api/v1/docs` | No | Auto-generated API documentation |

---

## Section 5: Constraints

### 5.1 Technology Constraints

| ID | Constraint | Rationale |
|:---|:-----------|:----------|
| CONSTR-001 | Django ORM only — no SQLAlchemy imports permitted | VIBE coding rules; consistency with Soma stack |
| CONSTR-002 | Django Ninja only — no FastAPI imports permitted | VIBE coding rules; single framework mandate |
| CONSTR-003 | Python 3.12+ required | Type annotation features (PEP 695+), performance improvements |
| CONSTR-004 | Milvus as the sole vector store backend | Operational simplicity; no multi-backend abstraction |
| CONSTR-005 | PostgreSQL as the sole relational database | ArrayField, JSONField, recursive CTE dependencies |
| CONSTR-006 | Zero `TODO`/`FIXME`/`HACK`/`XXX` in production code | VIBE compliance; tech debt tracked externally |

### 5.2 Integration Constraints

| ID | Constraint | Rationale |
|:---|:-----------|:----------|
| CONSTR-007 | SomaBrain `sbk_*` tokens validated via `/api/v1/auth/verify` on port 63996 | Centralized auth for Soma Cognitive Triad |
| CONSTR-008 | Standalone mode binds all requests to `standalone` tenant | Single-tenant simplification for standalone deployment |
| CONSTR-009 | Milvus collections named `sfm_{namespace}` | Naming convention for namespace isolation |

### 5.3 Operational Constraints

| ID | Constraint | Rationale |
|:---|:-----------|:----------|
| CONSTR-010 | All Docker containers must use `cap_drop: [ALL]` and `no-new-privileges: true` | Security hardening (SOMA-SFM-SEC-001) |
| CONSTR-011 | OPA must be configured fail-closed (`SOMA_OPA_FAIL_OPEN = False`) in production | Authorization fails safe |
| CONSTR-012 | Vault KV v2 secrets must be populated before SFM startup | Credential dependency |

---

## Section 6: Requirements Traceability Matrix

| Requirement ID | Test File(s) | Status |
|:---------------|:-------------|:-------|
| REQ-SFM-MEM-001 | `test_end_to_end_memory.py`, `test_deep_integration.py` | VERIFIED |
| REQ-SFM-MEM-002 | `test_end_to_end_memory.py`, `test_sanity_service.py` | VERIFIED |
| REQ-SFM-MEM-003 | `test_end_to_end_memory.py`, `test_deep_integration.py` | VERIFIED |
| REQ-SFM-MEM-004 | `tests/unit/test_models.py` | VERIFIED |
| REQ-SFM-MEM-005 | `test_exception_logging.py`, `test_deep_integration.py` | VERIFIED |
| REQ-SFM-MEM-006 | `tests/unit/test_models.py` | VERIFIED |
| REQ-SFM-SRCH-001 | `test_deep_integration.py`, `test_live_integration.py` | VERIFIED |
| REQ-SFM-SRCH-002 | `test_http_api_coord_validation.py` | VERIFIED |
| REQ-SFM-SRCH-003 | `test_http_api_coord_validation.py` | VERIFIED |
| REQ-SFM-SRCH-004 | `verify_sfm_resilience_e2e.py` | VERIFIED |
| REQ-SFM-SRCH-005 | `test_deep_integration.py` | VERIFIED |
| REQ-SFM-GRAPH-001 | `tests/unit/test_models.py` | VERIFIED |
| REQ-SFM-GRAPH-002 | `test_deep_integration.py` | VERIFIED |
| REQ-SFM-GRAPH-003 | `test_deep_integration.py` | VERIFIED |
| REQ-SFM-GRAPH-004 | Manual verification | PENDING |
| REQ-SFM-MTEN-001 | `test_deep_integration.py`, `test_live_integration.py` | VERIFIED |
| REQ-SFM-MTEN-002 | `test_deep_integration.py` | VERIFIED |
| REQ-SFM-MTEN-003 | `test_http_api_coord_validation.py` | VERIFIED |
| REQ-SFM-MTEN-004 | `test_live_integration.py` | VERIFIED |
| REQ-SFM-AUTH-001 | `test_http_api_coord_validation.py`, `tests/proofs/test_docker_proof.py` | VERIFIED |
| REQ-SFM-AUTH-002 | `test_live_integration.py` | VERIFIED |
| REQ-SFM-AUTH-003 | `tests/unit/test_models.py` | VERIFIED |
| REQ-SFM-AUDIT-001 | `test_exception_logging.py`, `test_deep_integration.py` | VERIFIED |
| REQ-SFM-AUDIT-002 | `tests/unit/test_models.py` (model-level enforcement) | VERIFIED |
| REQ-SFM-NFR-PERF-001 | Performance baseline (pending) | PENDING |
| REQ-SFM-NFR-PERF-002 | Load test (pending) | PENDING |
| REQ-SFM-NFR-PERF-003 | `test_http_api_coord_validation.py` | VERIFIED |
| REQ-SFM-NFR-REL-001 | `verify_sfm_resilience_e2e.py` | VERIFIED |
| REQ-SFM-NFR-REL-002 | `verify_sfm_resilience_e2e.py` | VERIFIED |
| REQ-SFM-NFR-REL-003 | `tests/proofs/test_docker_proof.py` | VERIFIED |
| REQ-SFM-NFR-AVL-001 | Monitoring (runtime) | OPERATIONAL |
| REQ-SFM-NFR-AVL-002 | Helm chart validation | VERIFIED |
| REQ-SFM-NFR-AVL-003 | Operational drill (pending) | PENDING |
| REQ-SFM-NFR-MNT-001 | CI pipeline (Ruff + grep) | VERIFIED |
| REQ-SFM-NFR-MNT-002 | CI pipeline (Ruff + mypy) | VERIFIED |
| REQ-SFM-NFR-MNT-003 | mypy enforcement | VERIFIED |

### Traceability Summary

| Status | Count | Percentage |
|:-------|:------|:-----------|
| VERIFIED | 32 | 91% |
| PENDING | 3 | 9% |
| **Total** | **35** | **100%** |

---

*End of SOMA-SFM-SRS-001 v1.0.0*
