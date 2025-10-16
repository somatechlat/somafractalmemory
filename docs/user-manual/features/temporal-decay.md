# Temporal Decay

## Overview

Temporal Decay is a key feature that simulates natural memory fading by automatically reducing the importance of stored memories over time based on access patterns and semantic relationships.

## Key Capabilities

### 1. Decay Functions

- Exponential decay
- Linear decay
- Custom decay functions
- Access-based adjustment

### 2. Temporal Features

- Time-based importance
- Access frequency impact
- Relationship strengthening
- Memory consolidation

### 3. Decay Management

- Configurable rates
- Importance thresholds
- Recovery mechanisms
- Batch processing

## Usage Examples

### Configure Decay

```python
import requests

response = requests.post(
    'http://localhost:9595/api/v1/config/decay',
    json={
        'function': 'exponential',
        'rate': 0.1,
        'min_importance': 0.1,
        'update_interval': 3600
    }
)
```

### Query with Importance

```python
response = requests.post(
    'http://localhost:9595/api/v1/memory/search',
    json={
        'vector': [0.1, 0.2, ...],
        'min_importance': 0.5,
        'include_metadata': True
    }
)
```

### Strengthen Memory

```python
response = requests.post(
    'http://localhost:9595/api/v1/memory/memory1/strengthen',
    json={
        'factor': 1.5,
        'reason': 'explicit_recall'
    }
)
```

## Configuration

```yaml
# config.yaml
decay:
  enabled: true
  function: exponential
  base_rate: 0.1
  min_importance: 0.1
  update_interval: 3600
  consolidation:
    enabled: true
    threshold: 0.3
    interval: 86400
```

## Performance Tuning

### Decay Settings

```yaml
decay_settings:
  batch_size: 1000
  workers: 4
  cache_ttl: 300
```

### Process Configuration

```yaml
process_settings:
  max_concurrent: 2
  timeout: 30
  retry_count: 3
```

## Best Practices

1. **Decay Configuration**
   - Start with conservative rates
   - Monitor importance distribution
   - Adjust based on usage patterns

2. **Memory Management**
   - Regular consolidation
   - Importance thresholds
   - Access pattern analysis

3. **Performance**
   - Batch updates
   - Scheduled maintenance
   - Cache management

## Monitoring

### Key Metrics

| Metric | Description | Warning | Critical |
|--------|-------------|----------|----------|
| avg_importance | Mean memory importance | <0.3 | <0.1 |
| decay_time | Update processing time | >10s | >30s |
| memory_count | Active memories | >80% cap | >90% cap |

### Health Checks

```bash
# Check decay process
curl http://localhost:9595/healthz/decay

# Monitor metrics
curl http://localhost:9595/metrics | grep decay_
```

## Troubleshooting

### Common Issues

1. **Rapid Decay**
   - Verify decay rate
   - Check access patterns
   - Adjust min importance

2. **High CPU Usage**
   - Increase batch size
   - Adjust update interval
   - Monitor worker count

3. **Memory Loss**
   - Check importance thresholds
   - Verify strengthening logic
   - Review consolidation settings

## Decay Analysis

### Importance Distribution

```python
response = requests.get(
    'http://localhost:9595/api/v1/analytics/importance',
    params={
        'bucket_count': 10,
        'min_importance': 0.1
    }
)
```

### Access Patterns

```python
response = requests.get(
    'http://localhost:9595/api/v1/analytics/access',
    params={
        'timeframe': '24h',
        'interval': '1h'
    }
)
```

## Related Features

- [Vector Storage](./vector-storage.md)
- [Semantic Graph](./semantic-graph.md)
- [Memory Consolidation](./memory-consolidation.md)

## API Reference

See the complete [API Documentation](../../development-manual/api-reference.md) for detailed endpoint specifications.
