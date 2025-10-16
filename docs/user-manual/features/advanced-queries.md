---
title: "Advanced Queries"
purpose: "Guide users on complex memory querying capabilities"
audience: "End-users and developers"
last_updated: "2025-10-16"
review_frequency: "quarterly"
---

# Advanced Queries

## Overview
SomaFractalMemory provides sophisticated query capabilities combining vector similarity, graph traversal, and metadata filtering for precise memory retrieval.

## Query Types

### Hybrid Queries
Combine multiple search criteria:
```python
from somafractalmemory import Client

# Initialize client
client = Client()

# Hybrid query
results = client.search(
    text="example query",
    filters={
        "type": "document",
        "date": {"$gt": "2025-01-01"}
    },
    vector_boost=0.7,
    text_boost=0.3
)
```

### Pattern Matching
Find memories matching specific patterns:
```python
# Regular expression search
results = client.search_pattern(
    pattern=".*important.*",
    field="content"
)

# Fuzzy matching
results = client.search_fuzzy(
    text="important",
    max_distance=2
)
```

## Query Components

### Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| $eq | Equals | `{"field": {"$eq": value}}` |
| $gt | Greater than | `{"field": {"$gt": value}}` |
| $lt | Less than | `{"field": {"$lt": value}}` |
| $in | In array | `{"field": {"$in": [1,2,3]}}` |
| $regex | Regex match | `{"field": {"$regex": "pattern"}}` |

### Sorting
```python
results = client.search(
    text="query",
    sort=[
        {"field": "date", "order": "desc"},
        {"field": "score", "order": "asc"}
    ]
)
```

### Pagination
```python
results = client.search(
    text="query",
    offset=20,
    limit=10
)
```

## Advanced Features

### Aggregations
```python
# Count by type
counts = client.aggregate(
    group_by="type",
    metrics=["count"]
)

# Average score by date
scores = client.aggregate(
    group_by="date",
    metrics=[{"avg": "score"}]
)
```

### Query Composition
Build complex queries:
```python
query = (
    client.query_builder()
    .text("example")
    .filter("type", "document")
    .vector_boost(0.7)
    .date_range("2025-01-01", "2025-12-31")
    .build()
)
```

## Performance Optimization

### Query Planning
```python
# Get query plan
plan = client.explain_query(query)

# Optimize query
optimized = client.optimize_query(query)
```

### Caching
```python
# Enable query cache
client.configure_cache(
    enabled=True,
    ttl=3600
)
```

## Common Use Cases

1. **Content Search**
   ```python
   results = client.search(
       text="topic",
       filters={"type": "article"},
       sort=[{"field": "date", "order": "desc"}]
   )
   ```

2. **Related Content**
   ```python
   related = client.find_related(
       memory_id="mem_123",
       relationship_types=["references", "similar-to"],
       limit=5
   )
   ```

3. **Time-based Queries**
   ```python
   timeline = client.search(
       filters={"date": {
           "$gte": "2025-01-01",
           "$lt": "2025-12-31"
       }},
       sort=[{"field": "date", "order": "asc"}]
   )
   ```

## Best Practices

1. **Query Design**
   - Use appropriate indexes
   - Limit result size
   - Combine filters effectively

2. **Performance**
   - Cache frequent queries
   - Use pagination
   - Optimize sort operations

3. **Maintenance**
   - Monitor query performance
   - Update indexes regularly
   - Clean up unused queries

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Slow Query | Missing index | Add appropriate index |
| No Results | Too strict filters | Relax constraints |
| Timeout | Complex query | Simplify or paginate |

## Query Examples

### Text Search with Metadata
```python
results = client.search(
    text="important meeting",
    filters={
        "type": "meeting",
        "priority": {"$gt": 5},
        "tags": {"$contains": "urgent"}
    }
)
```

### Vector Similarity with Graph
```python
results = client.search(
    vector=[0.1, 0.2, ...],
    graph_filter={
        "relationship": "references",
        "depth": 2
    }
)
```

### Complex Aggregation
```python
analysis = client.aggregate([
    {"group": "type"},
    {"count": "*"},
    {"avg": "importance"},
    {"max": "date"}
])
```

## Further Reading
- [Query Optimization](../../technical-manual/query-optimization.md)
- [API Reference](../../development-manual/api-reference.md#querying)
- [Performance Guide](../../technical-manual/performance.md)
