# SomaFractalMemory Standalone Deployment Guide

> **Document Version**: 3.0.0
> **Last Updated**: 2026-02-19
> **Status**: ✅ Verified — 30/30 tests, 8 services healthy

---

## Quick Start

```bash
# 1. Navigate to repo
cd /path/to/somafractalmemory

# 2. Start all services (--env-file is REQUIRED)
docker compose -f infra/standalone/docker-compose.yml \
  --env-file infra/standalone/.env up -d

# 3. Verify all 8 containers healthy
docker compose -f infra/standalone/docker-compose.yml ps

# 4. Health check
curl -s http://localhost:10101/health | python3 -m json.tool
```

---

## Prerequisites

| Requirement | Minimum | Recommended |
|:---|:---|:---|
| Docker | 24.0+ | Latest |
| Docker Compose | 2.20+ | Latest |
| RAM | 4GB | 8GB |
| Disk | 5GB | 10GB |

---

## Architecture: Secrets via Vault

SFM uses **HashiCorp Vault** for credential injection. The flow:

1. `.env` file provides `SFM_VAULT_TOKEN`, `SFM_DB_PASSWORD`, `SFM_DB_USER`
2. `vault-init` container writes these to Vault KV v2 at `somafractalmemory/database` and `somafractalmemory/redis`
3. API container bootstraps with `VAULT_ADDR` + `VAULT_TOKEN`
4. `infra.py` calls `vault_client.get_db_credentials()` → injects `SOMA_DB_USER`, `SOMA_DB_PASSWORD` into `os.environ`
5. `standalone.py` reads those env vars to override `DATABASES["default"]`

**No database passwords are passed directly to the API container.**

---

## Port Authority (10xxx Range)

SFM standalone uses the **10xxx** host port range. Inside the Docker network, services use standard internal ports.

| Service | Host Port | Internal Port | Protocol | Purpose |
|:---|:---|:---|:---|:---|
| API | **10101** | 10101 | HTTP | Main SFM API |
| PostgreSQL | **10432** | 5432 | TCP | Metadata store |
| Redis | **10379** | 6379 | TCP | KV cache |
| Milvus API | **10530** | 19530 | gRPC | Vector database |
| Milvus Mgmt | **10531** | 9091 | HTTP | Milvus health/metrics |
| Vault | **10200** | 8200 | HTTP | Secrets management |
| OPA | **10818** | 8181 | HTTP | Authorization engine |
| etcd | — | 2379 | TCP | Milvus metadata (no host mapping) |
| MinIO | — | 9000 | HTTP | Milvus object store (no host mapping) |

---

## Services (8 containers + 1 init)

| Container | Image | Health Check |
|:---|:---|:---|
| `somafractalmemory-standalone-api` | `somafractalmemory:latest` | `curl http://localhost:10101/health` |
| `somafractalmemory-standalone-postgres` | `postgres:15-alpine` | `pg_isready` |
| `somafractalmemory-standalone-redis` | `redis:7.2-alpine` | `redis-cli ping` |
| `somafractalmemory-standalone-milvus` | `milvusdb/milvus:v2.3.3` | `curl http://localhost:9091/healthz` |
| `somafractalmemory-standalone-etcd` | `quay.io/coreos/etcd:v3.5.5` | `etcdctl endpoint health` |
| `somafractalmemory-standalone-minio` | `minio/minio:RELEASE.2023-03-20T20-16-18Z` | `curl http://localhost:9000/minio/health/live` |
| `somafractalmemory-standalone-vault` | `hashicorp/vault:1.13.3` | `vault status` |
| `somafractalmemory-standalone-opa` | `openpolicyagent/opa:0.54.0` | `opa eval time.now_ns()` |
| `somafractalmemory-standalone-vault-init` | `alpine:latest` | Exits after seeding Vault |

---

## Environment Variables (`.env`)

All secrets and config live in `infra/standalone/.env`.

