---
title: "Python SDK Integration Guide"
purpose: "Guide users on using the Python SDK"
audience: "Python developers"
last_updated: "2025-10-16"
review_frequency: "quarterly"
---

# Python SDK Integration Guide

## Overview

The SomaFractalMemory Python SDK provides a high-level interface for interacting with the memory system. This guide covers installation, configuration, and common usage patterns.

## Installation

### Via pip
```bash
pip install somafractalmemory
```

### From source
```bash
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory
pip install -e .
```

## Quick Start

### Basic Usage
```python
from somafractalmemory import Client

# Initialize client
client = Client(
    api_key="your-api-key",
    endpoint="https://api.somafractalmemory.com"
)

# Store a memory
memory = client.store(
    content="Important information",
    metadata={"type": "note"}
)

# Retrieve a memory
retrieved = client.get(memory.id)
```

## Core Features

### Memory Operations

#### Store Memory
```python
# Simple storage
memory = client.store(
    content="Example content",
    metadata={"type": "note"}
)

# With vector
memory = client.store(
    content="Vector example",
    vector=[0.1, 0.2, 0.3],
    metadata={"type": "embedding"}
)

# Batch storage
memories = client.store_batch([
    {"content": "Memory 1"},
    {"content": "Memory 2"}
])
```

#### Retrieve Memory
```python
# By ID
memory = client.get("mem_123")

# Multiple IDs
memories = client.get_many(["mem_123", "mem_456"])

# With metadata
memory = client.get("mem_123", include_metadata=True)
```

### Vector Operations

#### Vector Search
```python
# Search by vector
results = client.search_vector(
    vector=[0.1, 0.2, 0.3],
    limit=5,
    threshold=0.7
)

# Search with filters
results = client.search_vector(
    vector=[0.1, 0.2, 0.3],
    filters={"type": "document"},
    limit=5
)
```

#### Text Search
```python
# Semantic search
results = client.search_text(
    text="example query",
    limit=5
)

# Hybrid search
results = client.search_hybrid(
    text="example query",
    filters={"date": {"$gt": "2025-01-01"}},
    limit=5
)
```

### Graph Operations

#### Create Links
```python
# Link memories
client.link(
    source_id="mem_123",
    target_id="mem_456",
    relationship="references"
)

# Batch link creation
client.link_batch([
    {
        "source": "mem_1",
        "target": "mem_2",
        "relationship": "refers-to"
    },
    {
        "source": "mem_2",
        "target": "mem_3",
        "relationship": "contains"
    }
])
```

#### Graph Queries
```python
# Find path
path = client.find_path(
    start_id="mem_123",
    end_id="mem_789",
    max_depth=3
)

# Graph traversal
related = client.traverse(
    start_id="mem_123",
    relationship="references",
    direction="outgoing",
    max_depth=2
)
```

## Advanced Features

### Async Operations
```python
import asyncio
from somafractalmemory import AsyncClient

async def main():
    client = AsyncClient()

    # Async store
    memory = await client.store(
        content="Async example"
    )

    # Async search
    results = await client.search_vector(
        vector=[0.1, 0.2, 0.3]
    )

asyncio.run(main())
```

### Streaming
```python
# Stream memories
for memory in client.stream_memories(query="example"):
    print(memory.content)

# Stream search results
for result in client.stream_search(
    vector=[0.1, 0.2, 0.3]
):
    print(result.score)
```

### Batch Operations
```python
# Batch processing with callback
def process_memory(memory):
    print(f"Processing {memory.id}")

client.process_batch(
    memories=["mem_1", "mem_2", "mem_3"],
    callback=process_memory,
    batch_size=10
)
```

## Configuration

### Client Options
```python
client = Client(
    api_key="your-api-key",
    endpoint="https://api.somafractalmemory.com",
    timeout=30,
    max_retries=3,
    pool_connections=10,
    cache_enabled=True
)
```

### Environment Variables
```bash
export SOMA_API_KEY="your-api-key"
export SOMA_ENDPOINT="https://api.somafractalmemory.com"
export SOMA_TIMEOUT=30
```

## Error Handling

### Exception Types
```python
from somafractalmemory.exceptions import (
    MemoryNotFound,
    AuthenticationError,
    RateLimitExceeded
)

try:
    memory = client.get("mem_123")
except MemoryNotFound:
    print("Memory not found")
except AuthenticationError:
    print("Authentication failed")
except RateLimitExceeded:
    print("Rate limit exceeded")
```

### Retry Handling
```python
from somafractalmemory import RetryConfig

client = Client(
    retry_config=RetryConfig(
        max_retries=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504]
    )
)
```

## Best Practices

1. **Connection Management**
   ```python
   # Use context manager
   with Client() as client:
       memory = client.store("Example")
   ```

2. **Resource Cleanup**
   ```python
   # Clean up resources
   client.close()
   ```

3. **Batch Processing**
   ```python
   # Process in batches
   for batch in client.iter_batch(items, size=100):
       client.process_batch(batch)
   ```

## Monitoring

### Health Checks
```python
# Check service health
status = client.health_check()
print(status.components)

# Check specific component
cache_status = client.health_check("cache")
```

### Metrics
```python
# Get client metrics
metrics = client.metrics()
print(metrics.requests_total)

# Component metrics
vector_metrics = client.component_metrics("vector_store")
```

## Examples

### Complete Example
```python
from somafractalmemory import Client, RetryConfig

# Configure client
client = Client(
    api_key="your-api-key",
    retry_config=RetryConfig(max_retries=3)
)

try:
    # Store memory
    memory = client.store(
        content="Example content",
        metadata={"type": "note"},
        vector=[0.1, 0.2, 0.3]
    )

    # Search similar
    results = client.search_vector(
        vector=memory.vector,
        limit=5
    )

    # Create links
    for result in results:
        client.link(
            source_id=memory.id,
            target_id=result.id,
            relationship="similar-to"
        )

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
```

## Further Reading
- [API Reference](../../development-manual/api-reference.md)
- [Vector Operations](../features/vector-search.md)
- [Graph Operations](../features/graph-relations.md)
- [Performance Guide](../../technical-manual/performance.md)
