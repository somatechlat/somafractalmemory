# ARCHIVED

This file is no longer maintained. Please refer to the up‑to‑date architecture documentation in **docs/ARCHITECTURE.md**.

# SomaFractalMemoryEnterprise: Modular Agentic Memory System

## 🛣️ Prioritized Roadmap

### 1. Core Foundation (Week 1)
- Modularize memory and graph interfaces.
- Implement config-driven mode selection (simple, local_llm, enterprise).
- Build core memory storage, recall, and semantic graph (local).

### 2. LLM Integration (Week 2)
- Add optional LLM-powered summarization and enrichment hooks.
- Implement caching and cost-saving strategies.
- Add agent self-reflection API for analyzing reported outcomes.

### 3. Observability & Tooling (Week 3)
- Integrate logging, tracing, and metrics.
- Build a simple web dashboard for memory inspection and config.
- Add automated test harness and simulation scripts.

### 4. Enterprise & Distributed Features (Week 4)
- Add support for distributed event streaming (Kafka/NATS/Redis Streams).
- Integrate distributed vector DB and Redis Cluster.
- Add monitoring/alerting (Prometheus, Grafana).
- Implement multi-agent support (namespaces, agent IDs).

### 5. Advanced Agent Features & Community (Ongoing)
- Memory prioritization, compression, and pruning.
- Knowledge graph sync (optional, for advanced users).
- Policy/safety layer for LLM and memory usage.
- Documentation, quickstart templates, and plugin system.

---

## 🧩 Modular Architecture Diagram (Textual)

```
+-------------------+         +-------------------+         +-------------------+
|   Agent(s)        | <-----> |   Memory API      | <-----> |   Config Manager  |
+-------------------+         +-------------------+         +-------------------+
                                   |        |
                                   |        |
                +------------------+        +------------------+
                |                                      |
+---------------------------+              +-------------------------+
|  Storage Module           |              |  Semantic Graph Module  |
|  (Postgres/Redis/Hybrid) |              |  (NetworkX/Neo4j/etc.) |
+---------------------------+              +-------------------------+
                |                                      |
                +---------------------------+----------+
                                                |
                        +-----------------------------+
                        |   Observability/Monitoring  |
                        |   (Logging, Metrics, UI)    |
                        +-----------------------------+
```

+-------------------+   +-------------------+   +-------------------+
|   FastAPI Server  | → |   openapi.json    | ← |   mkdocs site    |
+-------------------+   +-------------------+   +-------------------+

+-------------------+   +-------------------+
|   Docker Compose  | → |   start_stack.sh  |
+-------------------+   +-------------------+

## Feature Matrix

| Feature                  | Home Dev | Local LLM Dev | Enterprise |
|--------------------------|:--------:|:-------------:|:----------:|
| Memory Storage/Recall    |    ✔     |      ✔        |     ✔      |
| Semantic Graph           |    ✔     |      ✔        |     ✔      |
| Vector Search            |    ✔     |      ✔        |     ✔      |
| Distributed Event Stream |    ✖     |   (optional)  |     ✔      |
| Distributed Vector DB    |    ✖     |   (optional)  |     ✔      |
| High-Availability        |    ✖     |   (optional)  |     ✔      |
| Monitoring/Alerting      |    ✖     |   (optional)  |     ✔      |
| User Management/Security |    ✖     |      ✖        |     ✔      |

---

## Infrastructure (Docker Compose)
- **docker-compose.yml** – runs Redis and Qdrant for local development.
- **docker-compose.dev.yml** – adds Redpanda, Apicurio Registry, Postgres, and Qdrant for event‑driven and enterprise modes.
- **scripts/start_stack.sh** – orchestrates which services to start based on the chosen `MemoryMode` (`development`, `evented_enterprise`, `cloud_managed`, `test`).
- **OpenAPI generation** – `examples/api.py` creates `openapi.json` on FastAPI startup; `scripts/generate_openapi.py` can be run manually to dump the spec.

---

## Key Principles

- **Pluggable:** Swap storage and graph modules via config.
- **Unified API:** All agent code interacts with a single, stable interface.
- **Agent-Aware:** Self-reflection, memory prioritization, and meta-memory built in.
- **Scalable:** Grows from laptop to enterprise cluster with config change.
- **Observable:** Easy to debug, monitor, and optimize.

---

## Improvement Opportunities

- Modular, pluggable architecture for future-proofing
- Unified API for all modes
- Agent-centric features: self-reflection, memory prioritization, compression
- Observability: logging, metrics, dashboard
- Multi-agent support and knowledge graph integration
- Policy/safety layer for LLM and memory usage
- Community plugins and extensibility

---

*This document is a living architecture and action plan for the SomaFractalMemoryEnterprise agentic memory system. Update as the project evolves!*
