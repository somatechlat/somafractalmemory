# SOMA-SFM-ARCH-001: SomaFractalMemory Architecture Specification

> **Standard**: ISO/IEC 42010 — Systems and Software Engineering — Architecture Description
> **Owner**: SomaTech LAT

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SOMA-SFM-ARCH-001: SomaFractalMemory Architecture Specification |
| Document Identifier | SOMA-SFM-ARCH-001 |
| Version | 2.0.1 |
| Date | 2026-09-28 |
| Status | Approved |
| Author | SomaTech LAT Engineering |
| Approver | CTO, SomaTech LAT |
| Classification | Confidential |
| ISO Reference | ISO/IEC 42010 — Systems and Software Engineering — Architecture Description |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|:--------|:-----|:-------|:------------|
| 1.0.0 | 2025-09-01 | Engineering | Initial architecture specification |
| 1.1.0 | 2025-11-15 | Engineering | Added AAAS deployment mode, OPA integration |
| 2.0.0 | 2026-06-15 | Engineering | Production-ready revision; updated for v0.2.0, added Helm charts, Vault integration, circuit breaker, batch processing |
| 2.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-SFM-ARCH-001` \| case normalised to `Approved` \| prior classification `PROPRIETARY / COMMERCIAL SENSITIVE` normalised to `Confidential`. |

### Distribution

| Recipient | Role | Access Level |
|:----------|:-----|:-------------|
| SomaTech LAT Engineering | Implementation | Full |
| SomaBrain Team | Integration | Sections 2, 8 |
| SomaAgent01 Team | Integration | Sections 2, 6, 8 |
| Operations / SRE | Deployment | Sections 2, 7, 9, 10 |

---

## Section 1: Purpose and Scope

### 1.1 Purpose

SomaFractalMemory (SFM) is the **Storage & Recall** component of the **Soma Cognitive Triad**. It provides distributed long-term memory for autonomous AI agents, enabling persistent vector storage with semantic search across sessions.

SFM implements a **hierarchical memory system** with three tiers:

| Tier | Type | Description |
|:-----|:-----|:------------|
| 1 | **Episodes** | Raw experiences and interactions stored as-is |
| 2 | **Semantic** | Derived facts and structured knowledge |
| 3 | **Summaries** | Aggregated patterns and compressed representations |

### 1.2 Key Capabilities

- **Semantic Search**: 768-dimensional embeddings via Milvus vector store (IVF_FLAT index, COSINE metric)
- **Hierarchical Memory**: Episodic, semantic, and summary memory types with fractal coordinate addressing
- **Multi-Tenancy**: Cryptographic namespace isolation per tenant
- **Graph Operations**: Link memories with typed, weighted edges; shortest-path traversal via PostgreSQL recursive CTE
- **Fractal Organization**: Weighted importance scoring with reservoir-based normalization and configurable decay

### 1.3 Scope

This document describes the software architecture of SomaFractalMemory v0.2.0 as implemented in approximately **5,135 lines of Python** (Django 5.0+ / Django Ninja). It covers:

- Deployment topologies (Standalone and AAAS)
- Layered architecture (API → Service → Data → Storage)
- Core algorithms and data models
- API surface and security architecture
- Integration points with the Soma Cognitive Triad
- Storage backend configuration
- Observability and monitoring

### 1.4 Architectural Context

SFM operates as the third vertex of the **Soma Cognitive Triad**:

```
                    ┌──────────────────┐
                    │    SomaBrain      │
                    │ (Port 63996)      │
                    │ Processing &      │
                    │ Reasoning         │
                    └──────┬───────────┘
                           │ sbk_* token validation
                           │ REST API
                    ┌──────▼───────────┐
                    │ SomaAgent01       │
                    │ (Port 63900)      │
                    │ Orchestration &   │
                    │ Execution         │
                    └──────┬───────────┘
                           │ REST API consumer
                    ┌──────▼───────────┐
                    │ SomaFractalMemory │
                    │ (Port 10101/63901)│
                    │ Storage & Recall  │
                    └──────────────────┘
