# Architecture

This document describes the architecture of SomaFractalMemory.

## System Overview

SomaFractalMemory is a fractal memory system that stores and retrieves data using coordinate-based addressing. The system is built entirely on Django and Django Ninja.

```
┌─────────────────────────────────────────────────────────────┐
│                        Clients                               │
│                    (HTTP Requests)                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Django + gunicorn                          │
│                   (WSGI Server)                              │
│                   Port: 9595                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Django Ninja API                           │
│              (Request Routing & Validation)                  │
├──────────────┬──────────────┬──────────────┬───────────────┤
│    Health    │   Memory     │   Search     │    Graph      │
│   Router     │   Router     │   Router     │   Router      │
└──────────────┴──────────────┴──────────────┴───────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                              │
│              (MemoryService - Business Logic)                │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Redis     │  │    Milvus    │
│  (Django ORM)│  │   (Cache)    │  │  (Vectors)   │
│  Port: 5432  │  │  Port: 6379  │  │ Port: 19530  │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Component Details

### API Layer

The API is built with Django Ninja, which provides:
- Automatic OpenAPI schema generation
- Pydantic-based request/response validation
- Type-safe route handlers

**Location**: `somafractalmemory/api/`

| File | Purpose |
|------|---------|
| `core.py` | API initialization, dependencies |
| `schemas.py` | Pydantic models for requests/responses |
| `messages.py` | Centralized i18n message strings |
| `routers/health.py` | Health check endpoints |
| `routers/memory.py` | Memory CRUD operations |
| `routers/search.py` | Vector search endpoints |
| `routers/graph.py` | Graph traversal endpoints |

### Service Layer

Business logic is centralized in the service layer.

**Location**: `somafractalmemory/services.py`

The `MemoryService` class provides:
- `store()` - Store a memory with coordinate addressing
- `retrieve()` - Fetch memory by coordinate
- `delete()` - Remove a memory
- `search()` - Vector similarity search
- `health_check()` - Backend health status
- `stats()` - Memory statistics

### Data Layer

All database access uses Django ORM.

**Location**: `somafractalmemory/models.py`

| Model | Table | Description |
|-------|-------|-------------|
| `Memory` | `sfm_memories` | Memory storage |
| `GraphLink` | `sfm_graph_links` | Graph relationships |
| `VectorEmbedding` | `sfm_vector_embeddings` | Vector metadata |
| `MemoryNamespace` | `sfm_namespaces` | Namespace tracking |
| `AuditLog` | `sfm_audit_log` | Audit trail |

### Configuration

Django settings handle all configuration.

**Location**: `somafractalmemory/settings.py`

Key configurations:
- Database connection (PostgreSQL)
- Cache backend (Redis)
- Installed apps
- Middleware
- Logging

## Request Flow

### Store Memory

```
1. Client POST /memories
   └── Request body: {coord, payload, memory_type}

2. Django Ninja validates request
   └── Pydantic schema: MemoryStoreRequest

3. Memory router handles request
   └── routers/memory.py:store_memory()

4. Service layer processes
   └── services.py:MemoryService.store()

5. Django ORM persists to PostgreSQL
   └── models.py:Memory.objects.create()

6. Response returned
   └── {coord, memory_type}
```

### Retrieve Memory

```
1. Client GET /memories/{coord}

2. Memory router parses coordinate
   └── Parse "1.0,2.0,3.0" → (1.0, 2.0, 3.0)

3. Service layer retrieves
   └── MemoryService.retrieve(coordinate)

4. Django ORM queries PostgreSQL
   └── Memory.objects.filter(coordinate_key=...)

5. Response with full memory data
   └── {coordinate, payload, memory_type, ...}
```

## Database Schema

### sfm_memories

```sql
CREATE TABLE sfm_memories (
    id UUID PRIMARY KEY,
    namespace VARCHAR(255) NOT NULL,
    coordinate DOUBLE PRECISION[] NOT NULL,
    coordinate_key VARCHAR(512) NOT NULL,
    payload JSONB NOT NULL,
    memory_type VARCHAR(20) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    importance DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    tenant VARCHAR(255) NOT NULL DEFAULT 'default',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Indexes
CREATE UNIQUE INDEX ON sfm_memories(namespace, coordinate_key);
CREATE INDEX ON sfm_memories(tenant, namespace);
CREATE INDEX ON sfm_memories(memory_type);
```

### sfm_graph_links

```sql
CREATE TABLE sfm_graph_links (
    id UUID PRIMARY KEY,
    namespace VARCHAR(255) NOT NULL,
    from_coordinate DOUBLE PRECISION[] NOT NULL,
    from_coordinate_key VARCHAR(512) NOT NULL,
    to_coordinate DOUBLE PRECISION[] NOT NULL,
    to_coordinate_key VARCHAR(512) NOT NULL,
    link_type VARCHAR(100) NOT NULL,
    strength DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    metadata JSONB NOT NULL DEFAULT '{}',
    tenant VARCHAR(255) NOT NULL DEFAULT 'default',
    created_at TIMESTAMPTZ NOT NULL
);

-- Indexes
CREATE UNIQUE INDEX ON sfm_graph_links(namespace, from_coordinate_key, to_coordinate_key, link_type);
CREATE INDEX ON sfm_graph_links(namespace, from_coordinate_key);
CREATE INDEX ON sfm_graph_links(namespace, to_coordinate_key);
CREATE INDEX ON sfm_graph_links(link_type);
```

## Service Dependencies

### PostgreSQL

- **Purpose**: Primary data storage
- **Tables**: All memory and graph data
- **Connection**: Django ORM via psycopg2

### Redis

- **Purpose**: Caching and rate limiting
- **Usage**: Session cache, query cache
- **Connection**: redis-py client

### Milvus

- **Purpose**: Vector similarity search
- **Usage**: Semantic memory search
- **Connection**: pymilvus client

### etcd

- **Purpose**: Milvus metadata storage
- **Usage**: Internal to Milvus cluster

### MinIO

- **Purpose**: Milvus object storage
- **Usage**: Large vector data storage

## Security

### Authentication

Bearer token authentication via `Authorization` header:

```
Authorization: Bearer <token>
```

Token is validated in each router's `_check_auth()` function.

### Multi-tenancy

All data is isolated by tenant:
- `X-Soma-Tenant` header sets tenant context
- All queries filter by `tenant` field
- Default tenant: "default"

## Performance

### Connection Pooling

PostgreSQL connections are pooled by Django's connection handler.

### Caching

Redis provides:
- Query result caching
- Rate limit counters
- Session storage

### Worker Configuration

gunicorn runs with:
- 2 workers (configurable via `GUNICORN_WORKERS`)
- 2 threads per worker
- 120 second timeout
- 1000 max requests per worker (recycling)
