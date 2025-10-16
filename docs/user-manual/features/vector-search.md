---
title: "Vector Search"
purpose: "Guide users on vector similarity search capabilities"
audience: "End-users and developers"
last_updated: "2025-10-16"
review_frequency: "quarterly"
---

# Vector Search

## Overview
Vector search allows you to find memories based on semantic similarity rather than exact matching. This is particularly useful for natural language queries and finding related content.

## Key Concepts

### Vector Embeddings
- Numerical representations of content
- Captures semantic meaning
- Enables similarity comparisons

### Similarity Metrics
- Cosine similarity (default)
- Euclidean distance
- Dot product

## Basic Usage

### Simple Vector Search
```python
from somafractalmemory import Client

# Initialize client
client = Client()

# Search with a vector
results = client.search_vector(
    vector=[0.1, 0.2, ...],  # Your vector
    limit=5
)
```

### Text-to-Vector Search
```python
# Search using text (auto-embedded)
results = client.search_text(
    text="example query",
    limit=5
)
```

## Advanced Features

### Hybrid Search
Combine vector similarity with metadata filters:
```python
results = client.search_vector(
    vector=[0.1, 0.2, ...],
    filters={
        "type": "document",
        "date": {"$gt": "2025-01-01"}
    },
    limit=5
)
```

### Batch Search
Search multiple vectors efficiently:
```python
results = client.batch_search_vector(
    vectors=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
    limit=5
)
```

## Performance Tips

| Scenario | Recommendation |
|----------|---------------|
| Large Dataset | Use approximate search |
| Real-time | Enable cache |
| High Precision | Use exact search |

## Configuration

### Search Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| limit | 10 | Max results |
| threshold | 0.7 | Similarity threshold |
| exact | false | Use exact search |

### Example Configuration
```python
client.configure_search(
    exact=True,
    threshold=0.8,
    cache_enabled=True
)
```

## Common Use Cases

1. **Semantic Search**
   - Find documents with similar meaning
   - Language-agnostic search

2. **Recommendation**
   - Find similar items
   - Content recommendations

3. **Deduplication**
   - Find near-duplicate content
   - Content clustering

## Best Practices

1. **Vector Quality**
   - Use appropriate embedding model
   - Normalize vectors when needed
   - Update vectors when content changes

2. **Performance**
   - Use batch operations
   - Enable caching
   - Index frequently searched fields

3. **Maintenance**
   - Monitor index size
   - Regular performance checks
   - Update embeddings periodically

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Slow Search | Large index | Enable approximate search |
| Poor Results | Low-quality vectors | Update embedding model |
| High Memory | Too many vectors | Use disk-based index |

## Further Reading
- [Technical Details](../../technical-manual/vector-search.md)
- [API Reference](../../development-manual/api-reference.md#vector-search)
- [Performance Guide](../../technical-manual/performance.md)
