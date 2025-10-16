# Semantic Graph

## Overview

The Semantic Graph feature enables creating and traversing relationships between memory vectors, allowing for complex semantic networks and knowledge graphs.

## Key Capabilities

### 1. Graph Operations

- Create semantic links
- Query relationships
- Path traversal
- Graph analytics

### 2. Relationship Types

- Similarity links
- Temporal connections
- Custom relationships
- Weighted edges

### 3. Graph Features

- Bidirectional links
- Relationship metadata
- Path weights
- Subgraph queries

## Usage Examples

### Create Link

```python
import requests

response = requests.post(
    'http://localhost:9595/api/v1/memory/link',
    json={
        'source_id': 'memory1',
        'target_id': 'memory2',
        'relation_type': 'similar_to',
        'metadata': {
            'weight': 0.8,
            'timestamp': '2025-10-15T10:00:00Z'
        }
    }
)
```

### Query Connections

```python
response = requests.get(
    'http://localhost:9595/api/v1/memory/memory1/connections',
    params={
        'relation_types': ['similar_to'],
        'depth': 2,
        'min_weight': 0.5
    }
)
```

### Path Analysis

```python
response = requests.post(
    'http://localhost:9595/api/v1/memory/path',
    json={
        'start_id': 'memory1',
        'end_id': 'memory2',
        'max_depth': 3,
        'relation_types': ['similar_to', 'follows']
    }
)
```

## Configuration

```yaml
# config.yaml
graph:
  max_connections: 1000
  default_weight: 1.0
  relation_types:
    - similar_to
    - follows
    - references
  indexing:
    enabled: true
    update_interval: 60
```

## Performance Tuning

### Graph Settings

```yaml
graph_settings:
  cache_size: '1GB'
  max_path_depth: 5
  batch_size: 100
```

### Query Optimization

```yaml
query_settings:
  max_results: 1000
  timeout: 5000
  cache_ttl: 3600
```

## Best Practices

1. **Relationship Design**
   - Define clear relationship types
   - Use meaningful weights
   - Consider directionality

2. **Query Patterns**
   - Limit path depth
   - Use specific relation types
   - Include weight thresholds

3. **Performance**
   - Batch relationship creation
   - Cache frequent queries
   - Monitor graph density

## Monitoring

### Key Metrics

| Metric | Description | Warning | Critical |
|--------|-------------|----------|----------|
| edge_count | Total relationships | >1M | >5M |
| path_query_time | Path search latency | >200ms | >500ms |
| cache_hit_rate | Graph cache efficiency | <80% | <60% |

### Health Checks

```bash
# Check graph store health
curl http://localhost:9595/healthz/graph-store

# Check relationship stats
curl http://localhost:9595/metrics | grep graph_
```

## Troubleshooting

### Common Issues

1. **Slow Path Queries**
   - Reduce max depth
   - Check index status
   - Monitor memory usage

2. **High Memory Usage**
   - Limit connection count
   - Increase cache size
   - Consider pruning

3. **Missing Paths**
   - Verify relationship types
   - Check weight thresholds
   - Validate node existence

## Graph Analysis

### Centrality Measures

```python
response = requests.get(
    'http://localhost:9595/api/v1/memory/memory1/centrality',
    params={
        'metric': 'betweenness',
        'depth': 3
    }
)
```

### Community Detection

```python
response = requests.post(
    'http://localhost:9595/api/v1/memory/community',
    json={
        'algorithm': 'louvain',
        'min_size': 5
    }
)
```

## Related Features

- [Vector Storage](./vector-storage.md)
- [Temporal Analysis](./temporal-analysis.md)
- [Query Optimization](./query-optimization.md)

## API Reference

See the complete [API Documentation](../../development-manual/api-reference.md) for detailed endpoint specifications.
