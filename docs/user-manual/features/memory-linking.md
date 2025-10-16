---
title: "Memory Linking in SomaFractalMemory"
purpose: "Learn how to create and traverse relationships between memories"
audience:
  - "Application Developers"
  - "End Users"
prerequisites:
  - "SomaFractalMemory API access"
  - "Multiple stored memories"
version: "1.0.0"
last_updated: "2025-10-15"
review_frequency: "quarterly"
---

# Memory Linking

## Overview
SomaFractalMemory allows creation of relationships between memories through graph connections.

## Link Types
- **related**: General relationship
- **causal**: Cause-effect relationship
- **temporal**: Time-based relationship
- **spatial**: Space-based relationship

## Creating Links

### Basic Link Creation
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

### Finding Neighbors
```bash
curl "http://localhost:9595/neighbors?coord=1.0,2.0,3.0" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Finding Paths
```bash
curl "http://localhost:9595/shortest_path?frm=1.0,2.0,3.0&to=7.0,8.0,9.0" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Link Properties
- **type**: Relationship category
- **weight**: Connection strength (0.0-1.0)
- **timestamp**: Creation time

## Graph Operations
- Neighbor discovery
- Path finding
- Link type filtering
- Weight-based traversal

## Common Issues
| Problem | Solution |
|---------|----------|
| Invalid coordinates | Check coordinate format |
| Link already exists | Use different link type or update existing |
| No path found | Check coordinate connectivity |

## References
- [API Reference](../../development-manual/api-reference.md)
- [Graph Storage Details](../../technical-manual/architecture/graph-store.md)
- [Memory Types](memory-types.md)
