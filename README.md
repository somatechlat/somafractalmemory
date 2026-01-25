
# 💾 SomaFractalMemory

> [!IMPORTANT]
> **Distributed Long-Term Memory for Autonomous AI Agents**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django 5.0+](https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=for-the-badge)](LICENSE)

---

## 1. Identification

- **Project**: SomaFractalMemory
- **Version**: 0.2.0
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
- **Python**: 3.11+
- **Docker**: 24.0+
- **PostgreSQL**: 15+ (Metadata)
- **Milvus**: 2.3+ (Vectors)
- **Redis**: 7.0+ (Cache)

### 3.2 Quick Start (Production)
```bash
# 1. Clone & Setup
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory

# 2. Configure Environment
cp .env.example .env
# EDIT .env WITH REAL CREDENTIALS

# 3. Launch Stack
docker compose --profile core up -d
```

### 3.3 Configuration Parameters
| Variable | Description | Default |
|----------|-------------|---------|
| `SOMA_API_PORT` | API Service Port | `10101` |
| `SOMA_POSTGRES_URL` | Database Connection | `postgresql://...` |
| `SOMA_MILVUS_HOST` | Vector Store Host | `localhost` |
| `SOMA_REDIS_HOST` | Cache Host | `localhost` |

---

## 4. Operation Procedures

### 4.1 Production Run
```bash
# Start Django Server via Gunicorn/Uvicorn
gunicorn somafractalmemory.wsgi:application --bind 0.0.0.0:10101
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
`POST /api/v2/memory/store`
```json
{
  "content": "User prefers dark mode",
  "namespace": "user-prefs",
  "type": "semantic"
}
```

#### Search Memory
`POST /api/v2/memory/search`
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
