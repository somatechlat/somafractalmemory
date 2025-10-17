# Architecture Overview---

title: "System Architecture"

SomaFractalMemory is delivered as a FastAPI application backed by modular storage backends. The current production architecture contains the following components:purpose: "High-level system design and component interactions"

audience: "Architects, DevOps, technical leads"

| Component | Purpose | Default Port |last_updated: "2025-10-16"

|-----------|---------|--------------|review_frequency: "quarterly"

| FastAPI service (`somafractalmemory.http_api`) | Exposes the `/memories` CRUD/search surface and operational probes. | 9595 |---

| PostgreSQL | Durable key-value store for memory payloads and metadata. | 5433 |

| Qdrant | Vector similarity search for hybrid recall. | 6333 |# System Architecture

| Redis | Optional distributed rate limiter backing store; falls back to in-memory if unavailable. | 6381 |

| Prometheus | Scrapes `/metrics` for latency and throughput dashboards. | 9090 |## Overview



## Data FlowSomaFractalMemory is a distributed memory system combining vector search, graph relationships, and multi-tier caching for high-performance semantic memory operations.



1. Clients authenticate using a Bearer token and invoke `POST /memories` with a coordinate and payload.## Component Architecture

2. The API writes JSON payloads to PostgreSQL, embeds text via the configured model (hash-only in CI/local), and upserts vectors into Qdrant.

3. Retrieval uses `GET /memories/{coord}` to fetch canonical JSON, while searches call `POST /memories/search` which delegates to the hybrid recall pipeline in `core.py`.```

4. Deletes remove entries from PostgreSQL, Qdrant, and invalidates rate-limiter buckets.┌─────────────────────────────────────────────────────────────┐

│                    Client Layer                             │

## Security Boundaries│  (HTTP / gRPC / CLI)  →  Port 40020                        │

└────────────────┬────────────────────────────────────────────┘

- Only the `/memories` routes require authentication; `/stats`, `/health*`, `/metrics`, `/ping`, and `/` remain public but rate limited.                 │

- Tokens are sourced from `SOMA_API_TOKEN` or `SOMA_API_TOKEN_FILE`. No other auth schemes are supported.┌────────────────▼──────────────────────────────────────────────┐

- Secrets are stored in environment variables or mounted files; see [Security Policy](security/secrets-policy.md).│              SomaFractalMemory Service                        │

│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Layer (HTTP/gRPC)  →  Port 40020               │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  Core Logic (Memory, Vector, Graph Managers)        │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┬────────────┬────────────┐
    │            │            │            │            │
    ▼            ▼            ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│ Postgres│  │ Redis  │  │ Qdrant │  │ Kafka  │  │ Logs   │
│40021    │  │40022   │  │40023   │  │40024   │  │outputs │
└────────┘  └────────┘  └────────┘  └────────┘  └────────┘
```

## Service Port Map (40020 Range)

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| **API** | 40020 | HTTP/gRPC | Client entry point |
| **PostgreSQL** | 40021 | TCP | Persistent memory storage |
| **Redis** | 40022 | TCP | Hot cache layer |
| **Qdrant** | 40023 | HTTP | Vector similarity search |
| **Kafka** | 40024 | TCP | Event bus (optional) |

## Data Flow

### Memory Storage
```
Client → API (40020) → Memory Manager → PostgreSQL (40021)
                                      ↓
                                  Redis Cache (40022)
```

### Vector Search
```
Client → API (40020) → Vector Engine → Qdrant (40023)
                      ↓
                    Redis Cache (40022)
```

### Graph Relations
```
Client → API (40020) → Graph Manager → PostgreSQL (40021)
```

### Event Processing
```
API (40020) → Kafka (40024) → Workers → Services
```

## Deployment Models

### Kubernetes (Production)

- Multi-replica services with load balancing
- StatefulSets for databases
- ConfigMaps for configuration
- Secrets for credentials
- PersistentVolumeClaims for data

### Docker Compose (Development)

- Single-node deployment
- Shared volumes for persistence
- Health checks on all services
- Profile-based service selection

## Scaling Architecture

### Horizontal Scaling

- Multiple API replicas behind load balancer
- PostgreSQL read replicas for query distribution
- Redis cluster mode for distributed caching
- Kafka multi-broker cluster

### Vertical Scaling

- Increase resource limits for CPU/memory
- Configure Qdrant index settings
- Adjust cache eviction policies
- Tune connection pool sizes

## Further Reading
- [Deployment Guide](deployment.md)
- [Monitoring Guide](monitoring.md)
- [Scaling Guide](scaling.md)
- [Troubleshooting Guide](troubleshooting.md)
