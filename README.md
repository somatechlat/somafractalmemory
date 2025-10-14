# Soma Fractal Memory (SFM)

---

## 📖 Overview
**Soma Fractal Memory (SFM)** is a modular, agent-centric memory system written in Python. It provides a unified interface for storing, recalling, and linking memories across a distributed backend, including Redis, PostgreSQL, Qdrant, and Kafka. The system is designed for AI agents, knowledge-graph pipelines, and any application that requires fast, context-aware recall of prior events.

---

## ✨ Key Features
- **Hybrid Storage**: Combines Redis for caching, PostgreSQL for durable storage, and Qdrant for vector search.
- **Event-Driven Architecture**: Uses Kafka for asynchronous event processing, ensuring eventual consistency and decoupling of components.
- **Semantic Search**: Leverages transformer-based embeddings for semantic recall.
- **Graph-Based Memory**: Supports linking memories to create a semantic graph.
- **"Fast Core" In-Memory Cache**: An optional, in-process cache for ultra-low-latency recall.
- **Docker and Kubernetes Ready**: Comes with Docker Compose files and a Helm chart for easy deployment.

---

## 🚀 Getting Started

The best way to get started is to follow the **[Quickstart Guide](docs/QUICKSTART.md)**, which provides step-by-step instructions for setting up the development environment and running the full stack.

---

## 📚 Documentation

- **[Developer User Manual](docs/DEVELOPER_MANUAL.md)**: The complete, enterprise-grade guide for developers.
- **[Quickstart Guide](docs/QUICKSTART.md)**: A high-level guide to getting the project running quickly.
- **[API Reference](docs/api.md)**: Detailed information about the API endpoints.

---

## 🤝 Contributing

We welcome contributions! Please see the **[Developer Guide](docs/DEVELOPER_GUIDE.md)** for information on how to get started.

---

*© 2025 SomaTechLat – All rights reserved.*
