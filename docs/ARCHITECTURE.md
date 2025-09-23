# Architecture Overview# Architecture Overview



This document provides a high‑level view of the **SomaFractalMemory** system, its major components, and the data flow between them. The architecture is intentionally modular so that each piece can be swapped out or scaled independently.This document describes the high‑level components of **SomaFractalMemory** and how they interact. All components are real, production‑grade services – there is **no mocking** in the implementation.



------



## Mermaid Component Diagram## Component Diagram (Mermaid)



```mermaid```mermaid

graph TDflowchart LR

    subgraph "Client / CLI"    subgraph CLI[Command‑Line Interface]

        CLI[CLI & Python API]        A[soma CLI]

    end    end

    subgraph "Factory"    subgraph Factory[Factory]

        Factory[create_memory_system]        B[create_memory_system]

    end    end

    subgraph "Core"    subgraph Core[Core Engine]

        Core[SomaFractalMemoryEnterprise]        C[SomaFractalMemoryEnterprise]

    end    end

    subgraph "Backends"    subgraph KV[Key‑Value Store]

        KV[Key‑Value Store]        D[PostgresKeyValueStore]

        KV -->|Postgres| PG[PostgreSQL]        E[RedisKeyValueStore (optional cache & locks)]

        KV -->|Redis Cache| Redis[Redis]    end

        Vector[Vector Store]    subgraph Vector[Vector Store]

        Vector -->|Qdrant| Qdrant[Qdrant]        F[QdrantVectorStore]

        Graph[Graph Store]        G[InMemoryVectorStore (tests)]

        Graph -->|NetworkX| NX[NetworkX (in‑memory)]    end

    end    subgraph Graph[Graph Store]

    subgraph "Prediction"        H[NetworkXGraphStore]

        Pred[Prediction Provider]    end

        Pred -->|Ollama| Ollama[Ollama]    subgraph Predict[Prediction Provider]

        Pred -->|External| Ext[External Service]        I[NoPredictionProvider]

    end        J[OllamaPredictionProvider]

    subgraph "Observability"        K[ExternalPredictionProvider]

        Metrics[Prometheus]    end

        Tracing[OpenTelemetry]    subgraph Event[Event Publishing]

        Langfuse[Langfuse]        L[Kafka Producer (eventing/producer.py)]

    end    end

    subgraph "Eventing"    subgraph Obs[Observability]

        Kafka[Kafka Producer]        M[Prometheus metrics]

    end        N[OpenTelemetry instrumentation]

        O[Langfuse integration]

    CLI --> Factory    end

    Factory --> Core

    Core --> KV    A --> B --> C

    Core --> Vector    C --> D

    Core --> Graph    C --> E

    Core --> Pred    C --> F

    Core --> Metrics    C --> G

    Core --> Tracing    C --> H

    Core --> Langfuse    C --> I

    Core --> Kafka    C --> J

    Kafka -->|memory.events| KafkaTopic[Kafka Topic]    C --> K

```    C --> L

    C --> M

---    C --> N

    C --> O

## Narrative Description```



1. **Client / CLI** – Users interact with the library either programmatically (importing the Python API) or via the provided `soma` command‑line interface. Both paths funnel through the **Factory**.---



2. **Factory (`create_memory_system`)** – Based on the selected `MemoryMode`, the factory wires together concrete backend implementations:## Data Flow

   * **KV Store** – A hybrid of PostgreSQL (canonical storage) and Redis (cache) for fast reads.1. **CLI / HTTP API** invokes `create_memory_system` (Factory) → returns a fully‑wired `SomaFractalMemoryEnterprise` instance.

   * **Vector Store** – Qdrant for scalable ANN search, falling back to an in‑memory store for tests.2. **Core Engine** (`SomaFractalMemoryEnterprise`) receives calls such as `store_memory`, `recall`, `link_memories`.

   * **Graph Store** – NetworkX provides an in‑memory graph for semantic link traversal.3. **KV Store** – writes/reads raw JSON payloads to **PostgreSQL** (`PostgresKeyValueStore`). If a `redis` block is present, a **Redis** instance is also created and used as a cache and for distributed locks.

   * **Prediction Provider** – Either the local Ollama model, an external HTTP service, or a no‑op stub.4. **Vector Store** – embeddings are upserted into **Qdrant** (`QdrantVectorStore`) for similarity search. In test mode the `InMemoryVectorStore` is used.

   * **Eventing** – When enabled, a Kafka producer publishes a `memory.created` event after each successful `store_memory`.5. **Graph Store** – memory relationships are stored in a **NetworkX** graph (`NetworkXGraphStore`).

6. **Prediction Provider** – optional enrichment using either **Ollama** (local LLM) or an **External API**. If none is configured, `NoPredictionProvider` is a no‑op.