```

---

## Section 2: Deployment Modes

SFM supports two deployment modes with distinct configurations.

### 2.1 Standalone Mode

**Purpose**: Independent deployment with its own infrastructure stack.

| Parameter | Value |
|:----------|:------|
| **Port** | 10101 |
| **Auth** | Simple bearer token (`SOMA_API_TOKEN`) |
| **Token Validation** | `hmac.compare_digest` (constant-time comparison) |
| **Settings Module** | `somafractalmemory.settings.standalone` |
| **Infrastructure** | Own PostgreSQL, Redis, Milvus, Vault, OPA |
| **Docker Compose** | `infra/standalone/docker-compose.yml` |
| **Helm Chart** | `infra/helm/` (values-local-dev.yaml, values-prod-ha.yaml) |

**Infrastructure Stack (Standalone)**:

| Service | Image | Host Port | Internal Port |
|:--------|:------|:----------|:--------------|
| API | somafractalmemory:latest | 10101 | 10101 |
| PostgreSQL | postgres:15-alpine | 10432 | 5432 |
| Redis | redis:7.2-alpine | 10379 | 6379 |
| Milvus | milvusdb/milvus:v2.3.3 | 10530 | 19530 |
| Vault | hashicorp/vault:1.13.3 | 10200 | 8200 |
| OPA | openpolicyagent/opa:0.54.0 | 10818 | 8181 |
| Etcd | quay.io/coreos/etcd:v3.5.5 | — | 2379 |
| MinIO | minio/minio | — | 9000 |

### 2.2 AAAS Mode (Agent-as-a-Service)

**Purpose**: Integrated deployment as part of the Soma Cognitive Triad.

| Parameter | Value |
|:----------|:------|
| **Port** | 63901 |
| **Auth** | SomaBrain `sbk_*` token validation via `/api/v1/auth/verify` |
| **Auth Fallback** | Local `sfm_*` API keys, `SOMA_API_TOKEN` simple bearer |
| **Settings Module** | `somafractalmemory.settings.standalone` (shared) |
| **Integration** | SomaAgent01 (port 63900, REST consumer), SomaBrain (port 63996, auth provider) |

**Auth Flow (AAAS)**:

```
Client Request
  │
  ├─ sfm_* prefix → Local validation (SHA-256 key hash lookup)
  │
  ├─ sbk_* prefix → SomaBrain central auth
  │     GET http://somabrain:63996/api/v1/auth/verify
  │     Authorization: Bearer sbk_*
  │     timeout: 3.0s (hardened)
  │
  └─ SOMA_API_TOKEN → Simple bearer (hmac.compare_digest)
```

---

## Section 3: Architecture

### 3.1 Layered Architecture

SFM follows a strict three-layer architecture:

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                             │
│  Django Ninja Routers (memory, search, graph, health)   │
│  Authentication: StandaloneAuth / APIKeyAuth / MultiAuth│
│  Rate Limiting: Django Middleware                        │
├─────────────────────────────────────────────────────────┤
│                   Service Layer                          │
│  MemoryService: CRUD, search, stats, health_check       │
│  GraphService: links, neighbors, shortest_path, export  │
│  Factory: get_memory_service(), get_graph_service()     │
├─────────────────────────────────────────────────────────┤
│                    Data Layer                            │
│  Django ORM Models: Memory, GraphLink, VectorEmbedding, │
│                     MemoryNamespace, AuditLog            │
│  Milvus Client: MilvusVectorStore (IVF_FLAT, COSINE)    │
├─────────────────────────────────────────────────────────┤
│                 Storage Backends                         │
│  PostgreSQL 15+  │  Milvus 2.3+  │  Redis 7.0+          │
│  (metadata)      │  (vectors)    │  (cache)              │
│  Vault (KV v2)   │  OPA (authZ)  │                      │
└─────────────────────────────────────────────────────────┘
```

### 3.2 API Layer

