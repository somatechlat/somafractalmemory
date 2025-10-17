---
title: "System Architecture"
purpose: "High-level system design and component interactions for SomaFractalMemory."
audience:
  - "Architects"
  - "DevOps engineers"
  - "Technical leads"
last_updated: "2025-10-17"
review_frequency: "quarterly"
---

# System Architecture

SomaFractalMemory is delivered as a FastAPI application that orchestrates persistent storage (PostgreSQL), caching (Redis), and vector search (Qdrant). All environments expose the same port assignments defined in `.env.template`.

## Component Summary

| Component | Purpose | Exposed Port | Container Port |
|-----------|---------|--------------|----------------|
| FastAPI (`somafractalmemory.http_api`) | `/memories` CRUD + operational probes | 9595 | 9595 |
| PostgreSQL | Durable memory payload storage | 40021 | 5432 |
| Redis | Rate limiting + ephemeral cache | 40022 | 6379 |
| Qdrant | Vector similarity search | 40023 | 6333 |
| gRPC listener (reserved) | Future binary API surface | 50053 | 50053 |

## Security Boundaries

- `/memories*` requires a bearer token set via `SOMA_API_TOKEN`; health and metrics endpoints remain public but throttled.
- Secrets are injected through environment variables or mounted files—refer to the [Secrets Policy](security/secrets-policy.md) for rotation cadence.
- The gRPC port (`50053`) is reserved but not exposed; firewall rules only need to cover the HTTP port 9595 today.

## Service Topology

```
┌─────────────────────────────────────────┐
│             Client Layer                │
│        (HTTP ➜ Port 9595)               │
└─────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         SomaFractalMemory Service       │
│ ┌─────────────────────────────────────┐ │
│ │  API Layer (FastAPI HTTP)          │ │
│ ├─────────────────────────────────────┤ │
│ │  Core Logic (memory/vector/graph)  │ │
│ └─────────────────────────────────────┘ │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼───────────────┬───────────────┐
    │             │               │               │
    ▼             ▼               ▼               ▼
┌────────┐   ┌────────┐     ┌────────┐     ┌───────────┐
│Postgres│   │ Redis  │     │ Qdrant │     │ Observability │
│40021→5432│ │40022→6379│ │40023→6333│ │ Logs & Metrics │
└────────┘   └────────┘     └────────┘     └───────────┘
```

## Data Flow

### Memory Storage
```
Client → API (9595) → Memory Manager → PostgreSQL (40021)
                                      ↓
                                  Redis Cache (40022)
```

### Vector Search
```
Client → API (9595) → Vector Engine → Qdrant (40023)
                      ↓
                    Redis Cache (40022)
```

### Graph Relations
```
Client → API (9595) → Graph Manager → PostgreSQL (40021)
```

## Deployment Models

### Kubernetes (Production)

- Helm chart deploys Deployments + Services with the unified ports above.
- StatefulSets manage PostgreSQL, Redis, and Qdrant with optional persistence classes.
- ConfigMaps and Secrets supply runtime configuration and credentials.
- Horizontal Pod Autoscaler can scale the API deployment independently of backing stores.

### Docker Compose (Development/QA)

- Single-node stack mirrors production components and ports.
- Bind mounts provide live code reload (`./:/app:delegated`).
- Health checks mirror Kubernetes readiness probes.
- Environment settings derive from `.env.template` for consistency.

## Scaling Considerations

### Horizontal Scaling

- Add FastAPI replicas behind ingress or a load balancer.
- Enable PostgreSQL read replicas for analytics workloads.
- Promote Redis to clustered mode for high write traffic.
- Shard or replicate Qdrant collections to maintain low search latency.

### Vertical Scaling

- Increase CPU/memory resources on API pods when latency spikes.
- Tune PostgreSQL shared buffers and connection pools.
- Adjust Redis max memory and eviction policy for workload characteristics.
- Configure Qdrant optimizers (HNSW parameters) to match dataset size.

## Further Reading
- [Deployment Guide](deployment.md)
- [Monitoring Guide](monitoring.md)
- [Security Policy](security/secrets-policy.md)
