---
title: "Graph Relations"
purpose: "Guide users on creating and managing memory relationships"
audience: "End-users and developers"
last_updated: "2025-10-16"
review_frequency: "quarterly"
---

# Graph Relations

## Overview
Graph relations in SomaFractalMemory allow you to create, traverse, and analyze connections between memories. This enables complex knowledge structures and relationship-based queries.

## Key Concepts

### Memory Graph
- Memories as nodes
- Relationships as edges
- Directed connections
- Typed relationships

### Relationship Types
- Semantic (e.g., "is-related-to")
- Temporal (e.g., "happened-before")
- Causal (e.g., "causes")
- Custom types

## Basic Operations

### Creating Links
```python
from somafractalmemory import Client

# Initialize client
client = Client()

# Create a link between memories
client.link_memories(
    source_id="mem_123",
    target_id="mem_456",
    relationship="references"
)
```

### Querying Links
```python
# Get all links for a memory
links = client.get_memory_links("mem_123")

# Get specific relationship types
references = client.get_memory_links(
    "mem_123",
    relationship="references"
)
```

## Advanced Features

### Path Finding
Find paths between memories:
```python
path = client.find_path(
    start_id="mem_123",
    end_id="mem_789",
    max_depth=3
)
```

### Graph Traversal
Traverse the memory graph:
```python
memories = client.traverse_graph(
    start_id="mem_123",
    relationship="references",
    direction="outgoing",
    max_depth=2
)
```

## Graph Operations

### Bulk Operations
```python
# Create multiple links
client.bulk_link_memories([
    {
        "source": "mem_1",
        "target": "mem_2",
        "relationship": "refers-to"
    },
    {
        "source": "mem_2",
        "target": "mem_3",
        "relationship": "contains"
    }
])
```

### Graph Analysis
```python
# Find central memories
central = client.analyze_centrality("mem_123")

# Find communities
communities = client.find_communities()
```

## Common Patterns

### Knowledge Graph
```python
# Create concept hierarchy
client.link_memories(
    source="concept_a",
    target="concept_b",
    relationship="is-a"
)
```

### Temporal Sequences
```python
# Create event sequence
client.link_memories(
    source="event_1",
    target="event_2",
    relationship="precedes"
)
```

## Performance Tips

| Operation | Optimization |
|-----------|-------------|
| Traversal | Use depth limits |
| Bulk Links | Batch operations |
| Queries | Index relationships |

## Best Practices

1. **Relationship Design**
   - Use consistent relationship types
   - Document relationship meanings
   - Consider bidirectional needs

2. **Graph Structure**
   - Avoid cycles when unnecessary
   - Limit relationship depth
   - Use meaningful relationship types

3. **Maintenance**
   - Regular graph cleanup
   - Monitor relationship count
   - Archive unused links

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Cycle Detected | Circular references | Review graph structure |
| Path Not Found | Disconnected nodes | Check connectivity |
| Too Many Links | Excessive relationships | Implement limits |

## Use Cases

1. **Knowledge Management**
   - Concept hierarchies
   - Document relationships
   - Cross-references

2. **Process Tracking**
   - Workflow steps
   - Dependencies
   - State machines

3. **Recommendations**
   - Related content
   - Next steps
   - Similar items

## Configuration

### Graph Settings
```python
client.configure_graph(
    max_depth=5,
    index_relationships=True,
    allow_cycles=False
)
```

## Further Reading
- [Graph Theory Concepts](../../development-manual/concepts/graph-theory.md)
- [API Reference](../../development-manual/api-reference.md#graph-operations)
- [Performance Guide](../../technical-manual/performance.md#graph-optimization)
