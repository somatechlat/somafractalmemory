# Query Optimization

## Overview

Query Optimization in Soma Fractal Memory enables efficient vector searches, relationship traversals, and distributed memory operations through sophisticated indexing and caching strategies.

## Key Capabilities

### 1. Index Management

- HNSW index optimization
- Dynamic index updates
- Multi-dimensional indexing
- Custom index configuration

### 2. Query Features

- Vector similarity search
- Metadata filtering
- Graph traversal
- Hybrid queries

### 3. Performance Features

- Query caching
- Batch processing
- Parallel execution
- Resource management

## Usage Examples

### Optimized Search

```python
import requests

response = requests.post(
    'http://localhost:9595/api/v1/memory/search',
    json={
        'vector': [0.1, 0.2, ...],
        'limit': 10,
        'min_similarity': 0.7,
        'optimization': {
            'use_cache': True,
            'parallel': True
        }
    }
)
```

### Filtered Query

```python
response = requests.post(
    'http://localhost:9595/api/v1/memory/search',
    json={
        'vector': [0.1, 0.2, ...],
        'filter': {
            'metadata.importance': {'$gt': 0.5},
            'metadata.timestamp': {
                '$gt': '2025-01-01T00:00:00Z'
            }
        },
        'index': 'importance_time'
    }
)
```

### Batch Query

```python
response = requests.post(
    'http://localhost:9595/api/v1/memory/batch_search',
    json={
        'queries': [
            {
                'vector': [0.1, 0.2, ...],
                'limit': 5
            },
            {
                'vector': [0.3, 0.4, ...],
                'limit': 5
            }
        ],
        'parallel': True
    }
)
```

## Configuration

```yaml
# config.yaml
query_optimization:
  cache:
    enabled: true
    size: '1GB'
    ttl: 3600
  index:
    type: 'hnsw'
    M: 16
    efConstruction: 200
    efSearch: 100
  execution:
    max_parallel: 4
    timeout: 5000
```

## Performance Tuning

### Index Settings

```yaml
index_settings:
  build_threads: 4
  memory_limit: '4GB'
  update_interval: 60
```

### Query Settings

```yaml
query_settings:
  batch_size: 100
  cache_policy: 'lru'
  max_concurrent: 8
```

## Best Practices

1. **Index Configuration**
   - Optimize for workload
   - Monitor build time
   - Balance quality vs speed

2. **Query Design**
   - Use efficient filters
   - Batch similar queries
   - Leverage caching

3. **Resource Management**
   - Monitor memory usage
   - Control concurrency
   - Set appropriate timeouts

## Monitoring

### Key Metrics

| Metric | Description | Warning | Critical |
|--------|-------------|----------|----------|
| query_latency | Response time | >100ms | >200ms |
| cache_hit_rate | Cache efficiency | <80% | <60% |
| index_memory | Index memory usage | >80% RAM | >90% RAM |

### Health Checks

```bash
# Check query performance
curl http://localhost:9595/healthz/query

# Monitor metrics
curl http://localhost:9595/metrics | grep query_
```

## Troubleshooting

### Common Issues

1. **Slow Queries**
   - Check index health
   - Verify filter efficiency
   - Monitor resource usage

2. **High Memory Usage**
   - Adjust cache size
   - Optimize index settings
   - Control concurrency

3. **Cache Inefficiency**
   - Review cache policy
   - Check query patterns
   - Adjust TTL settings

## Query Analysis

### Performance Profiling

```python
response = requests.get(
    'http://localhost:9595/api/v1/analytics/query',
    params={
        'timeframe': '1h',
        'min_duration': 100
    }
)
```

### Index Statistics

```python
response = requests.get(
    'http://localhost:9595/api/v1/analytics/index',
    params={
        'include_memory': True
    }
)
```

## Related Features

- [Vector Storage](./vector-storage.md)
- [Semantic Graph](./semantic-graph.md)
- [Temporal Decay](./temporal-decay.md)

## API Reference

See the complete [API Documentation](../../development-manual/api-reference.md) for detailed endpoint specifications.