**Framework**: Django Ninja (OpenAPI 3.0, auto-generated schema)

**Router Registration** (from `somafractalmemory/api/core.py`):

| Mount Path | Router | Tags | Auth |
|:-----------|:-------|:-----|:-----|
| `/memories` | `search_router` | memories | StandaloneAuth |
| `/memories` | `memory_router` | memories | StandaloneAuth |
| `/graph` | `graph_router` | graph | StandaloneAuth |
| `` | `health_router` | system | Mixed (some open, some token) |

**Exception Handling**:
- `HttpError` → structured JSON with status code
- `Exception` → generic 500 with `ErrorCode.INTERNAL_ERROR` message

### 3.3 Service Layer

**MemoryService** (`somafractalmemory/admin/core/services.py`):

- `store(coordinate, payload, memory_type, tenant, metadata)` → Memory
- `retrieve(coordinate, tenant)` → dict | None
- `delete(coordinate, tenant)` → bool (soft delete)
- `search(query, top_k, offset, memory_type, tenant, filters)` → list[dict]
- `stats()` → dict (total, episodic, semantic counts)
- `health_check()` → dict (kv_store, vector_store, graph_store)

**GraphService** (`somafractalmemory/admin/core/services.py`):

- `add_link(from_coord, to_coord, link_data)` → GraphLink
- `get_neighbors(coord, link_type, limit, offset, tenant)` → list[dict]
- `find_shortest_path(from_coord, to_coord, link_type, tenant, max_depth)` → list | None
- `export_graph(path)` → None (streaming JSON export, O(1) memory)

### 3.4 Data Layer

All persistence through Django ORM models. No raw SQL except for the graph shortest-path recursive CTE. Indexes configured at the model level (see Section 5).

### 3.5 Storage Backends

See Section 9 for detailed configuration.

---

## Section 4: Core Algorithms

### 4.1 Hash-Based Deterministic Embedding

**Location**: `somafractalmemory/admin/core/services.py:27-42`

```
Algorithm: HashEmbedder
Input:     text (str), dim (int, default=768)
Output:    vector (list[float], length=dim)

For i in 0..dim:
    digest = SHA256(f"{text}|{i}")
    val = uint32(digest[0:4])  # big-endian, unsigned
    vec[i] = (val % 2,000,000) / 1,000,000 - 1.0  # map to [-1, 1]

norm = L2_norm(vec)
return vec / norm  # unit vector for cosine similarity
```

**Properties**:
- Deterministic: same text always produces the same vector
- No external ML model dependencies
- L2-normalized for cosine similarity compatibility
- **Limitation**: Not semantically meaningful; suitable for exact-match and development, not production semantic search

### 4.2 Coordinate-Based Memory Addressing

Memories are addressed by a **fractal coordinate** — a tuple of floats (e.g., `(1.0, 2.0, 3.0)`).

```
coord_key = ",".join(str(c) for c in coordinate)
```

The `coordinate_key` string is used for:
- Database lookups (indexed column)
- Milvus vector-to-memory mapping
- Graph link endpoints
- Unique constraint: `(namespace, tenant, coordinate_key)`

### 4.3 Graph Shortest Path (PostgreSQL Recursive CTE)

**Location**: `somafractalmemory/admin/core/services.py:441-539`

```
WITH RECURSIVE path_search AS (
    -- Base: direct links from source
    SELECT to_coordinate_key, path_coords, depth=1
    FROM sfm_graph_links
    WHERE from_coordinate_key = <source>

    UNION ALL

    -- Recursive: follow links, avoiding cycles
    SELECT l.to_coordinate_key, ps.path_coords || l.to_coordinate, depth+1
    FROM sfm_graph_links l
    JOIN path_search ps ON l.from_coordinate_key = ps.current_key
    WHERE NOT l.to_coordinate_key = ANY(ps.visited_keys)
      AND ps.depth < max_depth
)
SELECT path_coords FROM path_search
WHERE current_key = <target>
ORDER BY depth ASC LIMIT 1
```

