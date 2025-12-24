# Deployment Guide

This guide covers deploying SomaFractalMemory in production.

## Docker Compose Deployment

### Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- 10GB available RAM

### Quick Start

```bash
# Clone repository
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory

# Start all services
docker compose --profile core up -d

# Verify health
curl http://localhost:9595/healthz
```

### Services

| Service | Image | Port | Memory |
|---------|-------|------|--------|
| API | somafractalmemory-api | 9595 | 1 GB |
| PostgreSQL | postgres:15 | 40001 | 1.5 GB |
| Redis | redis:7 | 40002 | 512 MB |
| etcd | quay.io/coreos/etcd:v3.5.5 | - | 256 MB |
| MinIO | minio/minio | - | 256 MB |
| Milvus | milvusdb/milvus:v2.3.3 | 40003, 40004 | 6 GB |

### Environment Variables

Create a `.env` file:

```bash
# API Configuration
API_PORT=9595
SOMA_API_PORT=9595
SOMA_API_TOKEN=your-secure-token-here

# PostgreSQL
POSTGRES_HOST_PORT=40001
POSTGRES_USER=soma
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=somamemory

# Redis
REDIS_HOST_PORT=40002

# Memory settings
SOMA_MEMORY_NAMESPACE=production
```

### Production Commands

```bash
# Start services
docker compose --profile core up -d

# View logs
docker compose --profile core logs -f api

# Stop services
docker compose --profile core down

# Reset (remove volumes)
docker compose --profile core down -v
```

---

## Kubernetes Deployment

### Helm Chart

The `helm/` directory contains Kubernetes manifests.

```bash
# Install
helm install somafractalmemory ./helm \
  -f helm/values-prod-ha.yaml \
  --namespace somabrain

# Upgrade
helm upgrade somafractalmemory ./helm \
  -f helm/values-prod-ha.yaml \
  --namespace somabrain
```

### Resource Limits

```yaml
# helm/values.yaml
api:
  resources:
    limits:
      memory: 1Gi
      cpu: 1000m
    requests:
      memory: 512Mi
      cpu: 250m
```

---

## Configuration Reference

### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_API_TOKEN` | - | Authentication token |
| `SOMA_API_PORT` | 9595 | API port |
| `SOMA_MEMORY_NAMESPACE` | api_ns | Default namespace |
| `SOMA_RATE_LIMIT_MAX` | 0 | Rate limit (0=disabled) |
| `LOG_LEVEL` | INFO | Logging level |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | postgres | Database host |
| `POSTGRES_PORT` | 5432 | Database port |
| `POSTGRES_USER` | soma | Database user |
| `POSTGRES_PASSWORD` | soma | Database password |
| `POSTGRES_DB` | somamemory | Database name |

### Cache Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | redis | Redis host |
| `REDIS_PORT` | 6379 | Redis port |
| `REDIS_DB` | 0 | Redis database |

### Vector Store Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_MILVUS_HOST` | milvus | Milvus host |
| `SOMA_MILVUS_PORT` | 19530 | Milvus port |

---

## Health Checks

### Liveness Probe

```bash
curl http://localhost:9595/healthz
```

Expected response:
```json
{"kv_store": true, "vector_store": true, "graph_store": true}
```

### Readiness Probe

```bash
curl http://localhost:9595/readyz
```

### Detailed Health

```bash
curl http://localhost:9595/health
```

---

## Monitoring

### Prometheus Metrics

```bash
curl http://localhost:9595/metrics
```

Exposed metrics:
- `http_requests_total` - Request count
- `http_request_duration_seconds` - Request latency
- `memory_operations_total` - Memory operations

### Logging

Logs are written to stdout in JSON format:

```json
{
    "timestamp": "2025-12-24T02:58:14.044Z",
    "level": "INFO",
    "message": "Memory stored",
    "coordinate": "1.0,2.0,3.0"
}
```

---

## Backup and Restore

### PostgreSQL Backup

```bash
# Backup
docker compose --profile core exec postgres \
  pg_dump -U soma somamemory > backup.sql

# Restore
docker compose --profile core exec -T postgres \
  psql -U soma somamemory < backup.sql
```

### Volume Backup

```bash
# Stop services
docker compose --profile core down

# Backup volumes
docker run --rm -v somafractalmemory_pgdata:/data \
  -v $(pwd):/backup ubuntu tar cvf /backup/pgdata.tar /data
```

---

## Troubleshooting

### API Not Starting

1. Check logs: `docker compose --profile core logs api`
2. Verify PostgreSQL is healthy
3. Verify Milvus is healthy

### Database Connection Failed

1. Check PostgreSQL status: `docker compose --profile core ps postgres`
2. Verify credentials in `.env`
3. Check network connectivity

### Memory Issues

1. Check container memory limits
2. Review PostgreSQL shared_buffers
3. Check Redis maxmemory setting

---

## Security

### Token Authentication

Set a strong API token:

```bash
SOMA_API_TOKEN=$(openssl rand -hex 32)
```

### Network Security

- Internal services (etcd, MinIO) are not exposed externally
- API is the only public endpoint
- Use reverse proxy (nginx) for TLS termination

### Database Security

- Use strong passwords for PostgreSQL
- Enable SSL for database connections in production
- Regular backup rotation
