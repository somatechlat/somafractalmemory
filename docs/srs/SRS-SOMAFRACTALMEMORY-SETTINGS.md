# SRS-SOMAFRACTALMEMORY-SETTINGS

**Document ID:** SRS-SFM-SETTINGS-001
**Version:** 2.0.0
**Date:** 2026-01-25
**Status:** PRODUCTION
**Source of Truth:** `somafractalmemory/settings.py`

---

## 1. Overview

This document defines the configuration parameters for the SomaFractalMemory service.
All configuration is performed via environment variables (12-Factor App).

> [!IMPORTANT]
> All variable names are case-sensitive.

---

## 2. Infrastructure Configuration

### 2.1 Database (PostgreSQL)
Used for Django Models (Metadata, Graph Links, Logs).

| Variable | Default | required | Description |
|----------|---------|:--------:|-------------|
| `SOMA_DB_NAME` | - | ✅ | Database name |
| `SOMA_DB_USER` | - | ✅ | Database user |
| `SOMA_DB_PASSWORD` | - | ✅ | Database password |
| `SOMA_DB_HOST` | - | ✅ | Database host |
| `SOMA_DB_PORT` | `5432` | | Database port |
| `SOMA_POSTGRES_SSL_MODE` | - | | SSL Mode (disable, allow, prefer, require) |

### 2.2 Vector Store (Milvus)
Used for High-Dimensional Vector Embeddings.

| Variable | Default | Required | Description |
|----------|---------|:--------:|-------------|
| `SOMA_MILVUS_HOST` | - | ✅ | Milvus Host |
| `SOMA_MILVUS_PORT` | `19530` | | Milvus Port |

### 2.3 Cache (Redis)
Used for Session Caching and Locks.

| Variable | Default | Required | Description |
|----------|---------|:--------:|-------------|
| `SOMA_REDIS_HOST` | - | ✅ | Redis Host |
| `SOMA_REDIS_PORT` | `6379` | | Redis Port |
| `SOMA_REDIS_DB` | `0` | | Redis DB Index |
| `SOMA_REDIS_PASSWORD` | - | | Redis Password |

---

## 3. Application Configuration

### 3.1 Security & Network

| Variable | Default | Required | Description |
|----------|---------|:--------:|-------------|
| `SOMA_SECRET_KEY` | - | ✅ | Django Secret Key (Crypto) |
| `SOMA_ALLOWED_HOSTS` | - | ✅ | Comma-separated allowlist |
| `SOMA_API_TOKEN` | - | ✅ | Bearer token for API Auth |
| `SOMA_DEBUG` | `false` | | Enable Debug Mode |
| `SOMA_CORS_ORIGINS` | `` | | CORS Allowlist |

### 3.2 Memory Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_NAMESPACE` | `default` | Global isolation namespace |
| `SOMA_VECTOR_DIM` | `768` | Embedding dimensionality |
| `SOMA_MAX_MEMORY_SIZE` | `100000` | Max items before pruning |
| `SOMA_PRUNING_INTERVAL_SECONDS` | `600` | Cleanup interval |
| `SOMA_MODEL_NAME` | `microsoft/codebert-base` | Embedding Model ID |

### 3.3 Hybrid Search Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_HYBRID_RECALL_DEFAULT` | `true` | Enable hybrid (vector+keyword) |
| `SOMA_HYBRID_BOOST` | `2.0` | Keyword match score boost |
| `SOMA_SIMILARITY_METRIC` | `cosine` | Distance metric |

### 3.4 Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_ENABLE_BATCH_UPSERT` | `false` | Enable bulk write mode |
| `SOMA_ASYNC_METRICS_ENABLED` | `false` | Async Prometheus/Telemetry |
| `SFM_FAST_CORE` | `false` | Enable experimental Rust core |

---

## 4. Advanced Tuning

### 4.1 Decay Simulation
Control how memories fade over time.

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_DECAY_AGE_HOURS_WEIGHT` | `1.0` | Impact of memory age |
| `SOMA_DECAY_RECENCY_HOURS_WEIGHT` | `1.0` | Impact of last access |
| `SOMA_DECAY_IMPORTANCE_WEIGHT` | `2.0` | Protection of important memories |
| `SOMA_DECAY_THRESHOLD` | `2.0` | Pruning threshold score |

### 4.2 Circuit Breakers

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_CIRCUIT_FAILURE_THRESHOLD` | `3` | Failures before trip |
| `SOMA_CIRCUIT_RESET_INTERVAL` | `60.0` | Seconds to auto-reset |

---

## 5. Deployment Example (.env)

```bash
SOMA_SECRET_KEY=production-secret-CHANGE-ME
SOMA_ALLOWED_HOSTS=*
SOMA_DFS_MODE=AAAS

SOMA_DB_HOST=postgres
SOMA_DB_NAME=somamemory
SOMA_DB_USER=soma
SOMA_DB_PASSWORD=soma

SOMA_MILVUS_HOST=milvus
SOMA_REDIS_HOST=redis
```
