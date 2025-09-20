
# SomaFractalMemoryEnterprise: Modular Agentic Memory System

## 🛣️ Prioritized Roadmap

### 1. Core Foundation (Week 1)
- Modularize memory, prediction, and graph interfaces.
- Implement config-driven mode selection (simple, local_llm, enterprise).
- Build core memory storage, recall, and semantic graph (local).

### 2. Predictive Memory & LLM Integration (Week 2)
- Add pluggable prediction module (no LLM, local LLM, external LLM).
- Implement caching and cost-saving strategies.
- Add agent self-reflection API (for prediction error analysis).

### 3. Observability & Tooling (Week 3)
- Integrate logging, tracing, and metrics.
- Build a simple web dashboard for memory inspection and config.
- Add automated test harness and simulation scripts.

### 4. Enterprise & Distributed Features (Week 4)
- Add support for distributed event streaming (Kafka/NATS/Redis Streams).
- Integrate distributed vector DB and Redis Cluster.
- Add monitoring/alerting (Prometheus).
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
								   |        |        |
								   |        |        |
				+------------------+        |        +------------------+
				|                           |                           |
+---------------------------+   +-------------------------+   +-------------------------+
|  Storage Module           |   |  Prediction Module      |   |  Semantic Graph Module  |
|  (Dict/Redis/Cluster)     |   |  (None/Local/External)  |   |  (NetworkX/Neo4j/etc.) |
+---------------------------+   +-------------------------+   +-------------------------+
				|                           |                           |
				+---------------------------+---------------------------+
									|
						+-----------------------------+
						|   Observability/Monitoring  |
						|   (Logging, Metrics, UI)    |
						+-----------------------------+
```

---

## Feature Matrix

| Feature                  | Home Dev | Local LLM Dev | Enterprise |
|--------------------------|:--------:|:-------------:|:----------:|
| Memory Storage/Recall    |    ✔     |      ✔        |     ✔      |
| Semantic Graph           |    ✔     |      ✔        |     ✔      |
| Vector Search            |    ✔     |      ✔        |     ✔      |
| Predictive Memory        |    ✖     |      ✔        |     ✔      |
| Distributed Event Stream |    ✖     |   (optional)  |     ✔      |
| Distributed Vector DB    |    ✖     |   (optional)  |     ✔      |
| High-Availability        |    ✖     |   (optional)  |     ✔      |
| Monitoring/Alerting      |    ✖     |   (optional)  |     ✔      |
| User Management/Security |    ✖     |      ✖        |     ✔      |

---

## Key Principles

- **Pluggable:** Swap any module (storage, prediction, graph) via config.
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

## Security & Model-Download Roadmap (short)

- Secure-by-default: HF model downloads should be pinned via `SOMA_MODEL_REV`.
- Allow unpinned downloads only when `SOMA_ALLOW_UNPINNED_HF=true` is explicitly set for developer convenience.
- Gate pickle-based serialization behind `SOMA_ALLOW_PICKLE=true` and log a startup warning when enabled; prefer JSON or msgpack for production.
- Replace broad `except:` usages with narrow exception types and parameterized logging to avoid masking failures while keeping fallbacks robust.
- Re-run Bandit and static tools as part of CI; document any justified `# nosec` uses with a short rationale.

This roadmap is implemented incrementally on the `feature/safety-eviction-enterprise` branch (local). See `docs/SECURITY_ROADMAP.md` for full details and rationale.
