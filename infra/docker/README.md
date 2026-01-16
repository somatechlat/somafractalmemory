# SomaFractalMemory Docker Deployment

## Overview
Storage tier (L2) for the SOMA Stack. Restored from git commit `f003d52~1` with fixes for build context and environment variables.

## Prerequisites
- Docker Engine 24+
- Docker Compose v2+
- 8GB+ available RAM

## Quick Start
```bash
# From project root
docker compose -f infra/docker/docker-compose.yml -p sfm --profile core up -d

# Verify health
curl http://localhost:10101/healthz

# View logs
docker logs somafractalmemory_api -f
```

## Services

| Service | Image | Port (Host) | Port (Container) | Memory |
|---------|-------|-------------|------------------|--------|
| api | Built from Dockerfile | 10101 | 10101 | 1G |
| postgres | postgres:15 | 10432 | 5432 | 1.5G |
| redis | redis:7 | 10379 | 6379 | 512M |
| milvus | milvusdb/milvus:v2.3.3 | 10530 | 19530 | 8G |
| etcd | quay.io/coreos/etcd:v3.5.5 | 2379 | 2379 | 1G |
| minio | minio/minio | 9000 | 9000 | 1G |

## Environment Variables
| Variable | Value | Description |
|----------|-------|-------------|
| `SOMA_API_TOKEN` | `dev-token-somastack2024` | API authentication token |
| `SOMA_POSTGRES_URL` | `postgresql://soma:soma@postgres:5432/somamemory` | PostgreSQL connection |
| `SOMA_REDIS_HOST` | `redis` | Redis host |
| `SOMA_MILVUS_HOST` | `milvus` | Milvus host |
| `DJANGO_SETTINGS_MODULE` | `somafractalmemory.settings` | Django settings |

## Commands

```bash
# Start stack with core profile
docker compose -f infra/docker/docker-compose.yml -p sfm --profile core up -d

# Stop stack
docker compose -f infra/docker/docker-compose.yml -p sfm down

# Rebuild API
docker compose -f infra/docker/docker-compose.yml -p sfm --profile core up -d --build api

# Run migrations
docker exec somafractalmemory_api python manage.py migrate --noinput

# Clean up (including volumes)
docker compose -f infra/docker/docker-compose.yml -p sfm down -v
```

## Run E2E Tests
```bash
# Default uses localhost:10101 and token from SOMA_API_TOKEN env
.venv/bin/python -m pytest tests/test_end_to_end_memory.py -v

# With explicit settings
SFM_API_URL=http://localhost:10101 SOMA_API_TOKEN=dev-token-somastack2024 \
  .venv/bin/python -m pytest tests/test_end_to_end_memory.py -v
```

## Healthz Response
```json
{"kv_store": true, "vector_store": true, "graph_store": true}
```

## Troubleshooting

### API container restarting
Check logs: `docker logs somafractalmemory_api`

### Database connection refused
Ensure `SOMA_POSTGRES_URL` uses container network name `postgres:5432`, not `localhost:10432`.

### Missing module errors
The volume mount (`../..:/app`) overrides built files with host source, so source must be at project root.
