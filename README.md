# Soma Fractal Memory (SFM)

## Overview
Soma Fractal Memory (SFM) is a modular, agent‑centric memory system in Python. It exposes a unified interface to store, recall, and link memories using:
- PostgreSQL (canonical KV store) with Redis as cache
- Qdrant for vector similarity search
- Optional Kafka eventing for asynchronous pipelines
- A semantic graph in NetworkX

It ships with a FastAPI service, a CLI, and a gRPC service, plus Docker Compose and a Helm chart for deployment.

## Key features
- Hybrid storage (Postgres + Redis) and vector search (Qdrant)
- Hybrid recall (vector similarity with optional keyword boosts)
- Graph links and traversal
- Optional in‑process “Fast Core” slab index for ultra‑low latency
- Prometheus metrics and optional OpenTelemetry tracing
- Docker/Compose and Helm/Kubernetes ready

## Quick start

Local stack with Docker Compose:

1) Build images
2) Start services

The Makefile provides shortcuts:

- Build and start: `make compose-build` then `make compose-up`
- Tail API logs: `make compose-logs`
- Stop: `make compose-down`

The API will listen on http://127.0.0.1:9595. Most endpoints require a bearer token. Compose sets `SOMA_API_TOKEN=devtoken` by default; add header `Authorization: Bearer devtoken`.

## Documentation

- Developer Manual: `docs/DEVELOPER_MANUAL.md`
- API Reference: `docs/api.md`
- Roadmap: `docs/ROADMAP.md`

## Contributing

Contributions are welcome. See `docs/DEVELOPER_MANUAL.md` for development workflows.

© 2025 SomaTechLat – All rights reserved.
