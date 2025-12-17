"""
Graph Store helper functions for SomaFractalMemory.

This module contains utility functions used by PostgresGraphStore
for coordinate conversion and data serialization.
"""

import json
from typing import Any


def coord_to_str(coord: tuple[float, ...]) -> str:
    """Convert coordinate tuple to string for storage.

    Args:
        coord: A tuple of float coordinates.

    Returns:
        Comma-separated string representation.
    """
    return ",".join(str(c) for c in coord)


def str_to_coord(coord_str: str) -> tuple[float, ...]:
    """Convert string back to coordinate tuple.

    Args:
        coord_str: Comma-separated string representation.

    Returns:
        Tuple of float coordinates.
    """
    return tuple(float(c) for c in coord_str.split(","))


def export_graph_to_file(nodes: list[dict], edges: list[dict], path: str) -> None:
    """Export graph data to a JSON file.

    Args:
        nodes: List of node dictionaries.
        edges: List of edge dictionaries.
        path: File path to write to.
    """
    data = {"nodes": nodes, "edges": edges}
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def import_graph_from_file(path: str) -> dict[str, Any]:
    """Import graph data from a JSON file.

    Args:
        path: File path to read from.

    Returns:
        Dictionary with 'nodes' and 'edges' keys.
    """
    with open(path) as f:
        return json.load(f)


def parse_edge_row(
    to_coord_str: str, link_type: str, strength: float, metadata: Any
) -> tuple[tuple[float, ...], dict[str, Any]]:
    """Parse a database edge row into coordinate and edge data."""
    neighbor_coord = str_to_coord(to_coord_str)
    edge_data = {
        "type": link_type,
        "strength": strength,
        **(metadata if isinstance(metadata, dict) else {}),
    }
    return (neighbor_coord, edge_data)


def parse_node_rows(rows: list) -> list[dict]:
    """Parse node rows from database into export format."""
    return [{"coord": row[0], "data": row[1], "tenant": row[2]} for row in rows]


def parse_edge_rows_for_export(rows: list) -> list[dict]:
    """Parse edge rows from database into export format."""
    return [
        {
            "from_coord": row[0],
            "to_coord": row[1],
            "link_type": row[2],
            "strength": row[3],
            "metadata": row[4],
            "tenant": row[5],
        }
        for row in rows
    ]


# SQL Templates for table creation (use single {} placeholder for table name)
# Note: {{}} escapes braces in Python format strings, producing literal {}
NODES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {} (
    coord TEXT PRIMARY KEY,
    data JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    tenant TEXT NOT NULL DEFAULT 'default',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

EDGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {} (
    id SERIAL PRIMARY KEY,
    from_coord TEXT NOT NULL,
    to_coord TEXT NOT NULL,
    link_type TEXT NOT NULL DEFAULT 'related',
    strength FLOAT NOT NULL DEFAULT 1.0,
    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    tenant TEXT NOT NULL DEFAULT 'default',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(from_coord, to_coord, link_type, tenant)
)
"""


def bfs_shortest_path(
    from_str: str,
    to_str: str,
    get_neighbors_fn: Any,
    max_length: int = 10,
) -> list[str]:
    """Find shortest path using BFS.

    Args:
        from_str: Start coordinate as string.
        to_str: End coordinate as string.
        get_neighbors_fn: Function that takes coord_str and returns list of neighbor strings.
        max_length: Maximum path length to search.

    Returns:
        List of coordinate strings forming the path, or empty list if no path.
    """
    if from_str == to_str:
        return [from_str]

    visited: set[str] = {from_str}
    queue: list[tuple[str, list[str]]] = [(from_str, [from_str])]

    while queue and len(queue[0][1]) <= max_length:
        current, path = queue.pop(0)
        neighbors = get_neighbors_fn(current)

        for neighbor in neighbors:
            if neighbor == to_str:
                return path + [neighbor]

            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return []