**Parameters**:
- `max_depth`: configurable (default 5), prevents runaway traversal
- `link_type`: optional filter
- Cycle detection via `visited_keys` array

### 4.4 Importance

`Memory.importance` is a caller-supplied float used for ORM fallback ordering
(`order_by("-importance", "-created_at")`). There is no reservoir, winsorized
logistic or other normalization algorithm in this tree. The
`SOMA_IMPORTANCE_*` knobs that once documented one were deleted: a tunable
with no reader is a lie.

### 4.5 Decay and Pruning

Not implemented. `Memory.access_count` and `Memory.last_accessed` are recorded
on retrieve; nothing computes a decay score from them and there is no prune
command or scheduler in this codebase. The `SOMA_DECAY_*` and
`SOMA_MAX_MEMORY_SIZE` knobs were deleted with the absent feature. Scheduling
and eviction are future work, not configuration.

---

## Section 5: Data Models

All models defined in `somafractalmemory/admin/core/models.py`.

### 5.1 Memory (`sfm_memories`)

| Field | Type | Indexed | Description |
|:------|:-----|:--------|:------------|
| `id` | UUID | PK | Primary key |
| `namespace` | CharField(255) | Yes | Isolation namespace |
| `coordinate` | ArrayField(Float) | — | Fractal coordinate vector |
| `coordinate_key` | CharField(512) | Yes | Stringified coordinate |
| `memory_type` | CharField(20) | — | `episodic` or `semantic` |
| `payload` | JSONField | GIN | Memory content |
| `metadata` | JSONField | — | Additional metadata |
| `tenant` | CharField(255) | Yes | Tenant identifier |
| `importance` | FloatField | Yes | Importance score |
| `access_count` | IntegerField | — | Read counter |
| `last_accessed` | DateTimeField | — | Last access timestamp |
| `is_deleted` | BooleanField | Yes | Soft delete flag |
| `deleted_at` | DateTimeField | — | Soft delete timestamp |
| `created_at` | DateTimeField | Yes | Creation timestamp |
| `updated_at` | DateTimeField | — | Last update timestamp |

**Constraints**:
- `UniqueConstraint(namespace, tenant, coordinate_key)` — unique_namespace_tenant_coordinate

**Indexes**:
- `(namespace, coordinate_key)`
- `(namespace, memory_type)`
- `(tenant, namespace)`
- GIN on `payload` (sfm_memories_payload_gin)

### 5.2 GraphLink (`sfm_graph_links`)

| Field | Type | Indexed | Description |
|:------|:-----|:--------|:------------|
| `id` | UUID | PK | Primary key |
| `namespace` | CharField(255) | Yes | Isolation namespace |
| `from_coordinate` | ArrayField(Float) | — | Source coordinate |
| `from_coordinate_key` | CharField(512) | Yes | Source key |
| `to_coordinate` | ArrayField(Float) | — | Target coordinate |
| `to_coordinate_key` | CharField(512) | Yes | Target key |
| `link_type` | CharField(100) | Yes | Relationship type |
| `strength` | FloatField | — | Link strength (default 1.0) |
| `metadata` | JSONField | — | Link metadata |
| `tenant` | CharField(255) | Yes | Tenant identifier |
| `created_at` | DateTimeField | — | Creation timestamp |

**Constraints**:
- `UniqueConstraint(namespace, tenant, from_coordinate_key, to_coordinate_key, link_type)` — unique_graph_link_tenant

### 5.3 VectorEmbedding (`sfm_vector_embeddings`)

| Field | Type | Indexed | Description |
|:------|:-----|:--------|:------------|
| `id` | UUID | PK | Primary key |
| `memory` | ForeignKey(Memory) | — | Parent memory (CASCADE delete) |
| `collection_name` | CharField(255) | Yes | Milvus collection name |
| `milvus_id` | BigIntegerField | Yes | Milvus internal ID |
| `vector_dim` | IntegerField | — | Vector dimensionality (768) |
| `model_name` | CharField(255) | — | Embedding model identifier |
| `created_at` | DateTimeField | — | Creation timestamp |

