---
title: "SomaFractalMemory Glossary"
purpose: "Define key terms and concepts used throughout the documentation"
audience: "All stakeholders"
last_updated: "2025-10-16"
review_frequency: "quarterly"
---

# Glossary

## Core Concepts

### Memory System Terms

| Term | Definition |
|------|------------|
| Memory | A unit of information stored in the system, containing content and metadata |
| Vector | A numerical representation of content used for similarity search |
| Memory Graph | A network of linked memories showing relationships and connections |
| Recall | The process of retrieving memories based on various criteria |

### Technical Components

| Term | Definition |
|------|------------|
| FastAPI | The HTTP API framework used for the REST interface |
| gRPC | Protocol used for high-performance service-to-service communication |
| Qdrant | Vector database used for similarity search operations |
| PostgreSQL | Primary database for structured data storage |
| Redis | In-memory cache for high-speed data access |
| Kafka | Optional event bus for asynchronous processing |

### Data Structures

| Term | Definition |
|------|------------|
| Memory ID | Unique identifier for each stored memory |
| Memory Vector | High-dimensional vector representing memory content |
| Memory Link | A connection between two memories in the graph |
| Memory Payload | Additional metadata attached to a memory |

### Operations

| Term | Definition |
|------|------------|
| Store | Operation to save a new memory |
| Recall | Operation to retrieve memories |
| Link | Operation to create relationships between memories |
| Vector Search | Finding similar memories using vector similarity |

### Deployment Terms

| Term | Definition |
|------|------------|
| Node | A single instance of the memory service |
| Cluster | Multiple nodes working together |
| Shard | A portion of the data stored on a specific node |
| Replica | A backup copy of data for redundancy |

### Performance Terms

| Term | Definition |
|------|------------|
| Latency | Time taken to complete a memory operation |
| Throughput | Number of memory operations per second |
| Cache Hit | When requested data is found in Redis cache |
| Cache Miss | When data must be fetched from primary storage |

### Security Terms

| Term | Definition |
|------|------------|
| API Token | Authentication token for API access |
| RBAC | Role-Based Access Control for permissions |
| mTLS | Mutual TLS for service authentication |
| Encryption at Rest | Protection of stored data |

## Abbreviations

| Abbreviation | Full Form |
|-------------|------------|
| SFM | SomaFractalMemory |
| API | Application Programming Interface |
| KV | Key-Value (storage) |
| TTL | Time To Live |
| SLA | Service Level Agreement |
| SLO | Service Level Objective |

## File Types

| Extension | Purpose |
|-----------|---------|
| .md | Markdown documentation files |
| .py | Python source code |
| .puml | PlantUML diagram source |
| .yaml | Configuration files |
| .json | Data exchange format |

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 500 | Internal Server Error |

## Common Metrics

| Metric | Description |
|--------|-------------|
| rps | Requests per second |
| p95 | 95th percentile latency |
| mem_usage | Memory usage percentage |
| cache_hit_ratio | Cache effectiveness |

## Related Projects

| Project | Relationship |
|---------|-------------|
| Qdrant | Vector search engine |
| FastAPI | Web framework |
| NetworkX | Graph operations |
| OpenTelemetry | Observability |
