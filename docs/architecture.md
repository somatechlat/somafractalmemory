# SomaFractalMemory Architecture

> **SOMA Stack Memory Core** — Django Ninja API for fractal memory storage, vector search, and graph operations.

## Overview

SomaFractalMemory (SFM) is the persistent memory layer of the SOMA Stack. It provides:

- **Vector Storage** — High-dimensional embedding storage via Milvus
- **Graph Operations** — Entity relationships and semantic linking
- **Hybrid Search** — Combined vector + keyword search
- **Multi-Tenant Isolation** — Namespace-based data separation

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   SOMAFRACTALMEMORY                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Django Ninja│  │  Settings    │  │  Auth Middleware    │  │
│  │  API         │  │  (config)    │  │  (Bearer Token)      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│  ┌──────▼─────────────────▼──────────────────────▼───────────┐  │
│  │                    STORES LAYER                           │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │  │
│  │  │VectorStore  │ │GraphStore   │ │MetadataStore        │  │  │
│  │  │(Milvus)     │ │(PostgreSQL) │ │(PostgreSQL)         │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │                    COMMON LAYER                           │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │  │
│  │  │Embeddings   │ │Serialization│ │Config               │  │  │
│  │  │(Hash/Model) │ │(JSON)       │ │(settings.py)        │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  PostgreSQL   │    │    Milvus     │    │    Redis      │
│  (Metadata)   │    │  (Vectors)    │    │  (WM Cache)   │
└───────────────┘    └───────────────┘    └───────────────┘
```

## Deployment Model

**SaaS Only** — Deployed as part of the unified `somastack_saas` container.

```yaml
# docker-compose.yml
somastack_saas:
  ports:
    - "63901:10101"  # Memory API
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| **API Framework** | Django Ninja |
| **ORM** | Django ORM |
| **Settings** | django-environ |
| **Metadata DB** | PostgreSQL 15 |
| **Vector DB** | Milvus 2.3 |
| **Working Memory** | Redis 7.2 |
| **Object Storage** | MinIO |

## Directory Structure

```
somafractalmemory/
├── somafractalmemory/
│   ├── settings.py           # Django settings (316 lines)
│   ├── api/                  # Django Ninja API
│   │   ├── v1.py             # API entry point
│   │   └── endpoints/        # 8 endpoint modules
│   ├── stores/               # Storage backends
│   │   ├── vector_store.py   # Milvus integration
│   │   ├── graph_store.py    # Graph operations
│   │   └── metadata_store.py # PostgreSQL metadata
│   └── migrations/           # 1 Django migration
├── common/
│   └── config/
│       └── settings.py       # Shared configuration
├── Dockerfile.api            # API container
└── .env.example              # Environment template
```

## API Endpoints

### Memory Operations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/store` | Store memory item |
| POST | `/recall` | Recall by query |
| POST | `/search` | Vector similarity search |
| DELETE | `/delete/{id}` | Delete memory item |

### Graph Operations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/graph/link` | Create entity link |
| GET | `/graph/neighbors/{id}` | Get neighbors |
| DELETE | `/graph/link/{id}` | Delete link |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Kubernetes probe |
| GET | `/health` | Detailed health |

## Configuration

### Environment Variables

```bash
# PostgreSQL
SOMA_POSTGRES_URL=postgresql://soma:soma@somastack_postgres:5432/somamemory
SOMA_DB_HOST=somastack_postgres
SOMA_DB_PORT=5432
SOMA_DB_NAME=somamemory
SOMA_DB_USER=soma
SOMA_DB_PASSWORD=soma

# Redis
SOMA_REDIS_HOST=somastack_redis
SOMA_REDIS_PORT=6379

# Milvus
SOMA_MILVUS_HOST=somastack_milvus
SOMA_MILVUS_PORT=19530

# Collection
SFM_COLLECTION=somamemory_vectors
SFM_VECTOR_DIM=1536

# API Security
SOMA_API_TOKEN=your_secret_token

# Embedding
SOMA_FORCE_HASH_EMBEDDINGS=false
```

## Memory Model

### Vector Storage (Milvus)

```python
# Collection schema
collection = {
    "name": "somamemory_vectors",
    "fields": [
        {"name": "id", "type": "VARCHAR", "max_length": 64, "is_primary": True},
        {"name": "tenant_id", "type": "VARCHAR", "max_length": 64},
        {"name": "namespace", "type": "VARCHAR", "max_length": 128},
        {"name": "vector", "type": "FLOAT_VECTOR", "dim": 1536},
        {"name": "content", "type": "VARCHAR", "max_length": 65535},
        {"name": "importance", "type": "FLOAT"},
        {"name": "created_at", "type": "INT64"},
    ],
    "index": {"type": "IVF_FLAT", "metric": "COSINE", "nlist": 128}
}
```

### Metadata (PostgreSQL)

```python
class MemoryItem(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    tenant_id = models.CharField(max_length=64)
    namespace = models.CharField(max_length=128)
    content = models.TextField()
    payload = models.JSONField()
    importance = models.FloatField(default=0.5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant_id", "namespace"]),
        ]
```

## Hybrid Search

SFM supports hybrid search combining:

1. **Vector Similarity** — Cosine similarity in Milvus
2. **Keyword Search** — Full-text search in PostgreSQL
3. **Importance Weighting** — Score adjustment based on importance

```python
# Hybrid recall
results = await sfm.recall(
    query="What is the capital of France?",
    top_k=10,
    hybrid=True,
    importance_weight=0.3
)
```

## Integration

### With SomaBrain
- HTTP client via `SOMABRAIN_MEMORY_HTTP_ENDPOINT`
- Token authentication via `SOMA_API_TOKEN`
- In-process bridge in SaaS mode

### Milvus Stack (Dependencies)
- **etcd** — Milvus coordination
- **MinIO** — Object storage for large vectors

## Performance

### Importance Normalization

```python
# Reservoir sampling for stable P95
SOMA_IMPORTANCE_RESERVOIR_MAX=512
SOMA_IMPORTANCE_MIN_SAMPLES=32
SOMA_IMPORTANCE_DECAY=0.99
```

### Batch Processing

```python
# Enable for bulk operations
SOMA_ENABLE_BATCH_UPSERT=true
SOMA_BATCH_SIZE=100
SOMA_BATCH_TIMEOUT_MS=1000
```

## VIBE Compliance

- **Rule 82**: Modularity — Clean store abstraction
- **Rule 84**: No Stubs — Real Milvus/PostgreSQL
- **Rule 86**: Purity — Django Ninja only
- **Rule 103**: Real Infrastructure — Docker Compose

## Development

```bash
# Run locally with Django
cd somafractalmemory
python manage.py runserver 0.0.0.0:10101

# Run via Docker (SaaS mode)
cd ../somaAgent01/infra/saas
docker-compose up -d
```

## License

Proprietary — SomaTech.lat
