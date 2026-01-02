# SomaFractalMemory - Agent Context

> Purpose: Provide a single, accurate reference for agents working on the SomaFractalMemory repo.
> Last updated: 2026-01-02

---

## Quick Summary

SomaFractalMemory is a **fractal coordinate-based vector memory system**. It stores and retrieves memories using hierarchical fractal coordinates, backed by PostgreSQL, Redis, and Milvus.

**Role in SomaStack:** Layer 1 (Storage/Memory Layer)

---

## SomaStack Hierarchy

```
SomaStack/
├── shared/             # Port 49000-49099 (Keycloak, etc.)
├── SomaFractalMemory/  # Port 21000-21099 ← THIS REPO
├── SomaBrain/          # Port 30000-30199
└── SomaAgent01/        # Port 20000-20199
```

---

## Software Modes

- **StandAlone**: Runs independently with local auth/storage.
- **SomaStackClusterMode**: Paired with SomaBrain for integrated cognitive operations.

---

## Project Structure

```
somafractalmemory/
├── api/                    # Django Ninja API
│   ├── endpoints/          # Memory endpoints
│   └── schemas/            # Pydantic schemas
├── core/                   # Memory models
│   ├── models.py           # Django ORM models
│   └── fractal.py          # Fractal coordinate system
├── services/               # Memory services
│   ├── store.py            # Memory storage
│   ├── recall.py           # Memory retrieval
│   └── indexer.py          # Vector indexing
├── docs/                   # Documentation
│   └── SRS-SOMAFRACTALMEMORY-MASTER.md  # Master SRS
├── tests/                  # Test suites
└── docker-compose.yml      # Local stack
```

---

## Ports (21000 Range)

| Service | Port | Description |
|---------|------|-------------|
| **API** | 21000 | Memory REST API |
| **PostgreSQL** | 21001 | Metadata storage |
| **Redis** | 21002 | Cache layer |
| **Milvus gRPC** | 21003 | Vector search |
| **Milvus HTTP** | 21004 | Vector metrics |

---

## Core Environment Variables

```bash
# API
SOMA_API_PORT=9595           # Internal port
API_PORT=21000               # Host port
SOMA_API_TOKEN=devtoken      # API auth token

# Database
POSTGRES_HOST_PORT=21001
POSTGRES_PASSWORD=postgres

# Cache
REDIS_HOST_PORT=21002

# Vector DB
MILVUS_HOST_PORT=21003
MILVUS_GRPC_PORT=21004
```

---

## API Endpoints

Base URL: `http://localhost:21000/api/v1`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/memories` | Store memory |
| `POST` | `/memories/search` | Recall memories |
| `GET` | `/memories/{id}` | Get memory |
| `DELETE` | `/memories/{id}` | Delete memory |

### Memory Store Request

```json
POST /api/v1/memories
{
  "coord": "0.1,0.2,0.3,0.4",
  "payload": {
    "content": "Memory content",
    "agent_id": "uuid",
    "user_id": "uuid",
    "memory_type": "episodic"
  }
}
```

### Memory Search Request

```json
POST /api/v1/memories/search
{
  "query": "search text",
  "top_k": 5,
  "filters": {
    "agent_id": "uuid",
    "memory_type": "episodic"
  }
}
```

---

## Development with Tilt

```bash
# Start infrastructure
colima start
minikube start

# Deploy SomaStack (includes SomaFractalMemory)
cd somaAgent01
tilt up --port 10351

# SomaStack Tilt Dashboard
open http://localhost:10351
```

---

## Testing Notes

- Tests require real infrastructure; no mocks.
- Use `docker compose --profile core up -d` for test infra.
- Run tests: `pytest tests/`

---

## Key Documentation

- Master SRS: `docs/SRS-SOMAFRACTALMEMORY-MASTER.md`
- VIBE Rules: Follow rules from SomaAgent01 repo

---

## VIBE Coding Rules (CRITICAL)

1. **NO MOCKS** - All tests use real infrastructure
2. **Django ORM only** - No SQLAlchemy
3. **Milvus only** - No Qdrant
4. **Complete implementations** - No placeholders

---

## Related Services

| Service | Port | Connection |
|---------|------|------------|
| SomaBrain | 30101 | `SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://host.docker.internal:21000` |
| SomaAgent01 | 20020 | `SOMA_MEMORY_URL=http://host.docker.internal:21000` |
