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

# Configure environment
cp .env.example .env

# Start the standalone stack (API + Postgres + Redis + Milvus + dependencies)
docker compose -f infra/standalone/docker-compose.yml up -d

# Verify health
curl http://localhost:10101/healthz
```

### Services

| Service | Image | Port | Memory |
|---------|-------|------|--------|
| API | somafractalmemory-api | 10101 | 1 GB |
| PostgreSQL | postgres:15 | 10432 | 1.5 GB |
| Redis | redis:7 | 10379 | 512 MB |
| etcd | quay.io/coreos/etcd:v3.5.5 | - | 256 MB |
| MinIO | minio/minio | - | 256 MB |
| Milvus | milvusdb/milvus:v2.3.3 | 10530 | 6 GB |

### Environment Variables

Create a `.env` file (see `.env.example`):

```bash
# Required secrets
SOMA_API_TOKEN=your-secure-token-here
SFM_DB_PASSWORD=your-secure-db-password
SFM_VAULT_TOKEN=your-secure-vault-token
SFM_MINIO_ROOT_USER=your-minio-user
SFM_MINIO_ROOT_PASSWORD=your-minio-password
```

### Production Commands

```bash
# Start services
docker compose -f infra/standalone/docker-compose.yml up -d

# View logs
docker compose -f infra/standalone/docker-compose.yml logs -f --tail=200 somafractalmemory-standalone-api

# Stop services
docker compose -f infra/standalone/docker-compose.yml down

# Reset (remove volumes)
docker compose -f infra/standalone/docker-compose.yml down -v
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
| `SOMA_API_TOKEN` | - | **Required**. Authentication token |
| `SOMA_SECRET_KEY` | - | **Required**. Django crypto key |
| `SOMA_ALLOWED_HOSTS` | * | **Required**. Hostname allowlist |
| `SOMA_API_PORT` | 10101 | API port |
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
curl http://localhost:10101/healthz
```

Expected response:
```json
{"kv_store": true, "vector_store": true, "graph_store": true}
```

### Readiness Probe

```bash
curl http://localhost:10101/readyz
```

### Detailed Health

```bash
curl http://localhost:10101/health
```

---

## Monitoring

### Prometheus Metrics

```bash
curl http://localhost:10101/metrics
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
docker compose -f infra/standalone/docker-compose.yml exec -T somafractalmemory-standalone-postgres \
  pg_dump -U "${SFM_DB_USER:-somafractalmemory}" "${SFM_DB_NAME:-somafractalmemory}" > backup.sql

# Restore
docker compose -f infra/standalone/docker-compose.yml exec -T somafractalmemory-standalone-postgres \
  psql -U "${SFM_DB_USER:-somafractalmemory}" "${SFM_DB_NAME:-somafractalmemory}" < backup.sql
```

### Volume Backup

```bash
# Stop services
docker compose -f infra/standalone/docker-compose.yml down

# Backup volumes
docker run --rm -v somafractalmemory_pgdata:/data \
  -v $(pwd):/backup ubuntu tar cvf /backup/pgdata.tar /data
```

---

## Troubleshooting

### API Not Starting

1. Check logs: `docker compose -f infra/standalone/docker-compose.yml logs -f --tail=200 somafractalmemory-standalone-api`
2. Verify PostgreSQL is healthy
3. Verify Milvus is healthy

### Database Connection Failed

1. Check PostgreSQL status: `docker compose -f infra/standalone/docker-compose.yml ps somafractalmemory-standalone-postgres`
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