### 5.4 MemoryNamespace (`sfm_namespaces`)

| Field | Type | Description |
|:------|:-----|:------------|
| `id` | UUID | Primary key |
| `name` | CharField(255) | Unique namespace name |
| `tenant` | CharField(255) | Tenant identifier |
| `description` | TextField | Namespace description |
| `config` | JSONField | Namespace-specific configuration |
| `total_memories` | IntegerField | Cached total count |
| `episodic_count` | IntegerField | Cached episodic count |
| `semantic_count` | IntegerField | Cached semantic count |

### 5.5 AuditLog (`sfm_audit_log`)

| Field | Type | Indexed | Description |
|:------|:-----|:--------|:------------|
| `id` | UUID | PK | Primary key |
| `action` | CharField(20) | — | `create`, `read`, `update`, `delete`, `search` |
| `namespace` | CharField(255) | Yes | Operation namespace |
| `coordinate_key` | CharField(512) | — | Target coordinate |
| `tenant` | CharField(255) | Yes | Tenant identifier |
| `user_id` | CharField(255) | — | Authenticated user |
| `ip_address` | GenericIPAddress | — | Client IP |
| `details` | JSONField | — | Operation details |
| `timestamp` | DateTimeField | Yes | Operation timestamp |

---

## Section 6: API Surface

### 6.1 Memory Operations

| Method | Path | Auth | Description |
|:-------|:-----|:-----|:------------|
| `POST /memories` | Body: `{coord, payload, memory_type}` | Bearer | Store a memory |
| `GET /memories/{coord}` | Path: coordinate | Bearer | Retrieve a memory |
| `DELETE /memories/{coord}` | Path: coordinate | Bearer | Soft delete a memory |

### 6.2 Search

| Method | Path | Auth | Description |
|:-------|:-----|:-----|:------------|
| `POST /memories/search` | Body: `{query, top_k, offset, filters}` | Bearer | Semantic search (POST) |
| `GET /memories/search?query=...&top_k=5` | Query params | Bearer | Semantic search (GET) |

### 6.3 Graph Operations

| Method | Path | Auth | Description |
|:-------|:-----|:-----|:------------|
| `POST /graph/link` | Body: `{from_coord, to_coord, link_type, strength}` | Bearer | Create graph link |
| `GET /graph/neighbors?coord=...` | Query params | Bearer | Get neighbor links |
| `GET /graph/path?from=...&to=...` | Query params | Bearer | Shortest path |

### 6.4 System / Health

| Method | Path | Auth | Description |
|:-------|:-----|:-----|:------------|
| `GET /healthz` | — | None | Liveness probe (returns 503 if unhealthy) |
| `GET /readyz` | — | None | Readiness probe |
| `GET /health/basic` | — | None | Basic health (all backends) |
| `GET /health` | — | Bearer | Detailed health with per-tenant stats |
| `GET /stats` | — | None | Memory statistics |
| `GET /metrics` | — | None | Prometheus metrics |
| `GET /ping` | — | None | Simple liveness ping |
| `GET /` | — | None | Root status |

---

## Section 7: Security Architecture

### 7.1 Authentication

**Standalone Mode**:
- `StandaloneAuth` (Django Ninja `HttpBearer`)
- Validates `SOMA_API_TOKEN` using `hmac.compare_digest` (constant-time comparison)
- Prevents timing attacks on token validation
- All authenticated requests bound to `standalone` tenant

**AAAS Mode**:
- `MultiAuth` composite: `APIKeyAuth` → `SimpleTokenAuth` fallback
- `sfm_*` prefix: Local SHA-256 hash lookup against `APIKey` model
- `sbk_*` prefix: Remote validation via SomaBrain (`GET /api/v1/auth/verify`, 3s timeout)
- `SOMA_API_TOKEN`: Simple bearer with `hmac.compare_digest`

### 7.2 Authorization

