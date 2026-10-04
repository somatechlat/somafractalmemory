# Deployment Guide

## Document Control

| Field | Value |
|---|---|
| Document Title | Deployment Guide |
| Document Identifier | SOMA-SFM-GUIDE-DEPLOY-001 |
| Version | 1.1.0 |
| Date | 2026-10-03 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2027-01-03 |


## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-09-28 | SomaTech Engineering | Initial issue. Brought under the house ISO document-control contract. |
| 1.1.0 | 2026-10-03 | SomaTech Engineering | Truth pass against the code. Removed `SOMA_API_PORT` and `SOMA_RATE_LIMIT_MAX` from the configuration reference — those knobs were deleted (`settings/infra.py`). Defaults now match `TUNABLES` in `settings/model.py`. Added the deleted-key list so operators do not set knobs that do nothing. |


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
SOMA_DB_PASSWORD=your-secure-db-password
SOMA_VAULT_TOKEN=your-secure-vault-token
SOMA_MINIO_ROOT_USER=your-minio-user
SOMA_MINIO_ROOT_PASSWORD=your-minio-password
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

Every tunable is declared once on the `TUNABLES` registry in
`somafractalmemory/settings/model.py`. Keys that no longer exist were deleted
because nothing reads them — see `settings/infra.py`. Do not configure a key
that is not in `TUNABLES`.

### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_API_TOKEN` | - | **Required**. Authentication token (fail-closed: unconfigured rejects every caller) |
| `SOMA_SECRET_KEY` | - | **Required**. Django crypto key |
| `SOMA_ALLOWED_HOSTS` | - | **Required**. Hostname allowlist |
| `SOMA_MEMORY_NAMESPACE` | `api_ns` | Default namespace |
| `SOMA_LOG_LEVEL` | `INFO` | Logging level |
| `SOMA_LOG_JSON` | `false` | Render logs as JSON |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_DB_HOST` | `localhost` | Database host |
| `SOMA_DB_PORT` | `5432` | Database port |
| `SOMA_DB_USER` | - | Database user (Vault: `somafractalmemory/database` → `username`) |
| `SOMA_DB_PASSWORD` | - | Database password (Vault: `somafractalmemory/database` → `password`) |
| `SOMA_DB_NAME` | `somafractalmemory` | Database name |

Credentials have **no code default**. Vault is consulted first; a Vault failure
raises. There is no ENV fallback and no `SOMA_POSTGRES_URL` legacy DSN.

### Cache Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_REDIS_HOST` | `null` | Redis host. Absent means no Redis is deployed. |
| `SOMA_REDIS_PORT` | `6379` | Redis port |
| `SOMA_REDIS_DB` | `0` | Redis database |

### Vector Store Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_MILVUS_HOST` | `null` | Milvus host. Absent means no Milvus is deployed. |
| `SOMA_MILVUS_PORT` | `19530` | Milvus port |
| `SOMA_VECTOR_DIM` | `768` | Vector dimension (must equal the agent seam's `MEM_EMBED_DIM`) |
| `SOMA_SIMILARITY_METRIC` | `cosine` | Milvus distance metric (`cosine\|ip\|l2`) |
| `SOMA_MILVUS_NLIST` | `128` | IVF_FLAT cluster count at collection creation |
| `SOMA_MILVUS_NPROBE` | `16` | IVF_FLAT clusters probed per search |

### Deleted keys (do not set)

These once appeared in deployment material. They were deleted because no
feature reads them. Setting them does nothing.

`SOMA_API_PORT`, `SOMA_RATE_LIMIT_MAX`, `SOMA_RATE_LIMIT_WINDOW_SECONDS`,
`SOMA_CORS_ORIGINS`, `SOMA_MAX_REQUEST_BODY_MB`, `SOMA_OPA_URL`,
`SOMA_OPA_TIMEOUT`, `SOMA_OPA_FAIL_OPEN`, `SOMA_JWT_*`, `SOMA_POSTGRES_URL`,
`SOMA_FORCE_HASH_EMBEDDINGS`, `SOMA_ENABLE_BATCH_UPSERT`, `SOMA_DECAY_*`,
`SOMA_PRUNING_INTERVAL_SECONDS`, `SOMA_MAX_MEMORY_SIZE`, `SOMA_IMPORTANCE_*`,
`SOMA_HYBRID_*`, `SOMA_CIRCUIT_*`. Full record: `settings/infra.py`.

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
  pg_dump -U "${SOMA_DB_USER:-somafractalmemory}" "${SOMA_DB_NAME:-somafractalmemory}" > backup.sql

# Restore
docker compose -f infra/standalone/docker-compose.yml exec -T somafractalmemory-standalone-postgres \
  psql -U "${SOMA_DB_USER:-somafractalmemory}" "${SOMA_DB_NAME:-somafractalmemory}" < backup.sql
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
