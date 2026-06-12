
# 💾 SomaFractalMemory

> [!IMPORTANT]
> **Distributed Long-Term Memory for Autonomous AI Agents**

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django 5.0+](https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=for-the-badge)](LICENSE)

---

## 1. Identification

- **Project**: SomaFractalMemory
- **Version**: 0.2.0
- **API Version**: 2.0.0 (OpenAPI schema version; decoupled from package version)
- **Classification**: PROPRIETARY / COMMERCIAL SENSITIVE
- **Status**: Production Ready

## 2. System Overview

**SomaFractalMemory** is a distributed long-term memory service for AI agents. It provides **persistent vector storage** with semantic search, enabling agents to recall past experiences and learned knowledge across sessions.

### 2.1 Architectural Context
Core component of the **Soma Cognitive Triad**:
1. **SomaBrain**: Processing & Reasoning
2. **SomaAgent01**: Orchestration & Execution
3. **SomaFractalMemory**: **Storage & Recall** (This Repo)

### 2.2 Key Capabilities
- **Semantic Search**: 768-dim embeddings via Milvus.
- **Hierarchical Memory**: Episodes (raw), Semantic (facts), Summaries (patterns).
- **Multi-Tenancy**: Crypto-isolated namespaces.
- **Fractal Organization**: Weighted importance and degradation graphs.

---

## 3. Installation & Configuration

### 3.1 Prerequisites
- **Python**: 3.12+
- **Docker**: 24.0+
- **PostgreSQL**: 15+ (Metadata)
- **Milvus**: 2.3+ (Vectors)
- **Redis**: 7.0+ (Cache)
- **HashiCorp Vault**: (Optional, Recommended for Secrets)
- **Open Policy Agent**: (Optional, Recommended for AuthZ)

### 3.2 Quick Start (Standalone)
```bash
# 1. Clone & Setup
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory

# 2. Launch Stack (--env-file is REQUIRED)
docker compose -f infra/standalone/docker-compose.yml \
  --env-file infra/standalone/.env up -d

# 3. Verify health
curl -s http://localhost:10101/healthz | python3 -m json.tool
```

### 3.3 Configuration Parameters

Settings are loaded from `somafractalmemory/settings/infra.py` and `standalone.py`.

| Variable | Description | Default | Source |
|:---|:---|:---|:---|
| `SOMA_API_PORT` | API listen port | `10101` | `infra.py:83` |
| `SOMA_DB_HOST` | PostgreSQL host | `localhost` | `django_core.py:61` |
| `SOMA_DB_PORT` | PostgreSQL port | `5432` | `django_core.py:62` |
| `SOMA_DB_USER` | PostgreSQL user | `postgres` | `django_core.py:59` |
| `SOMA_DB_PASSWORD` | PostgreSQL password | — | Vault injection |
| `SOMA_REDIS_HOST` | Redis host | `localhost` | `infra.py:46` |
| `SOMA_REDIS_PORT` | Redis port | `6379` | `infra.py:47` |
| `SOMA_MILVUS_HOST` | Milvus host | `localhost` | `infra.py:54` |
| `SOMA_MILVUS_PORT` | Milvus port | `19530` | `infra.py:55` |
| `VAULT_ADDR` | Vault server URL | — | Container env |
| `VAULT_TOKEN` | Vault auth token | — | Container env |
| `SOMA_OPA_URL` | OPA AuthZ URL | `http://opa:8181` | `infra.py:157` |
| `SOMA_OPA_FAIL_OPEN` | Fail-open on OPA error | `False` | `infra.py:159` |
| `SOMA_API_TOKEN` | API bearer token | — | Container env |
| `SOMA_ALLOWED_HOSTS` | Django ALLOWED_HOSTS | `localhost,127.0.0.1` | Container env |

### 3.4 Port Authority (10xxx Range)

| Service | Host Port | Internal Port |
|:---|:---|:---|
| API | **10101** | 10101 |
| PostgreSQL | **10432** | 5432 |
| Redis | **10379** | 6379 |
| Milvus | **10530** | 19530 |
| Vault | **10200** | 8200 |
| OPA | **10818** | 8181 |

---

## 4. Operation Procedures

### 4.1 Production Run
```bash
# Development: uvicorn (ASGI) — declared in pyproject.toml
uvicorn somafractalmemory.config.asgi:application --host 0.0.0.0 --port 10101

# Production: gunicorn with uvicorn workers (install gunicorn separately)
gunicorn somafractalmemory.config.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:10101
```

### 4.2 Development Mode
```bash
# Run tests
pytest tests/
```

### 4.3 API Health Check
```bash
curl http://localhost:10101/healthz
# Returns: {"kv_store": true, "vector_store": true, "graph_store": true}
```

---

## 5. Interface Specification

### 5.1 REST API References

#### Store Memory
`POST /memories`
```json
{
  "coord": "1.0,2.0,3.0",
  "payload": { "content": "User prefers dark mode" },
  "memory_type": "semantic"
}
```

#### Search Memory
`POST /memories/search`
```json
{
  "query": "dark mode",
  "top_k": 5
}
```

---

## 6. Maintenance & Contribution

- **License**: Apache 2.0
- **Maintainer**: SomaTech LAT
- **Issues**: [GitHub Issues](https://github.com/somatechlat/somafractalmemory/issues)