**Bearer token (`SOMA_API_TOKEN`)** via `StandaloneAuth`, compared with
`hmac.compare_digest`. Namespace and tenant checks are fail-closed in
`api/utils.py`. There is no OPA client in this tree; `SOMA_OPA_*` knobs were
deleted with the absent gate. Policy enforcement belongs where the gate is.

### 7.3 Secrets Management

**HashiCorp Vault (KV v2)**:
- Secrets stored at `somafractalmemory/credentials`, `somafractalmemory/database`
- Client: `hvac` library, singleton with `@lru_cache`
- Token delivered as a file (`VAULT_TOKEN_FILE`) — never from ENV (Rule 164)
- Credentials resolved once in `settings.django_core._credential`: Vault first,
  the deployment's injection channel second, never a code default
- A Vault failure raises. It is not a graceful fallback and never falls
  through to ENV.

### 7.4 Docker Hardening

From `infra/standalone/docker-compose.yml` (API container):

```yaml
cap_drop: [ "ALL" ]
security_opt:
  - no-new-privileges:true
read_only: false  # Django needs write access to /tmp
```

### 7.5 Network Isolation

- Standalone: Dedicated bridge network `somafractalmemory-standalone-net`
- Shared network: Optional `docker-compose.shared-network.yml` for Soma Triad integration via `soma-stack-net`

---

## Section 8: Integration Points

### 8.1 SomaBrain Integration

| Aspect | Detail |
|:-------|:-------|
| **URL** | `http://somabrain:63996/api/v1/auth/verify` |
| **Protocol** | HTTP GET with `Authorization: Bearer sbk_*` |
| **Timeout** | 3.0 seconds (hardened against thread exhaustion) |
| **Response** | `{tenant_slug, tenant_id, api_key_id, scopes, is_test}` |
| **Failure Mode** | Returns `None` (auth denied), logs error |
| **Source** | `somafractalmemory/admin/aaas/auth.py:130-168` |

### 8.2 SomaAgent01 Integration

| Aspect | Detail |
|:-------|:-------|
| **Role** | REST API consumer |
| **Port** | 63900 |
| **Protocol** | HTTP calls to SFM API |
| **Auth** | Uses `sbk_*` tokens validated via SomaBrain |

---

## Section 9: Storage Configuration

### 9.1 PostgreSQL

| Table | Purpose | Key Indexes |
|:------|:--------|:------------|
| `sfm_memories` | Memory storage | GIN on payload, composite (namespace, coordinate_key) |
| `sfm_graph_links` | Graph edges | Composite (namespace, from/to_coordinate_key) |
| `sfm_vector_embeddings` | Vector metadata | (collection_name, milvus_id) |
| `sfm_namespaces` | Namespace config | Unique name |
| `sfm_audit_log` | Operation audit | (namespace, action, timestamp), (tenant, timestamp) |

**Django Migrations**: Applied automatically at container startup.

### 9.2 Milvus

| Parameter | Value |
|:----------|:------|
| **Version** | 2.3.3 |
| **Index Type** | IVF_FLAT |
| **Metric** | COSINE |
| **nlist** | 128 |
| **Dimension** | 768 |
| **Collection Naming** | `sfm_{namespace}` |
| **Memory Limit** | 4GB (Docker resource limit) |
| **Dependencies** | Etcd (metadata), MinIO (object storage) |

### 9.3 Redis

| Parameter | Value |
|:----------|:------|
| **Version** | 7.2-alpine |
| **Purpose** | Cache layer |
| **Port** | 6379 (internal), 10379 (host) |
| **Auth** | Optional password via Vault |

### 9.4 HashiCorp Vault

| Parameter | Value |
|:----------|:------|
| **Version** | 1.13.3 |
| **Engine** | KV v2 |
| **Mount Point** | `somafractalmemory` |
| **Secrets** | `data/database`, `data/redis` |
| **Cache TTL** | 300 seconds |
| **Init Container** | Auto-mounts KV v2 and writes initial secrets |

---

## Section 10: Observability

