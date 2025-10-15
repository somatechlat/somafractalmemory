---
title: "Graph Store Architecture"
purpose: "Technical details of the memory relationship storage system"
audience:
  - "System Architects"
  - "DevOps Engineers"
prerequisites:
  - "Understanding of graph databases"
  - "Knowledge of distributed systems"
version: "1.0.0"
last_updated: "2025-10-15"
review_frequency: "quarterly"
---

# Graph Store Architecture

## Overview
SomaFractalMemory uses a graph database to store and manage relationships between memories.

## Components

### Graph Database
- PostgreSQL with graph extensions
- Custom graph traversal engine
- Edge weight management system

### Edge Schema
```sql
CREATE TABLE memory_edges (
    from_coord TEXT,
    to_coord TEXT,
    type TEXT,
    weight FLOAT,
    timestamp TIMESTAMP,
    metadata JSONB,
    PRIMARY KEY (from_coord, to_coord, type)
);
```

## Graph Operations

### Basic Operations
- Add/remove edges
- Update edge weights
- Edge type filtering
- Neighbor discovery

### Advanced Queries
```sql
-- Find all neighbors within 2 hops
WITH RECURSIVE neighbors AS (
    SELECT from_coord, to_coord, 1 as depth
    FROM memory_edges
    WHERE from_coord = 'start_coord'
    UNION
    SELECT e.from_coord, e.to_coord, n.depth + 1
    FROM memory_edges e
    JOIN neighbors n ON e.from_coord = n.to_coord
    WHERE n.depth < 2
)
SELECT DISTINCT to_coord FROM neighbors;
```

## Scaling

### Data Distribution
- Partitioned by coordinate ranges
- Edge replication for availability

### Performance Optimization
- Indexed edge lookups
- Cached frequent paths
- Batched edge updates

## Integration

### Internal Components
- Vector Store
- Query Router
- Cache Layer

### External Systems
- PostgreSQL
- Redis (for path caching)

## Monitoring

### Key Metrics
- Edge count
- Query latency
- Cache hit rate
- Path computation time

### Health Checks
- Database connectivity
- Index health
- Cache synchronization

## Common Operations

### Path Finding
```python
def find_shortest_path(start_coord, end_coord):
    """Find shortest path between two memory coordinates"""
    visited = set()
    queue = [(start_coord, [start_coord])]

    while queue:
        (vertex, path) = queue.pop(0)
        for neighbor in get_neighbors(vertex):
            if neighbor == end_coord:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return None
```

### Weight Updates
```sql
UPDATE memory_edges
SET weight = weight * decay_factor
WHERE timestamp < NOW() - INTERVAL '7 days'
  AND type = 'temporal';
```

## References
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Graph Theory Basics](../../development-manual/concepts/graph-theory.md)
- [Query Optimization Guide](../performance.md)
