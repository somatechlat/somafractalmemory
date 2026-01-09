# SomaFractalMemory Docker Deployment

## Overview
Storage tier (L2) for the SOMA Stack. This directory contains Docker Compose configuration for local development and E2E testing.

## Prerequisites
- Docker Engine 24+
- Docker Compose v2+
- 4GB+ available RAM

## Quick Start
```bash
# From project root
docker compose -f infra/docker/docker-compose.yml -p sfm up -d

# Verify health
curl http://localhost:10101/healthz

# View logs
docker logs sfm-sfm-api-1 -f
```

## Services

| Service | Image | Port (Host) | Port (Container) | Memory |
|---------|-------|-------------|------------------|--------|
| sfm-api | Built from Dockerfile | 10101 | 10101 | 384M |
| postgres | postgres:15-alpine | 30201 | 5432 | 512M |
| redis | redis:7-alpine | 30202 | 6379 | 256M |
| milvus | milvusdb/milvus:v2.3.4 | 30203 | 19530 | 2G |

## Environment Variables
| Variable | Value | Description |
|----------|-------|-------------|
| `SOMA_POSTGRES_URL` | `postgresql://soma:soma@postgres:5432/somamemory` | PostgreSQL connection |
| `SOMA_REDIS_HOST` | `redis` | Redis host |
| `SOMA_MILVUS_HOST` | `milvus` | Milvus host |

## Commands

```bash
# Start stack
docker compose -f infra/docker/docker-compose.yml -p sfm up -d

# Stop stack
docker compose -f infra/docker/docker-compose.yml -p sfm down

# Rebuild API
docker compose -f infra/docker/docker-compose.yml -p sfm up -d --build sfm-api

# Clean up (including volumes)
docker compose -f infra/docker/docker-compose.yml -p sfm down -v
```

## E2E Tests
```bash
# Run memory save test
curl -X POST http://localhost:10101/api/v1/store \
  -H "Content-Type: application/json" \
  -d '{"content": "test memory", "embedding": [0.1, 0.2, 0.3]}'
```
