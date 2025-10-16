---
title: "System Architecture"
purpose: "To provide a high-level overview of the SomaFractalMemory system architecture."
audience: ["Developers", "SREs"]
version: "1.0.0"
last_updated: "2025-10-16"
---

# System Architecture

SomaFractalMemory is a distributed system composed of several key components:

- **API Server**: A FastAPI application that provides the primary interface for interacting with the memory system.
- **PostgreSQL**: The primary, persistent key-value store for memory data.
- **Redis**: A caching layer in front of PostgreSQL to accelerate frequently accessed data.
- **Qdrant**: A vector database used for high-speed similarity searches.
- **Kafka**: An event bus for asynchronous processing of memory events.

The system is designed to be deployed in a containerized environment, with official support for both Docker Compose and Kubernetes (via Helm).
