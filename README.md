<div align="center">

# 💾 SomaFractalMemory

### *Distributed Long-Term Memory for Autonomous AI Agents*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django 5.0+](https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=for-the-badge)](LICENSE)
[![Build](https://img.shields.io/badge/Build-Passing-brightgreen?style=for-the-badge)]()

<br/>

**Persistent semantic memory at scale**

[Website](https://www.somatech.dev) · [Features](#-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [API](#-api-reference) · [Documentation](#-documentation)

</div>

---

## 🌀 Overview

**SomaFractalMemory** is a distributed long-term memory service for AI agents. It provides **persistent vector storage** with semantic search, enabling agents to recall past experiences and learned knowledge across sessions.

The **"fractal" architecture** stores memories at multiple scales of abstraction—from raw experiences to high-level summaries—creating a hierarchical memory structure that mirrors human cognition.

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🔍 Semantic Search

- **768-dimensional embeddings** for rich representation
- **Milvus integration** for billion-scale vector search
- **Hybrid retrieval** combining vector + lexical
- **Metadata filtering** for precise recall

</td>
<td width="50%">

### 🏗️ Hierarchical Memory

- **Episode memories** — raw experiences
- **Semantic memories** — abstracted knowledge
- **Summary memories** — high-level patterns
- **Fractal organization** across scales

</td>
</tr>
<tr>
<td>

### 🔐 Multi-Tenant Isolation

- **Namespace separation** per tenant
- **Cryptographic isolation** of memory spaces
- **Quota management** per tenant
- **Access control** via OPA policies

</td>
<td>

### 📊 Advanced Features

- **Decay simulation** for natural forgetting
- **Importance-weighted storage**
- **Automatic summarization**
- **Cross-memory linking**

</td>
</tr>
</table>

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          SOMAFRACTALMEMORY                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│    ┌─────────────────────────────────────────────────────────────────────┐     │
│    │                       REST API LAYER                                 │     │
│    │                    (Django Ninja - OpenAPI)                          │     │
│    └───────────────────────────────┬─────────────────────────────────────┘     │
│                                    │                                            │
│    ┌───────────────────────────────┼───────────────────────────────────┐       │
│    │                               │                                   │       │
│    ▼                               ▼                                   ▼       │
│  ┌───────────────┐         ┌───────────────┐         ┌───────────────┐        │
│  │   STORAGE     │         │   RETRIEVAL   │         │   EMBEDDING   │        │
│  │   ENGINE      │         │    ENGINE     │         │    SERVICE    │        │
│  │               │         │               │         │               │        │
│  │ • Write       │         │ • Vector      │         │ • Encode      │        │
│  │ • Index       │         │ • Lexical     │         │ • Batch       │        │
│  │ • Decay       │         │ • Filter      │         │ • Cache       │        │
│  └───────┬───────┘         └───────┬───────┘         └───────────────┘        │
│          │                         │                                           │
│          └─────────────────────────┘                                           │
│                        │                                                        │
│    ┌───────────────────┼───────────────────────────────────────────────┐       │
│    │                   ▼                                               │       │
│    │   ┌─────────────────────────────────────────────────────────┐    │       │
│    │   │                  MEMORY HIERARCHY                        │    │       │
│    │   │                                                          │    │       │
│    │   │   📝 Episodes      📚 Semantic       📊 Summaries       │    │       │
│    │   │   (raw traces)     (knowledge)       (patterns)          │    │       │
│    │   │        │               │                 │               │    │       │
│    │   │        └───────────────┼─────────────────┘               │    │       │
│    │   │                        ▼                                 │    │       │
│    │   │              🌀 FRACTAL INDEX                           │    │       │
│    │   └─────────────────────────────────────────────────────────┘    │       │
│    │                      NAMESPACE ISOLATION                          │       │
│    └───────────────────────────────────────────────────────────────────┘       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────────┐
              │                       │                           │
        ┌─────▼─────┐          ┌──────▼──────┐          ┌─────────▼─────────┐
        │ PostgreSQL │          │   Milvus    │          │      Redis        │
        │  Metadata  │          │   Vectors   │          │      Cache        │
        └───────────┘          └─────────────┘          └───────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | Runtime |
| PostgreSQL | 15+ | Metadata storage |
| Milvus | 2.3+ | Vector similarity |
| Redis | 7+ | Caching |

### Installation

```bash
# Clone the repository
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Initialize database
python manage.py migrate

# Start the server
python manage.py runserver 10101
```

### 🐳 Docker Deployment

```bash
docker-compose up -d
```

---

## 📡 API Reference

### Store Memory

```bash
curl -X POST http://localhost:10101/api/v2/memory/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User prefers dark mode in all applications",
    "namespace": "user-preferences",
    "type": "semantic",
    "importance": 0.9,
    "metadata": {
      "user_id": "user-123",
      "category": "preferences"
    }
  }'
```

```json
{
  "id": "mem_8f3b2a1c",
  "embedding_id": "vec_9k5e3g2b",
  "importance": 0.9,
  "created_at": "2026-01-03T10:30:00Z"
}
```

### Search Memory

```bash
curl -X POST http://localhost:10101/api/v2/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the user preferences for UI?",
    "namespace": "user-preferences",
    "top_k": 10,
    "filters": {"category": "preferences"}
  }'
```

```json
{
  "memories": [
    {
      "id": "mem_8f3b2a1c",
      "content": "User prefers dark mode in all applications",
      "score": 0.92,
      "type": "semantic"
    }
  ],
  "latency_ms": 8
}
```

### Delete Memory

```bash
curl -X DELETE http://localhost:10101/api/v2/memory/{id}
```

---

## ⚙️ Configuration

Core configuration in `config.yaml`:

```yaml
# Core settings
namespace: "default"
vector_dim: 768
api_port: 10101

# Database connections
postgres_url: "postgresql://soma:soma@postgres:5432/somamemory"
milvus_host: "milvus"
milvus_port: 19530
```

📖 **Full reference:** [`docs/srs/SRS-SOMAFRACTALMEMORY-SETTINGS.md`](docs/srs/SRS-SOMAFRACTALMEMORY-SETTINGS.md)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System architecture |
| [API Reference](docs/api-reference.md) | Complete API documentation |
| [Settings](docs/srs/SRS-SOMAFRACTALMEMORY-SETTINGS.md) | All configuration options |
| [Deployment](docs/deployment.md) | Production deployment guide |

---

## 🤝 SomaStack Ecosystem

| Project | Description | Link |
|---------|-------------|------|
| 🧠 **SomaBrain** | Hyperdimensional cognitive memory | [GitHub](https://github.com/somatechlat/somabrain) |
| 🤖 **SomaAgent01** | Agent orchestration gateway | [GitHub](https://github.com/somatechlat/somaAgent01) |

---

<div align="center">

## 📜 License

Licensed under the [Apache License, Version 2.0](LICENSE)

---

<br/>

**Built with 💾 by the SomaTech team**

*"Memories that persist, intelligence that grows."*

<br/>

[![Star](https://img.shields.io/github/stars/somatechlat/somafractalmemory?style=social)](https://github.com/somatechlat/somafractalmemory)

</div>
