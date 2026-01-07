---
inclusion: always
---

# Infrastructure Guide

## Local Development Stack

Start all services:
```bash
docker compose --profile core up -d
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| API | 10101 | FastAPI HTTP server |
| PostgreSQL | 5433 | Canonical KV store |
| Redis | 6379/6381 | Cache layer + locks |
| Milvus | 19530 | Vector similarity search |

## Health Checks

```bash
# API health
curl http://127.0.0.1:10101/healthz

# Full health with auth
curl -H "Authorization: Bearer devtoken" http://127.0.0.1:10101/health
```

## Environment Variables

### Required
- `SOMA_API_TOKEN` - API authentication (use `devtoken` for local dev)

### Database
- `POSTGRES_URL` - PostgreSQL connection string
  - Default: `postgresql://postgres:postgres@localhost:5433/somamemory`

### Redis
- `REDIS_HOST` - Redis hostname (default: `redis`)
- `REDIS_PORT` - Redis port (default: `6379`)

### Milvus
- `SOMA_MILVUS_HOST` - Milvus hostname (default: `milvus`)
- `SOMA_MILVUS_PORT` - Milvus port (default: `19530`)

### Feature Flags
- `SOMA_FORCE_HASH_EMBEDDINGS` - Use hash-based embeddings (fast, deterministic)
- `SOMA_ENABLE_BATCH_UPSERT` - Enable batched writes for throughput
- `SOMA_BATCH_SIZE` - Batch size (default: 100)
- `SOMA_BATCH_FLUSH_MS` - Batch flush interval (default: 5ms)

## Backend Selection

The system uses a **hybrid KV store** pattern:
1. **PostgreSQL** - Canonical/authoritative data
2. **Redis** - Cache layer for fast reads + distributed locks

Writes go to both; reads try Redis first, fall back to Postgres.

## Vector Store

**Milvus only** - Qdrant support was removed for consistency with SomaBrain.

The vector store handles:
- Embedding storage and retrieval
- Similarity search
- Payload filtering

## Graceful Degradation

The factory (`factory.py`) handles service unavailability:
- If Postgres unavailable → Redis-only mode (with warning)
- If Redis unavailable → InMemoryKeyValueStore fallback (with warning)
- If Milvus unavailable → **Error** (vectors are required)

## Migrations

Database migrations use Alembic:
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```