| Variable | Required | Description |
|:---|:---|:---|
| `SFM_VAULT_TOKEN` | ✅ | Vault dev root token |
| `SFM_DB_USER` | ✅ | PostgreSQL username |
| `SFM_DB_PASSWORD` | ✅ | PostgreSQL password |
| `SFM_MINIO_ROOT_USER` | ✅ | MinIO access key |
| `SFM_MINIO_ROOT_PASSWORD` | ✅ | MinIO secret key |
| `SOMA_API_TOKEN` | ✅ | API bearer token |
| `SOMA_ALLOWED_HOSTS` | No | Default: `localhost,127.0.0.1` |
| `SOMA_LOG_LEVEL` | No | Default: `INFO` |

---

## Django Settings Chain

```
DJANGO_SETTINGS_MODULE = somafractalmemory.settings.standalone

Load order:
  1. settings/__init__.py → imports django_core.py + infra.py
  2. django_core.py → DATABASES defaults (env-based)
  3. infra.py → Vault credential injection, Redis/Milvus/OPA config
  4. standalone.py → Overrides DATABASES from env, strips AAAS apps
```

---

## Migration Tree

```
0001_initial → Memory, GraphLink, VectorEmbedding, MemoryNamespace, AuditLog
  └── 0003_tenant_scoped_uniqueness → UniqueConstraint updates
        └── 0004_apikey_usagerecord → APIKey, UsageRecord (AAAS models)
```

Apply migrations:
```bash
docker exec somafractalmemory-standalone-api python manage.py migrate --noinput
```

Verify no pending migrations:
```bash
docker exec somafractalmemory-standalone-api python manage.py makemigrations --check
```

---

## API Endpoints

| Endpoint | Method | Auth | Purpose |
|:---|:---|:---|:---|
| `/healthz` | GET | No | Basic health (kv, vector, graph) |
| `/health` | GET | No | Detailed health with latency + stats |
| `/memories` | POST | Bearer | Store a memory |
| `/memories/<coord>` | GET | Bearer | Retrieve a memory |
| `/memories/<coord>` | DELETE | Bearer | Delete a memory |
| `/memories/search` | POST | Bearer | Vector similarity search |
| `/stats` | GET | Bearer | Memory statistics |
| `/docs` | GET | No | OpenAPI documentation |

---

## Running Tests

```bash
# Full test suite (30 tests — unit, integration, deep integration, E2E)
docker exec -e SOMA_INFRA_AVAILABLE=1 somafractalmemory-standalone-api \
  python -m pytest tests/ -v --tb=short --create-db

# Unit tests only
docker exec somafractalmemory-standalone-api \
  python -m pytest tests/unit/ -v

# Deep integration tests (requires SOMA_INFRA_AVAILABLE=1)
docker exec -e SOMA_INFRA_AVAILABLE=1 somafractalmemory-standalone-api \
  python -m pytest tests/test_deep_integration.py -v --reuse-db

# Code quality
docker exec somafractalmemory-standalone-api python -m ruff check somafractalmemory/
```

---

## Troubleshooting

### Clean Deploy (Nuclear Option)
```bash
docker compose -f infra/standalone/docker-compose.yml --env-file infra/standalone/.env down -v
docker compose -f infra/standalone/docker-compose.yml --env-file infra/standalone/.env up -d
```

### Vault Credential Issues
```bash
# Check Vault health
curl -s http://localhost:10200/v1/sys/health | python3 -m json.tool

# Read DB credentials from Vault
curl -s -H "X-Vault-Token: $(grep SFM_VAULT_TOKEN infra/standalone/.env | cut -d= -f2)" \
  http://localhost:10200/v1/somafractalmemory/data/database | python3 -m json.tool
```

### API Logs
```bash
docker logs somafractalmemory-standalone-api --tail 50
```

---

## Integration with SomaBrain

```bash
# SomaBrain connects to SFM via:
export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://localhost:10101
```

---

## Document History

| Version | Date | Changes |
|:---|:---|:---|
| 3.0.0 | 2026-02-19 | Full rewrite: 8-service arch, Port Authority, Vault flow, migration tree, 30-test suite |
| 2.0.0 | 2026-01-09 | 6-service verification, API reference |
| 1.0.0 | 2026-01-08 | Initial deployment guide |
