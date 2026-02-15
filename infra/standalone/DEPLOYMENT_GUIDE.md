# SomaFractalMemory Docker Deployment Guide

> **Document Version**: 2.0.0
> **Last Updated**: 2026-01-09
> **Status**: ✅ Verified 100% Healthy

This guide provides step-by-step instructions for deploying SomaFractalMemory (SFM).

---

## Quick Start

```bash
# 1. Clone and navigate
cd /path/to/somafractalmemory

# 2. Start all services
docker compose -f infra/standalone/docker-compose.yml up -d

# 3. Apply migrations
docker exec somafractalmemory-standalone-api python manage.py migrate

# 4. Verify health (all 6 services should be healthy)
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker | 24.0+ | Latest |
| Docker Compose | 2.20+ | Latest |
| RAM | 4GB | 8GB |
| Disk | 5GB | 10GB |

---

## Step-by-Step Deployment

### Step 1: Environment Setup

```bash
# Copy example environment file (if exists)
cp .env.example .env 2>/dev/null || true

# Default environment is suitable for local development
```

### Step 2: Start Core Services

```bash
# Start standalone stack
docker compose -f infra/standalone/docker-compose.yml up -d

# Wait for services to initialize
sleep 20
```

### Step 3: Apply Database Migrations

```bash
# Apply Django migrations
docker exec somafractalmemory-standalone-api python manage.py migrate
```

### Step 4: Verify Health

```bash
# Check all containers are healthy
docker compose ps

# Expected: 6 services, all (healthy)
# - somafractalmemory-standalone-api
# - somafractalmemory-standalone-postgres
# - somafractalmemory-standalone-redis
# - somafractalmemory-standalone-milvus
# - somafractalmemory-standalone-etcd
# - somafractalmemory-standalone-minio
```

### Step 5: Test API

```bash
# Basic health check
curl -s http://localhost:10101/healthz

# Expected: {"kv_store": true, "vector_store": true, "graph_store": true}

# Search test (empty results expected)
curl -s -X POST http://localhost:10101/memories/search \
  -H "Authorization: Bearer $SOMA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}'

# Expected: {"memories": []}
```

---

## Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| somafractalmemory-standalone-api | 10101 | Main API service |
| somafractalmemory-standalone-postgres | 5432 | PostgreSQL database |
| somafractalmemory-standalone-redis | 6379 | KV store + cache |
| somafractalmemory-standalone-milvus | 19530 | Vector database |
| somafractalmemory-standalone-etcd | 2379 | Milvus metadata |
| somafractalmemory-standalone-minio | 9000 | Milvus object storage |

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/healthz` | GET | Basic health check |
| `/health` | GET | Detailed health with store status |
| `/memories` | POST | Store a memory |
| `/memories/<coord>` | GET | Fetch a memory |
| `/memories/<coord>` | DELETE | Delete a memory |
| `/memories/search` | POST | Vector similarity search |
| `/stats` | GET | Memory statistics |
| `/docs` | GET | OpenAPI documentation |

---

## Running Tests

### Integration Tests (from host)
```bash
cd /path/to/somafractalmemory
source .venv/bin/activate
python -m pytest tests/integration/ -v
```

### API Tests
```bash
# Store + Search flow test
curl -X POST http://localhost:10101/memories/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test memory", "limit": 5}'
```

---

## Troubleshooting

### Container Restarting
```bash
# Check logs
docker logs somafractalmemory-standalone-api --tail 50

# Verify Milvus dependencies (etcd, minio) are healthy first
docker logs somafractalmemory-standalone-milvus --tail 50
```

### Migration Errors
```bash
# Run migrations manually
docker exec somafractalmemory-standalone-api python manage.py migrate --run-syncdb

# If tables exist, reset database (DESTRUCTIVE)
docker compose down -v && docker compose up -d
```

### Milvus Connection Issues
```bash
# Verify Milvus is ready
curl -s http://localhost:9091/healthz

# Check etcd health
docker exec somafractalmemory-standalone-etcd etcdctl endpoint health
```

---

## Integration with SomaBrain

SomaFractalMemory serves as the persistent memory layer for SomaBrain:

```bash
# Both clusters should be running:
# SomaBrain: 16 services on ports 30101+
# SFM: 6 services on port 10101

# Configure SomaBrain to use SFM
export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://localhost:10101
```

---

## Production Deployment

For Kubernetes deployment:
```bash
# See Kubernetes manifests
ls infra/k8s/

# Apply with kubectl
kubectl apply -f infra/k8s/sfm-resilient.yaml
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-01-09 | 6-service verification, API reference, troubleshooting |
| 1.0.0 | 2026-01-08 | Initial deployment guide |
