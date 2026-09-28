# SOMA-SFM-GUIDE-USER-001 — User Guide

## Document Control

| Field | Value |
|---|---|
| Document Title | User Guide |
| Document Identifier | SOMA-SFM-GUIDE-USER-001 |
| Version | 1.1.0 |
| Date | 2026-09-28 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2026-12-28 |


## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-09-28 | SomaTech Engineering | Initial issue. Brought under the house ISO document-control contract. |
| 1.1.0 | 2026-09-28 | SomaTech Engineering | Restructured into one document. The file was five separately scaffolded sections concatenated together, each carrying its own H1 and an "automated documentation scaffolding tool" footer, and its table of contents linked to `installation.md`, `quick-start.md`, `features.md` and `faq.md`, none of which exist as files. Those four sections are in this document; they are now real in-page anchors. Removed a reStructuredText `toctree` directive, which is Sphinx syntax and has no effect in MkDocs. |

## Contents

- [Installation](#installation)
- [Quick-Start](#quick-start)
- [Features](#features)
- [Frequently Asked Questions](#frequently-asked-questions)

All guides assume the platform is running locally on macOS or Linux. For
production deployments see [`PRODUCTION_READINESS.md`](PRODUCTION_READINESS.md).

---

## Installation

This section walks through installing **SomaFractalMemory** on a local macOS or
Linux development machine.

### Prerequisites

* Python **3.12+**
* Docker Engine + Docker Compose v2 (required for PostgreSQL, Redis, Milvus, etc.)
* Git
* A POSIX-compatible shell (`zsh` is the default on macOS).

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/somatechlat/somafractalmemory
   cd somafractalmemory
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install the package and development extras**
   ```bash
   pip install -U pip
   pip install -e ".[dev]"
   ```

4. **Create and configure the environment file**
   ```bash
   cp .env.example .env
   echo "SOMA_API_TOKEN=<set-a-real-token>" >> .env
   ```

5. **Start the supporting services**
   ```bash
   docker compose -f infra/standalone/docker-compose.yml up -d
   ```
   This brings up PostgreSQL, Redis, Milvus, and the API.

6. **Verify the API is healthy**
   ```bash
   curl -fsS http://127.0.0.1:10101/healthz
   ```
   You should see `true`.

7. **Run the test suite** (optional but recommended)
   ```bash
   pytest -q
   ```

You are now ready to interact with the API as described in
[Quick-Start](#quick-start).

---

## Quick-Start

Minimal steps to store and retrieve a memory using the HTTP API.

### 1. Start the stack

```bash
docker compose -f infra/standalone/docker-compose.yml up -d
```

The API will be reachable at `http://127.0.0.1:10101`.

### 2. Set the API token

```bash
export SOMA_API_TOKEN="your-token"
```

### 3. Store a memory

```bash
curl -s -X POST http://127.0.0.1:10101/memories \
  -H "Authorization: Bearer $SOMA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"coord":"1.0,2.0,3.0","payload":{"message":"Hello"},"memory_type":"semantic"}'
```

You should receive a `200` response with the stored memory ID.

### 4. Retrieve the memory by coordinate

```bash
curl -s http://127.0.0.1:10101/memories/1.0,2.0,3.0 \
  -H "Authorization: Bearer $SOMA_API_TOKEN"
```

### 5. Search by query

```bash
curl -s -X POST http://127.0.0.1:10101/memories/search \
  -H "Authorization: Bearer $SOMA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"Hello","top_k":5}'
```

The response contains the most similar memories.

---

## Features

### Core features

| Feature | Description |
|---------|-------------|
| **Episodic Memory** | Store arbitrary JSON payloads indexed by a coordinate vector. Retrieval by exact coordinate. |
| **Semantic Memory** | Store payloads with vector embeddings (via Milvus) enabling similarity search. |
| **Graph Store** | Relationships between memories are captured in a NetworkX graph for traversals and reasoning. |
| **Versioning** | Each memory version is retained, allowing rollback and audit trails. |
| **Bulk Operations** | Batch insert and delete APIs for high-throughput ingestion. |
| **Health & Metrics** | `/healthz`, `/readyz` endpoints and Prometheus-compatible metrics. |
| **Extensible Provider Architecture** | Plug-in new KV, vector, or graph back-ends by implementing the provider interfaces. |

### Non-functional characteristics

* **Scalable** – Horizontal scaling via Docker Compose; each component can be
  replaced with a managed cloud service.
* **Secure** – Token-based authentication; TLS termination can be added via a
  reverse proxy.
* **Observability** – Structured logging, OpenTelemetry traces (optional).

---

## Frequently Asked Questions

### General

**Q: What is the difference between *episodic* and *semantic* memory?**
A: *Episodic* memory stores the payload exactly as-provided and is retrieved by
the exact coordinate key. *Semantic* memory also stores the payload but creates a
vector embedding (via Milvus) that enables similarity search based on content.

**Q: Do I need Docker to run the system?**
A: Docker is required for the supporting services (PostgreSQL, Redis, Milvus).
The API is a Django + Django Ninja service and can be run locally without Docker
if you provide alternative back-ends.

### Authentication & security

**Q: How is authentication handled?**
A: The API expects a bearer token in the `Authorization` header. Set
`SOMA_API_TOKEN` in your environment (or `.env`) to match the running API.

**Q: Can I run the API behind a TLS reverse proxy?**
A: Yes. The API does not terminate TLS itself; you can place an Nginx or Traefik
proxy in front of it.

### Operations

**Q: How do I delete a memory?**
A: Use the `DELETE /memories/{coord}` endpoint. This removes the entry from the
KV store, vector store, and graph store.

**Q: How can I bulk-load many memories?**
A: The API currently exposes `POST /memories` and `POST /memories/search`. Bulk
ingest is not part of the current HTTP surface.

### Development

**Q: Where can I find the API OpenAPI schema?**
A: Visit `http://127.0.0.1:10101/openapi.json` when the server is running.

**Q: How do I run the test suite?**
A: Inside the virtual environment run `pytest -q`. Linting with `ruff check .`
and type checking with `mypy somafractalmemory` are also recommended.

End of Document
