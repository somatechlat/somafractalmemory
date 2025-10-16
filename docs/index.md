---
title: "SomaFractalMemory Documentation"
purpose: "Main documentation hub following 4-manual structure"
audience:
  - "All Stakeholders"
version: "1.0.0"
last_updated: "2025-10-16"
review_frequency: "quarterly"
---

# SomaFractalMemory Documentation

**Enterprise AI Memory System for Distributed Applications**

## The Four Core Manuals

| Manual | Audience | Purpose |
|---|---|---|
| **[User Manual](user-manual/index.md)** | End-Users, Product Managers | How to *use* the system |
| **[Technical Manual](technical-manual/index.md)** | SREs, DevOps, System Administrators | How to *deploy and operate* |
| **[Development Manual](development-manual/index.md)** | Software Engineers, Contributors | How to *build and contribute* |
| **[Onboarding Manual](onboarding-manual/index.md)** | New Team Members, Agent Coders | How to *quickly become productive* |

## Quick Start

1. **Users**: [Installation Guide](user-manual/installation.md) → [Quick Start Tutorial](user-manual/quick-start-tutorial.md)
2. **Operators**: [Deployment Guide](technical-manual/deployment.md) → [Monitoring Setup](technical-manual/monitoring.md)
3. **Developers**: [Local Setup](development-manual/local-setup.md) → [API Reference](development-manual/api-reference.md)
4. **New Team**: [Project Context](onboarding-manual/project-context.md) → [Environment Setup](onboarding-manual/environment-setup.md)

## System Overview
- **Enterprise AI Memory System** with vector search, graph relationships, and distributed architecture
- **Multi-backend storage**: PostgreSQL + Redis + Qdrant + Kafka
- **Interfaces**: FastAPI HTTP, gRPC, CLI, Python library
- **Use cases**: AI agents, knowledge management, semantic search
