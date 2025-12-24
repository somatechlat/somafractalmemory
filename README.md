# SomaFractalMemory

A production-ready fractal memory system built with Django and Django Ninja.

## Overview

SomaFractalMemory is a coordinate-based memory storage system that enables:
- **Memory Storage**: Store and retrieve memories by coordinate vectors
- **Graph Relationships**: Create links between memory coordinates
- **Vector Search**: Semantic search using Milvus vector database
- **Multi-tenancy**: Isolated data per tenant

## Technology Stack

| Component | Technology |
|-----------|------------|
| **API Framework** | Django 5.2 + Django Ninja |
| **ORM** | Django ORM |
| **Database** | PostgreSQL 15 |
| **Cache** | Redis 7 |
| **Vector Store** | Milvus 2.3 |
| **WSGI Server** | gunicorn |
| **Container** | Docker |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)

### Run with Docker Compose

```bash
# Clone the repository
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory

# Start all services
docker compose --profile core up -d

# Check health
curl http://localhost:9595/healthz
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Liveness probe |
| `/health` | GET | Detailed health with service latencies |
| `/stats` | GET | Memory statistics |
| `/memories` | POST | Store a memory |
| `/memories/{coord}` | GET | Retrieve a memory |
| `/memories/{coord}` | DELETE | Delete a memory |
| `/graph/link` | POST | Create a graph link |
| `/graph/neighbors` | GET | Get neighbors of a coordinate |
| `/graph/path` | GET | Find path between coordinates |

### Example Usage

```bash
# Store a memory
curl -X POST http://localhost:9595/memories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"coord": "1.0,2.0,3.0", "payload": {"content": "Hello World"}, "memory_type": "episodic"}'

# Retrieve a memory
curl http://localhost:9595/memories/1.0,2.0,3.0 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create a graph link
curl -X POST http://localhost:9595/graph/link \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"from_coord": "1.0,2.0,3.0", "to_coord": "4.0,5.0,6.0", "link_type": "related"}'
```

## Project Structure

```
somafractalmemory/
├── somafractalmemory/          # Django application
│   ├── api/                    # Django Ninja API
│   │   ├── routers/            # Route handlers
│   │   │   ├── health.py       # Health endpoints
│   │   │   ├── memory.py       # Memory CRUD
│   │   │   ├── search.py       # Vector search
│   │   │   └── graph.py        # Graph operations
│   │   ├── schemas.py          # Pydantic schemas
│   │   ├── messages.py         # i18n messages
│   │   └── core.py             # API initialization
│   ├── models.py               # Django ORM models
│   ├── services.py             # Business logic
│   ├── settings.py             # Django configuration
│   ├── urls.py                 # URL routing
│   └── wsgi.py                 # WSGI application
├── common/                     # Shared utilities
│   ├── config/                 # Configuration helpers
│   └── utils/                  # Logger, decorators
├── scripts/                    # Operational scripts
│   ├── bootstrap.sh            # Container startup
│   └── docker-entrypoint.sh    # Docker entrypoint
├── tests/                      # Test suite
├── docs/                       # Documentation
├── Dockerfile                  # Container image
├── docker-compose.yml          # Service orchestration
└── pyproject.toml              # Python project config
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_API_TOKEN` | - | API authentication token |
| `SOMA_API_PORT` | 9595 | API server port |
| `POSTGRES_HOST` | postgres | PostgreSQL host |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `POSTGRES_USER` | soma | Database user |
| `POSTGRES_PASSWORD` | soma | Database password |
| `POSTGRES_DB` | somamemory | Database name |
| `REDIS_HOST` | redis | Redis host |
| `REDIS_PORT` | 6379 | Redis port |
| `SOMA_MILVUS_HOST` | milvus | Milvus host |
| `SOMA_MILVUS_PORT` | 19530 | Milvus gRPC port |

### Memory Limits (10GB Total)

| Service | Memory Limit |
|---------|--------------|
| PostgreSQL | 1.5 GB |
| Redis | 512 MB |
| etcd | 256 MB |
| MinIO | 256 MB |
| Milvus | 6 GB |
| API | 1 GB |

## Database Models

### Memory

Stores memory data with coordinate-based addressing.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `coordinate` | Float[] | Coordinate vector |
| `payload` | JSONB | Memory content |
| `memory_type` | String | "episodic" or "semantic" |
| `metadata` | JSONB | Additional metadata |
| `importance` | Float | Importance score |
| `tenant` | String | Tenant identifier |
| `created_at` | DateTime | Creation timestamp |

### GraphLink

Stores relationships between memory coordinates.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `from_coordinate` | Float[] | Source coordinate |
| `to_coordinate` | Float[] | Target coordinate |
| `link_type` | String | Relationship type |
| `strength` | Float | Link strength |
| `metadata` | JSONB | Additional metadata |
| `tenant` | String | Tenant identifier |

## Development

### Local Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/
```

### Running Tests

```bash
# Unit tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=somafractalmemory
```

## API Documentation

The API exposes an OpenAPI specification at `/openapi.json`.

### Authentication

All endpoints (except health probes) require Bearer token authentication:

```
Authorization: Bearer YOUR_TOKEN
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request
