---
title: "Memory Recall in SomaFractalMemory"
purpose: "Learn how to retrieve memories from SomaFractalMemory"
audience:
  - "Application Developers"
  - "End Users"
prerequisites:
  - "SomaFractalMemory API access"
  - "Stored memories in the system"
version: "1.0.0"
last_updated: "2025-10-15"
review_frequency: "quarterly"
---

# Memory Recall

## Overview
SomaFractalMemory provides multiple methods for retrieving stored memories:
- Semantic recall
- Coordinate-based recall
- Graph traversal
- Hybrid search

## Recall Methods

### Basic Memory Recall
```bash
curl -X POST http://localhost:9595/recall \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Sample memory",
    "top_k": 5
  }'
```

### Recall with Filters
```bash
curl -X POST http://localhost:9595/recall \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Sample memory",
    "top_k": 5,
    "filters": {
      "type": "episodic"
    }
  }'
```

### Recall with Scores
```bash
curl -X POST http://localhost:9595/recall_with_scores \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Sample memory",
    "top_k": 5,
    "exact": true
  }'
```

## Scoring System
Recall results are scored based on:
- Vector similarity
- Importance score
- Memory freshness
- Access patterns

## Response Format
```json
{
  "matches": [
    {
      "text": "Sample memory",
      "type": "episodic",
      "coordinate": [1.0, 2.0, 3.0],
      "importance_norm": 0.8,
      "score": 0.95
    }
  ]
}
```

## Performance Tips
- Use appropriate `top_k` values
- Apply relevant filters
- Consider using batch recall for multiple queries

## Common Issues
| Problem | Solution |
|---------|----------|
| No results | Check query relevance and filters |
| Slow recall | Reduce `top_k` or add filters |
| Poor relevance | Adjust query or check importance scores |

## References
- [API Reference](../../development-manual/api-reference.md)
- [Vector Search Guide](vector-search.md)
- [Performance Tuning](../../technical-manual/performance.md)
