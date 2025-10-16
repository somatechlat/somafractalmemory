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

The API will listen on http://127.0.0.1:9595. Most endpoints require a bearer token. Compose sets `SOMA_API_TOKEN=devtoken` by default; add header `Authorization: Bearer devtoken`. The Kubernetes deployment uses port `9393` by default.

## Documentation

**📚 [Complete Documentation Hub](docs/index.md)** - Four-manual structure following enterprise standards

| Manual | Purpose | Start Here |
|--------|---------|------------|
| 👤 **[User Manual](docs/user-manual/index.md)** | How to use SomaFractalMemory | [Quick Start](docs/user-manual/quick-start-tutorial.md) |
| ⚙️ **[Technical Manual](docs/technical-manual/index.md)** | Deploy & operate the system | [Deployment](docs/technical-manual/deployment.md) |
| 💻 **[Development Manual](docs/development-manual/index.md)** | Build & contribute code | [Local Setup](docs/development-manual/local-setup.md) |
| 🚀 **[Onboarding Manual](docs/onboarding-manual/index.md)** | New team member guide | [Project Context](docs/onboarding-manual/project-context.md) |

## Contributing

See [Contribution Process](docs/development-manual/contribution-process.md) for development workflows and [Coding Standards](docs/development-manual/coding-standards.md).

© 2025 SomaTechLat – All rights reserved.
