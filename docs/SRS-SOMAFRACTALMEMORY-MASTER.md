# SomaFractalMemory — Master Technical Specification
## ISO/IEC 25010 Compliant Documentation

| Document ID | SRS-SOMAFRACTALMEMORY-MASTER-001 |
|-------------|----------------------------------|
| Version | 1.0.0 |
| Date | 2026-01-02 |
| Status | APPROVED |
| Classification | Internal - Engineering |

---

# TABLE OF CONTENTS

1. [Scope](#1-scope)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Models](#3-data-models)
4. [Services Layer](#4-services-layer)
5. [API Reference](#5-api-reference)
6. [Configuration](#6-configuration)
7. [Migration Audit](#7-migration-audit)
8. [Integration](#8-integration)

---

# 1. SCOPE

## 1.1 Purpose
Complete technical specification for SomaFractalMemory, the coordinate-based storage layer of the SOMA stack.

## 1.2 System Overview
- **Project:** SomaFractalMemory
- **Framework:** Django 5.1 + Django Ninja 1.3
- **Database:** PostgreSQL (ArrayField, JSONField)
- **Vector Store:** Milvus

## 1.3 Compliance Status
| Metric | Value |
|--------|-------|
| SQLAlchemy imports | **0** |
| FastAPI imports | **0** |
| TODO comments | **0** |
| VIBE Compliance | **100%** |
| Total Files | 53 |

---

# 2. ARCHITECTURE OVERVIEW

## 2.1 Project Structure

```
somafractalmemory/
├── somafractalmemory/                 # Python package
│   ├── api/                           # Django Ninja API routers + schema
│   ├── admin/
│   │   ├── core/                      # ORM models + services (source of truth)
│   │   └── aaas/                      # API keys + usage tracking
│   ├── config/                        # Django URL mount + WSGI
│   ├── settings/                      # Settings profiles (default + standalone)
│   └── services.py                    # Compatibility re-exports for MemoryService/GraphService
├── infra/                             # Docker/K8s/Helm
├── scripts/                           # Ops scripts
├── tests/                             # Test suite
└── manage.py                          # Django entry point
```

## 2.2 Port Namespace

| Service | Port |
|---------|------|
| API | 10101 |

---

# 3. DATA MODELS

## 3.1 Memory Model

```python
class Memory(models.Model):
    id = models.UUIDField(primary_key=True)
    namespace = models.CharField(max_length=255, db_index=True)
    coordinate = ArrayField(models.FloatField())  # PostgreSQL array
    coordinate_key = models.CharField(max_length=512)
    memory_type = models.CharField(choices=["episodic", "semantic"])
    payload = models.JSONField()
    metadata = models.JSONField()
    tenant = models.CharField(max_length=255, db_index=True)
    importance = models.FloatField(default=0.0, db_index=True)
    access_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## 3.2 GraphLink Model

```python
class GraphLink(models.Model):
    id = models.UUIDField(primary_key=True)
    namespace = models.CharField(max_length=255, db_index=True)
    from_coordinate = ArrayField(models.FloatField())
    to_coordinate = ArrayField(models.FloatField())
    link_type = models.CharField(max_length=100, default="related")
    strength = models.FloatField(default=1.0)
    metadata = models.JSONField()
    tenant = models.CharField(max_length=255, db_index=True)
```

## 3.3 VectorEmbedding Model

```python
class VectorEmbedding(models.Model):
    id = models.UUIDField(primary_key=True)
    memory = models.ForeignKey(Memory, on_delete=models.CASCADE)
    collection_name = models.CharField(max_length=255)
    milvus_id = models.BigIntegerField(null=True)  # Milvus reference
    vector_dim = models.IntegerField(default=768)
    model_name = models.CharField(default="microsoft/codebert-base")
```

## 3.4 Supporting Models

- `MemoryNamespace` - Namespace configuration and statistics
- `AuditLog` - CRUD operation compliance logging

---

# 4. SERVICES LAYER

## 4.1 MemoryService

| Method | Purpose |
|--------|---------|
| `store(key, payload, memory_type)` | Create/update memory |
| `retrieve(namespace, coordinate)` | Fetch by coordinate |
| `search(query, top_k)` | Text + vector search |
| `delete(namespace, coordinate)` | Soft delete |
| `stats(namespace)` | Aggregate statistics |

## 4.2 GraphService

| Method | Purpose |
|--------|---------|
| `add_link(from_coord, to_coord, link_type)` | Create relationship |
| `get_neighbors(coord, depth)` | Fetch connected nodes |
| `find_shortest_path(start, end)` | BFS pathfinding |

---

# 5. API REFERENCE

## 5.1 Endpoint Categories

| Router | Purpose |
|--------|---------|
| `/api/memories/` | Memory CRUD |
| `/api/memories/search` | Semantic search |
| `/api/graph/` | Graph operations |
| `/api/health/` | Health probes |

---

# 6. CONFIGURATION

## 6.1 Environment Variables

| Variable | Purpose |
|----------|---------|
| `SFM_DATABASE_URL` | PostgreSQL DSN |
| `SFM_MILVUS_HOST` | Milvus host |
| `SFM_MILVUS_PORT` | Milvus port |
| `SFM_SECRET_KEY` | Django secret |

---

# 7. MIGRATION AUDIT

## 7.1 Compliance Matrix

| Category | Files | SQLAlchemy | FastAPI | TODOs | Score |
|----------|-------|------------|---------|-------|-------|
| somafractalmemory/* | 25 | 0 | 0 | 0 | 100% |
| common/* | 10 | 0 | 0 | 0 | 100% |
| tests/* | 18 | 0 | 0 | 0 | 100% |
| **TOTAL** | **53** | **0** | **0** | **0** | **100%** |

## 7.2 Action Items

**NO MIGRATION REQUIRED** - 100% Django-compliant.

---

# 8. INTEGRATION

## 8.1 SomaBrain → SomaFractalMemory

```python
# somabrain/memory_client.py
self._endpoint = settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT
response = self._http_client.post(f"{self._endpoint}/memories", json={...})
```

---

**END OF DOCUMENT**

*SRS-SOMAFRACTALMEMORY-MASTER-001 v1.0.0*
