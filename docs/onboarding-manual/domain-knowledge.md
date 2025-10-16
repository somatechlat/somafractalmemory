# Domain Knowledge

## Core Concepts

### Memory Management

Soma Fractal Memory uses a hierarchical system based on:

1. **Importance Scoring**
   - Algorithmic importance calculation
   - Decay over time
   - Access frequency weighting

2. **Vector Embeddings**
   - Hash-based embeddings
   - Similarity search
   - Dimensional reduction

3. **Storage Hierarchy**
   - Hot data in Redis
   - Warm data in PostgreSQL
   - Vector search in Qdrant

## Key Algorithms

### 1. Importance Calculation

```python
def calculate_importance(age: float, access_count: int) -> float:
    """Calculate memory importance score.

    Args:
        age: Time since creation in seconds
        access_count: Number of accesses

    Returns:
        Normalized importance score (0-1)
    """
    raw_score = access_count / (1 + age / 3600)
    return min(1.0, raw_score / 100)
```

### 2. Memory Decay

- Linear decay over time
- Configurable thresholds
- Importance-based pruning

## Data Models

### Memory Entry
```json
{
  "id": "uuid",
  "content": "memory content",
  "importance": 0.8,
  "created_at": "timestamp",
  "last_accessed": "timestamp",
  "access_count": 42,
  "vector": [0.1, 0.2, ...]
}
```

## Integration Points

### 1. External Systems
- Kafka for events
- Prometheus for metrics
- Jaeger for tracing

### 2. Internal Services
- PostgreSQL for persistence
- Redis for caching
- Qdrant for vector search

## Performance Characteristics

### Latency Targets

| Operation | Target | p95 |
|-----------|--------|-----|
| Store | 50ms | 100ms |
| Recall | 100ms | 200ms |
| Search | 200ms | 500ms |

### Scaling Limits

- Maximum memories: 1M per namespace
- Vector dimensions: 768
- Maximum payload size: 1MB

## Common Patterns

### 1. Memory Storage
```python
# Store with importance
await memory.store({
    "content": "data",
    "importance": 0.8
})

# Auto-calculated importance
await memory.store("data")
```

### 2. Memory Retrieval
```python
# Direct lookup
result = await memory.get(memory_id)

# Similarity search
results = await memory.search("query", limit=10)
```

## Advanced Topics

1. **Sharding Strategy**
   - Namespace-based sharding
   - Consistent hashing
   - Cross-shard queries

2. **Caching Patterns**
   - Write-through cache
   - LRU eviction
   - Cache coherence

3. **Failure Handling**
   - Circuit breakers
   - Retry policies
   - Fallback strategies
