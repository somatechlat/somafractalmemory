# Vector Storage

## Overview

Vector storage is the core feature of Soma Fractal Memory, enabling efficient storage and retrieval of high-dimensional vectors with temporal awareness.

## Key Capabilities

### 1. Vector Operations

- Store vectors with metadata
- Query by vector similarity
- Batch operations
- Automatic indexing

### 2. Temporal Features

- Automatic decay over time
- Time-based queries
- Historical snapshots
- Retention policies

### 3. Performance

- Sub-100ms query latency
- 1000+ QPS throughput
- Efficient memory usage
- Optimized indexes

## Usage Examples

### Store Vector

```python
import requests

response = requests.post(
    'http://localhost:9595/api/v1/memory',
    json={
        'vector': [0.1, 0.2, ...],  # 768 dimensions
        'metadata': {
            'source': 'example',
            'timestamp': '2025-10-15T10:00:00Z'
        }
    }
)
```

### Query Similar Vectors

```python
response = requests.post(
    'http://localhost:9595/api/v1/memory/search',
    json={
        'vector': [0.1, 0.2, ...],
        'limit': 10,
        'min_similarity': 0.7
    }
)
```

### Batch Operations

```python
response = requests.post(
    'http://localhost:9595/api/v1/memory/batch',
    json={
        'vectors': [
            {
                'vector': [0.1, 0.2, ...],
                'metadata': {'source': 'batch1'}
            },
            {
                'vector': [0.3, 0.4, ...],
                'metadata': {'source': 'batch2'}
            }
        ]
    }
)
```

## Configuration

```yaml
# config.yaml
vector_storage:
  dimension: 768
  similarity_metric: 'cosine'
  index_type: 'hnsw'
  decay:
    enabled: true
    rate: 0.1
    min_threshold: 0.1
```

## Performance Tuning

### Index Configuration

```yaml
index:
  M: 16  # Max number of connections
  efConstruction: 200  # Index quality
  efSearch: 100  # Search quality
```

### Memory Settings

```yaml
memory:
  cache_size: '2GB'
  max_vectors: 1000000
  batch_size: 1000
```

## Best Practices

1. **Vector Normalization**
   - Normalize vectors before storage
   - Use consistent dimensionality
   - Handle missing values

2. **Batch Operations**
   - Use batch API for bulk operations
   - Consider chunk size (1000 recommended)
   - Monitor memory usage

3. **Query Optimization**
   - Use appropriate similarity threshold
   - Include relevant metadata filters
   - Monitor query latency

## Monitoring

### Key Metrics

| Metric | Description | Warning | Critical |
|--------|-------------|----------|----------|
| vector_count | Total stored vectors | >80% capacity | >90% capacity |
| query_latency_p95 | Query response time | >100ms | >200ms |
| index_memory | Index memory usage | >80% RAM | >90% RAM |

### Health Checks

```bash
# Check vector store health
curl http://localhost:9595/healthz/vector-store

# Check index status
curl http://localhost:9595/metrics | grep vector_index
```

## Troubleshooting

### Common Issues

1. **High Latency**
   - Check index configuration
   - Monitor memory usage
   - Consider scaling

2. **Out of Memory**
   - Reduce batch size
   - Increase swap space
   - Scale vertically

3. **Poor Search Results**
   - Verify vector normalization
   - Check similarity threshold
   - Validate index quality

## Related Features

- [Semantic Graph](./semantic-graph.md)
- [Temporal Decay](./temporal-decay.md)
- [Query Optimization](./query-optimization.md)

## API Reference

See the complete [API Documentation](../../development-manual/api-reference.md) for detailed endpoint specifications.
