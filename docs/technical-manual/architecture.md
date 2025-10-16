---
title: "System Architecture"
purpose: "High-level system design and component interactions"
audience: "Architects, DevOps, technical leads"
last_updated: "2025-10-16"
review_frequency: "quarterly"
---

# System Architecture

## Overview

SomaFractalMemory is a distributed memory system combining vector search, graph relationships, and multi-tier caching for high-performance semantic memory operations.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer                             │
│  (HTTP / gRPC / CLI)  →  Port 40020                        │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼──────────────────────────────────────────────┐
│              SomaFractalMemory Service                        │
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
