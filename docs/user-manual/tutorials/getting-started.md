---
title: "Getting Started with SomaFractalMemory"
purpose: "Guide users through their first memory storage and recall operations"
audience:
  - "New Users"
  - "Application Developers"
prerequisites:
  - "API access token"
  - "Docker installed"
version: "1.0.0"
last_updated: "2025-10-15"
review_frequency: "quarterly"
---

# Getting Started with SomaFractalMemory

## Overview

This tutorial will guide you through setting up SomaFractalMemory and performing basic operations.

```mermaid
graph LR
    A[Setup Environment] --> B[Store Memory]
    B --> C[Create Links]
    C --> D[Recall Memory]
    D --> E[Explore Graph]
```

## System Architecture

Before we begin, let's understand how the components interact:

```mermaid
flowchart TB
    subgraph Client["Your Application"]
        API[REST API Client]
    end

    subgraph SFM["SomaFractalMemory"]
        Server[API Server]
        Vector[Vector Store]
        Graph[Graph Store]
        Cache[Cache Layer]
    end

    API -->|HTTP Request| Server
    Server -->|Store/Recall| Vector
    Server -->|Link/Navigate| Graph
    Server <-->|Fast Access| Cache
```

## Step 1: Setting Up Your Environment

1. Start the services:
   ```bash
   docker compose up -d
   ```

   System status diagram:
   ```mermaid
   stateDiagram-v2
   [*] --> Starting
   Starting --> Initializing: Services Starting
   Initializing --> Ready: Health Checks Pass
   Ready --> [*]
   ```

2. Verify the system is ready:
   ```bash
   curl http://localhost:9595/health
   ```

## Step 2: Storing Your First Memory

### Memory Structure
```mermaid
classDiagram
    class Memory {
        +String text
        +Vector coordinate
        +Float importance
        +Dict metadata
    }
    class Vector {
        +Float[] dimensions
        +normalize()
    }
    Memory --> Vector
```

### Example Request
```bash
curl -X POST http://localhost:9595/store \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "coord": "1.0,2.0,3.0",
    "payload": {
      "text": "My first memory",
      "type": "episodic"
    },
    "importance": 0.8
  }'
```

## Step 3: Creating Memory Links

### Link Structure
```mermaid
graph LR
    A[Memory A] -->|type: related| B[Memory B]
    A -->|type: causal| C[Memory C]
    B -->|type: temporal| D[Memory D]
```

### Example Link Creation
```bash
curl -X POST http://localhost:9595/link \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_coord": "1.0,2.0,3.0",
    "to_coord": "4.0,5.0,6.0",
    "type": "related",
    "weight": 1.0
  }'
```

## Step 4: Memory Recall

### Recall Process
```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    participant V as Vector Store
    participant G as Graph Store

    C->>S: POST /recall
    S->>V: Search similar vectors
    V-->>S: Return matches
    S->>G: Get linked memories
    G-->>S: Return links
    S-->>C: Combined results
```

### Example Recall
```bash
curl -X POST http://localhost:9595/recall \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "first memory",
    "top_k": 5
  }'
```

## Step 5: Exploring the Memory Graph

### Graph Navigation
```mermaid
graph TD
    A[Start Memory] --> B[Related Memory 1]
    A --> C[Related Memory 2]
    B --> D[Linked Memory 1.1]
    B --> E[Linked Memory 1.2]
    C --> F[Linked Memory 2.1]

    style A fill:#f9f,stroke:#333,stroke-width:4px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
```

### Finding Neighbors
```bash
curl "http://localhost:9595/neighbors?coord=1.0,2.0,3.0" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Performance Considerations

### Memory Access Patterns
```mermaid
graph TD
    subgraph "Fast Path"
        Cache[Cache Layer]
    end
    subgraph "Standard Path"
        Vector[Vector Store]
        Graph[Graph Store]
    end

    Request --> Cache
    Cache -->|Cache Miss| Vector
    Cache -->|Cache Miss| Graph
    Vector --> Response
    Graph --> Response
    Cache -->|Cache Hit| Response
```

### Response Times
| Operation | Typical Latency |
|-----------|----------------|
| Store | < 100ms |
| Recall | < 50ms |
| Link | < 30ms |
| Neighbor Query | < 20ms |

## Next Steps
- [Advanced Features](../features/index.md)
- [API Reference](../../development-manual/api-reference.md)
- [Performance Tuning](../../technical-manual/performance.md)

## Troubleshooting

### Common Issues
```mermaid
graph TD
    A[Issue] --> B{Type?}
    B -->|Connection| C[Check Services]
    B -->|Authorization| D[Verify Token]
    B -->|Performance| E[Check Load]

    C --> F[Docker Status]
    C --> G[Health Check]
    D --> H[Token Format]
    D --> I[Permissions]
    E --> J[Monitor CPU]
    E --> K[Monitor Memory]
```

### Status Codes
| Code | Meaning | Solution |
|------|----------|----------|
| 401 | Invalid token | Check authorization header |
| 404 | Memory not found | Verify coordinates |
| 429 | Rate limit | Reduce request frequency |

## Support Resources
- [Community Forum](https://community.somafractalmemory.com)
- [GitHub Issues](https://github.com/yourusername/somafractalmemory/issues)
- [API Status](https://status.somafractalmemory.com)