3. **Core (`SomaFractalMemoryEnterprise`)** – Implements the public API (store, retrieve, recall, decay, etc.). It orchestrates:7. **Event Publishing** – after a successful `store_memory`, the core builds a JSON‑schema‑validated event and sends it to **Kafka** via the real `confluent_kafka` producer. This can be disabled via `eventing.enabled`.

   * **Encryption** – Optional field‑level encryption via Fernet.8. **Observability** –

   * **Observability** – Prometheus counters/histograms, OpenTelemetry tracing for PostgreSQL/Qdrant calls, and Langfuse logging for model interactions.   - **Prometheus** counters (`store_count`, `store_latency`).

   * **Background Tasks** – Decay thread, WAL reconciliation, and optional background workers (e.g., vector indexer).   - **OpenTelemetry** automatically instruments PostgreSQL (`psycopg2`) and Qdrant client calls.

   - **Langfuse** captures traces for LLM predictions.

4. **Backends** – Each backend is abstracted behind an interface, allowing alternative implementations (e.g., Milvus, Weaviate) to be plugged in without changing the core logic.

---

5. **Eventing & Consumers** – The Kafka producer emits JSON‑schema‑validated events. Separate consumer services can subscribe to these topics to trigger downstream workflows such as analytics, alerts, or replication.

## Production Guarantees

6. **Observability Stack** – Metrics are exposed on `/metrics` for Prometheus scraping. Traces are exported via the OpenTelemetry SDK, and Langfuse captures model usage for fine‑grained monitoring.- **No mock services** – all external dependencies (PostgreSQL, Qdrant, Redis, Kafka) are real client libraries. The code expects reachable services; if a service is unavailable, the relevant component raises a clear exception.

- **Schema‑validated events** – `eventing/producer.py` validates each memory‑created event against `MEMORY_SCHEMA` before publishing.

---- **TLS / SASL support** – secure connections to PostgreSQL, Qdrant, and Kafka are configurable via environment variables (`POSTGRES_SSL_*`, `QDRANT_TLS*`, `KAFKA_*`).

- **Deterministic testing** – the `TEST` mode uses in‑memory stores (`fakeredis`, `InMemoryVectorStore`) but still runs the full code paths without any mocked network calls.

The architecture is designed for **extensibility**, **observability**, and **production readiness** while retaining a simple development mode for rapid prototyping.

---

## Extensibility
- To add a new vector backend, implement `IVectorStore` and reference it in `factory.create_memory_system`.
- To plug‑in a custom prediction service, implement `IPredictionProvider` and add a config block under `external_prediction`.
- To replace the graph engine, provide a class implementing `IGraphStore`.

---

*All components are described in the source code (`core.py`, `factory.py`, `implementations/*`). This document provides the high‑level view for developers and operators.*

## SomaFractalMemoryEnterprise: Modular Agentic Memory System

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
- Add monitoring/alerting (Prometheus, Grafana).
- Implement multi-agent support (namespaces, agent IDs).

### 5. Advanced Agent Features & Community (Ongoing)
- Memory prioritization, compression, and pruning.
- Knowledge graph sync (optional, for advanced users).
- Policy/safety layer for LLM and memory usage.
- Documentation, quickstart templates, and plugin system.

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

## Secure Connections (TLS / SASL)

The system supports encrypted connections to external services via environment variables. These variables are read by the respective client implementations:

- **PostgreSQL** – `POSTGRES_SSL_MODE` (`disable`/`require`/`verify-ca`/`verify-full`) and optional `POSTGRES_SSL_ROOT_CERT`, `POSTGRES_SSL_CERT`, `POSTGRES_SSL_KEY`.
- **Qdrant** – `QDRANT_TLS` (`true`/`false`) and optional `QDRANT_TLS_CERT`.
- **Kafka** – `KAFKA_SECURITY_PROTOCOL` (`PLAINTEXT`/`SSL`/`SASL_SSL`), `KAFKA_SSL_CA_LOCATION`, `KAFKA_SASL_MECHANISM`, `KAFKA_SASL_USERNAME`, `KAFKA_SASL_PASSWORD`.

These settings enable end‑to‑end encryption without code changes, suitable for production deployments.

## Optional Redis Cache Flag

In **development** mode the `PostgresRedisHybridStore` can use Redis as an optional cache. Control this via the configuration key `redis.enabled` (default `true`). Setting it to `false` disables the Redis cache, causing the store to fall back to pure PostgreSQL. This is useful for minimal CI environments or when Redis is unavailable.

```yaml
redis:
  enabled: false
```

## Key Principles

- **Pluggable:** Swap any module (storage, prediction, graph) via config.
- **Unified API:** All agent code interacts with a single, stable interface.
- **Agent-Aware:** Self-reflection, memory prioritization, and meta-memory built in.
- **Scalable:** Grows from laptop to enterprise cluster with config change.
- **Observable:** Easy to debug, monitor, and optimize.

## Improvement Opportunities

- Modular, pluggable architecture for future-proofing
- Unified API for all modes
- Agent-centric features: self-reflection, memory prioritization, compression
- Observability: logging, metrics, dashboard
- Multi-agent support and knowledge graph integration
- Policy/safety layer for LLM and memory usage
- Community plugins and extensibility

*This document is a living architecture and action plan for the SomaFractalMemoryEnterprise agentic memory system. Update as the project evolves!*
