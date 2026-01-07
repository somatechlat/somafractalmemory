---
inclusion: always
---

# SomaFractalMemory Project Overview

## What This Is

SomaFractalMemory is an enterprise-grade agentic memory system for AI applications. It provides:

- **Coordinate-based memory storage** using fractal addressing
- **Multi-backend architecture**: PostgreSQL (canonical), Redis (cache), Milvus (vectors)
- **Semantic graph operations** via NetworkX
- **Memory decay and lifecycle management**
- **REST API** on port 10101 (FastAPI + Uvicorn)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP API (FastAPI)                       │
│                      Port 10101                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              SomaFractalMemoryEnterprise                    │
│                     (core.py)                               │
└─────────────────────────────────────────────────────────────┘
        │                   │                    │
        ▼                   ▼                    ▼
┌───────────────┐  ┌────────────────┐  ┌─────────────────┐
│   KV Store    │  │  Vector Store  │  │   Graph Store   │
│ (Postgres +   │  │   (Milvus)     │  │  (NetworkX)     │
│   Redis)      │  │                │  │                 │
└───────────────┘  └────────────────┘  └─────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `somafractalmemory/core.py` | Main `SomaFractalMemoryEnterprise` class |
| `somafractalmemory/factory.py` | `create_memory_system()` factory function |
| `somafractalmemory/http_api.py` | FastAPI routes |
| `somafractalmemory/serialization.py` | JSON-first serialization |
| `somafractalmemory/interfaces/` | Abstract interfaces (IKeyValueStore, IVectorStore, IGraphStore) |
| `somafractalmemory/implementations/` | Concrete backends (Redis, Postgres, Milvus, NetworkX) |
| `common/config/settings.py` | Centralized Pydantic settings |

## Memory Types

- `episodic` - Event-based memories with temporal context
- `semantic` - Factual/conceptual knowledge

## Configuration

All configuration flows through `common/config/settings.py` using Pydantic. Key env vars:

- `SOMA_API_TOKEN` - API authentication token
- `POSTGRES_URL` - PostgreSQL connection string
- `REDIS_HOST` / `REDIS_PORT` - Redis connection
- `SOMA_MILVUS_HOST` / `SOMA_MILVUS_PORT` - Milvus vector DB
- `SOMA_FORCE_HASH_EMBEDDINGS` - Use deterministic hash embeddings (dev/test)
