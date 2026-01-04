# 💾 SomaFractalMemory Quick Start Guide

> **Fractal Coordinate Memory System** - Get SomaFractalMemory running in 10 minutes

---

## Prerequisites

| Component | Minimum Version |
|-----------|-----------------|
| Docker | 24.0+ |
| Docker Compose | 2.20+ |
| Python | 3.11+ |
| RAM | 8GB |

---

## Step 1: Clone & Configure

```bash
# Clone the repository
git clone https://github.com/somatech/somafractalmemory.git
cd somafractalmemory

# Copy environment template
cp .env.example .env
```

### Required Environment Variables

```bash
# Database (use shared SOMA Stack database)
SOMA_DB_HOST=localhost
SOMA_DB_PORT=20432
SOMA_DB_NAME=somafractalmemory
SOMA_DB_USER=postgres
SOMA_DB_PASSWORD=somastack2024

# Redis
REDIS_URL=redis://:somastack2024@localhost:20379/2

# Milvus (Vector DB)
MILVUS_HOST=localhost
MILVUS_PORT=20530

# API Settings
SFM_API_PORT=9595
SFM_API_TOKEN=your-secure-token
```

---

## Step 2: Start Infrastructure

### With SomaAgent01 Stack (Recommended)

```bash
# Start from somaAgent01 directory
cd ../somaAgent01
docker compose up -d
```

### Standalone Mode

```bash
docker compose up -d
```

---

## Step 3: Verify Health

```bash
# Check API health
curl http://localhost:9595/health

# Expected response:
# {"status": "healthy", "component": "somafractalmemory"}
```

---

## Step 4: Run Migrations

```bash
# With Tilt (automatic, from SomaAgent01)
tilt up

# Manual
python manage.py migrate --database=somafractalmemory
```

---

## Port Namespace Reference

**SomaFractalMemory uses port 9xxx/10xxx:**

| Service | Port |
|---------|------|
| Memory API | 9595 |
| Metrics | 9596 |

**Dependencies (from SomaAgent01 20xxx):**
- PostgreSQL: 20432
- Redis: 20379
- Milvus: 20530

---

## Step 5: Development Workflow

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -e .

# Run development server
uvicorn somafractalmemory.asgi:application --host 0.0.0.0 --port 9595 --reload
```

---

## Key API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/memories` | POST | Store memory with fractal coordinates |
| `/memories/search` | POST | Search memories by query |
| `/memories/{id}` | GET | Retrieve specific memory |
| `/memories/{id}` | DELETE | Delete memory |
| `/health` | GET | Health check |

---

## Memory Storage Example

```python
import httpx

# Store a memory
response = httpx.post(
    "http://localhost:9595/memories",
    headers={"Authorization": "Bearer your-token"},
    json={
        "coord": "0.1,0.2,0.3,0.4",  # Fractal coordinates
        "payload": {
            "content": "User asked about weather",
            "agent_id": "agent-uuid",
            "user_id": "user-uuid",
            "timestamp": "2026-01-04T08:00:00Z"
        },
        "memory_type": "episodic"
    }
)

# Search memories
response = httpx.post(
    "http://localhost:9595/memories/search",
    headers={"Authorization": "Bearer your-token"},
    json={
        "query": "weather",
        "top_k": 5,
        "filters": {"agent_id": "agent-uuid"}
    }
)
```

---

## Architecture Overview

```
SomaFractalMemory
├── somafractalmemory/
│   ├── __init__.py     - Package initialization
│   ├── services.py     - Core memory services
│   ├── models.py       - Data models
│   ├── settings.py     - Configuration
│   └── api/            - API endpoints
│       ├── memories.py
│       ├── health.py
│       └── schemas.py
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect to Milvus" | Ensure SomaAgent01 stack is running |
| "Database does not exist" | Run `make reset-infra` from SomaAgent01 |
| "Invalid fractal coordinates" | Use comma-separated float values |

---

## Related Documentation

- [SomaAgent01 Quick Start](../somaAgent01/docs/QUICKSTART.md)
- [Architecture](./docs/architecture.md)
- [API Reference](./docs/api-reference.md)

---

**Version**: 1.0.0 | **Last Updated**: 2026-01-04
