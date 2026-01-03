# SRS-SOMAFRACTALMEMORY-SETTINGS

**Document ID:** SRS-SFM-SETTINGS-001
**Version:** 1.0.0
**Date:** 2026-01-03
**Status:** CANONICAL
**Repository:** `somafractalmemory`
**Sources:** `config.yaml`, `common/*.py`

---

## 1. Overview

This document defines ALL settings for the **SomaFractalMemory** long-term memory service.

### 1.1 Statistics

| Category | Count |
|----------|:-----:|
| Infrastructure | 12 |
| Memory | 6 |
| **TOTAL** | **18** |

---

# PART 1: INFRASTRUCTURE SETTINGS

---

## 2. Core Configuration (`config.yaml`)

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `namespace` | str | default | Memory namespace |
| `vector_dim` | int | 768 | Embedding dimension |
| `api_port` | int | 9595 | API server port |

---

## 3. Database Connections

### 3.1 PostgreSQL

| Setting | Type | Default |
|---------|------|---------|
| `postgres_url` | str | postgresql://soma:soma@postgres:5432/somamemory |
| `infra.postgres` | str | postgres |

### 3.2 Milvus (Vector Store)

| Setting | Type | Default |
|---------|------|---------|
| `milvus_host` | str | milvus |
| `milvus_port` | int | 19530 |
| `infra.milvus` | str | milvus |

---

## 4. External Services

### 4.1 Infrastructure Endpoints

| Key | Default | Purpose |
|-----|---------|---------|
| `infra.redis` | redis | Cache service |
| `infra.vault` | '' | Secrets management |
| `infra.opa` | '' | Policy engine |
| `infra.auth` | '' | Authentication |
| `infra.etcd` | '' | Config store |
| `infra.prometheus` | '' | Metrics |
| `infra.jaeger` | '' | Tracing |

---

# PART 2: SOFTWARE SETTINGS

---

## 5. Memory Configuration

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `namespace` | str | default | Isolation namespace |
| `vector_dim` | int | 768 | Vector dimensions |

---

## 6. API Configuration

| Setting | Type | Default |
|---------|------|---------|
| `api_port` | int | 9595 |

---

## 7. Environment Variables

The following environment variables override `config.yaml`:

| Variable | Type | Purpose |
|----------|------|---------|
| `SFM_NAMESPACE` | str | Override namespace |
| `SFM_VECTOR_DIM` | int | Override vector dim |
| `SFM_API_PORT` | int | Override port |
| `POSTGRES_URL` | str | Database URL |
| `MILVUS_HOST` | str | Vector store |
| `MILVUS_PORT` | int | Vector port |
| `REDIS_URL` | str | Cache URL |

---

**This is the canonical settings reference for SomaFractalMemory.**