### 10.1 Prometheus Metrics

**Endpoint**: `GET /metrics` (unauthenticated)

Exposed via `prometheus_client.generate_latest()`.

### 10.2 Structured Logging

**Library**: `structlog` (with fallback to standard `logging`)

**Configuration** (from `somafractalmemory/admin/common/utils/logger.py`):

| Processor | Description |
|:----------|:------------|
| `add_log_level` | Injects log level |
| `add_logger_name` | Injects logger name |
| `TimeStamper(fmt="iso")` | ISO 8601 timestamps |
| `StackInfoRenderer` | Stack trace rendering |
| `format_exc_info` | Exception formatting |
| `JSONRenderer` / `ConsoleRenderer` | JSON in production, console in dev |

**Log Levels**: Configurable via `SOMA_LOG_LEVEL` (default: `INFO`)

### 10.3 Health Probes

| Probe | Endpoint | Fail Behavior | Auth |
|:------|:---------|:-------------|:-----|
| Liveness | `/healthz` | 503 if any backend unhealthy | None |
| Readiness | `/readyz` | Returns current status | None |
| Detailed | `/health` | Per-service latencies, tenant stats | Bearer |

### 10.4 Audit Logging

Every CRUD and search operation generates an `AuditLog` record with:
- Action type (create, read, update, delete, search)
- Namespace, coordinate, tenant
- Client IP and user ID (when available)
- Operation details as JSON
- Auto-timestamped

---

## Appendix A: Configuration Reference

Every tunable is declared once on the `TUNABLES` registry in
`somafractalmemory/settings/model.py` and read through `resolve_setting` /
`service_url` / `milvus_uri`. A key with no reader is deleted, not documented.

| Category | Key Settings | Reader |
|:---------|:-------------|:-------|
| Database | `SOMA_DB_NAME`, `SOMA_DB_HOST`, `SOMA_DB_PORT` | `settings.django_core.DATABASES` |
| Database credentials | `SOMA_DB_USER`, `SOMA_DB_PASSWORD` | `django_core._credential` (Vault first) |
| Redis | `SOMA_REDIS_HOST/PORT/DB/PASSWORD` | `api/routers/health.py` |
| Milvus | `SOMA_MILVUS_HOST/PORT/TIMEOUT_S` | `milvus_vector.py`, `health.py` |
| Milvus index | `SOMA_SIMILARITY_METRIC`, `SOMA_MILVUS_NLIST`, `SOMA_MILVUS_NPROBE` | `milvus_vector.py` |
| Vault | `SOMA_VAULT_URL` (bootstrap: `SOMA_VAULT_ADDR`/`VAULT_ADDR`) | `vault_client._vault_addr` |
| Memory | `SOMA_MEMORY_NAMESPACE`, `SOMA_TEST_MEMORY_NAMESPACE`, `SOMA_VECTOR_DIM` | `api/core.py`, `health.py`, `services.py` |
| Search | `SOMA_SEARCH_CANDIDATE_MULTIPLIER`, `SOMA_HASH_EMBEDDING_PENALTY` | `services.py` |
| Observability | `SOMA_LOG_LEVEL`, `SOMA_LOG_JSON` | `admin/common/utils/logger.py` |
| Probes | `SOMA_PROBE_TIMEOUT_S` | `api/routers/health.py` |
| Backup | `SOMA_BACKUP_DIR`, `SOMA_MEMORY_DATA_DIR`, `SOMA_S3_BUCKET` | `scripts/backup_restore.py` |

Credentials with no code default (fail-closed, Rule 91): `SOMA_SECRET_KEY`,
`SOMA_DB_USER`, `SOMA_DB_PASSWORD`, `SOMA_ALLOWED_HOSTS`, `SOMA_API_TOKEN`.
AuthZ is the bearer token via `StandaloneAuth`; there is no OPA client, circuit
breaker, rate limiter, CORS middleware or body-size cap in this tree.

---

*End of SOMA-SFM-ARCH-001 v2.0.0*
