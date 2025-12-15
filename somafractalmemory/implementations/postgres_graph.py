"""PostgreSQL-backed Graph Store for SomaFractalMemory.

Implements IGraphStore with persistent storage in PostgreSQL.
Per Task V2.1-V2.7: Replaces in-memory NetworkXGraphStore for production use.

Tables:
- graph_nodes: Stores memory nodes with coordinate as primary key
- graph_edges: Stores directed edges between nodes with metadata
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from typing import Any

import psycopg2
from psycopg2 import OperationalError
from psycopg2 import errors as psycopg_errors
from psycopg2.extras import Json
from psycopg2.sql import SQL, Identifier

from somafractalmemory.interfaces.graph import IGraphStore


class PostgresGraphStore(IGraphStore):
    """PostgreSQL implementation of the graph store interface.

    Persists graph nodes and edges to PostgreSQL tables, ensuring data
    survives SFM restarts. Per Task V2.1-V2.7.

    Tables created:
    - graph_nodes(coord TEXT PRIMARY KEY, data JSONB, tenant TEXT, created_at TIMESTAMPTZ)
    - graph_edges(id SERIAL PRIMARY KEY, from_coord TEXT, to_coord TEXT, link_type TEXT,
                  strength FLOAT, metadata JSONB, tenant TEXT, created_at TIMESTAMPTZ)
    """

    _NODES_TABLE = "graph_nodes"
    _EDGES_TABLE = "graph_edges"

    def __init__(self, url: str | None = None):
        """Initialize PostgresGraphStore.

        Args:
            url: PostgreSQL connection URL. If None, uses settings.
        """
        from common.config.settings import load_settings

        _settings = load_settings()
        raw_url = (
            url
            or getattr(_settings, "postgres_url", None)
            or "postgresql://soma:soma@localhost:5432/soma"
        )
        # Strip the +psycopg2 dialect suffix if present
        self._url = raw_url.replace("postgresql+psycopg2://", "postgresql://", 1)
        self._sslmode = getattr(_settings, "postgres_ssl_mode", None)
        self._sslrootcert = getattr(_settings, "postgres_ssl_root_cert", None)
        self._sslcert = getattr(_settings, "postgres_ssl_cert", None)
        self._sslkey = getattr(_settings, "postgres_ssl_key", None)
        self._conn = None
        self._lock = threading.RLock()
        self._ensure_connection()
        self._ensure_tables()

    def _ensure_connection(self):
        """Establish connection if none exists or if closed."""
        if self._conn is None or getattr(self._conn, "closed", 0) != 0:
            conn_kwargs = {}
            if self._sslmode:
                conn_kwargs["sslmode"] = self._sslmode
            if self._sslrootcert:
                conn_kwargs["sslrootcert"] = self._sslrootcert
            if self._sslcert:
                conn_kwargs["sslcert"] = self._sslcert
            if self._sslkey:
                conn_kwargs["sslkey"] = self._sslkey
            self._conn = psycopg2.connect(self._url, **conn_kwargs)
            self._conn.autocommit = True

    def _reset_connection(self):
        """Close and reset connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = None

    def _execute(self, fn: Callable[[Any], Any]) -> Any:
        """Execute a function with cursor, handling connection recovery."""
        recoverable_errors: tuple[type[Exception], ...] = (
            psycopg2.InterfaceError,
            OperationalError,
            psycopg_errors.InFailedSqlTransaction,
        )

        def _run() -> Any:
            self._ensure_connection()
            with self._conn.cursor() as cur:  # type: ignore[union-attr]
                return fn(cur)

        try:
            return _run()
        except recoverable_errors:
            self._reset_connection()
            return _run()

    def _ensure_tables(self):
        """Create graph_nodes and graph_edges tables if they don't exist."""

        def _create_tables(cur):
            # Create graph_nodes table (V2.2)
            cur.execute(
                SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {} (
                        coord TEXT PRIMARY KEY,
                        data JSONB NOT NULL DEFAULT '{}',
                        tenant TEXT NOT NULL DEFAULT 'default',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                ).format(Identifier(self._NODES_TABLE))
            )
            # Create graph_edges table (V2.2)
            cur.execute(
                SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {} (
                        id SERIAL PRIMARY KEY,
                        from_coord TEXT NOT NULL,
                        to_coord TEXT NOT NULL,
                        link_type TEXT NOT NULL DEFAULT 'related',
                        strength FLOAT NOT NULL DEFAULT 1.0,
                        metadata JSONB NOT NULL DEFAULT '{}',
                        tenant TEXT NOT NULL DEFAULT 'default',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(from_coord, to_coord, link_type, tenant)
                    );
                    """
                ).format(Identifier(self._EDGES_TABLE))
            )

        self._execute(_create_tables)

        # Create indexes for efficient queries
        try:

            def _create_indexes(cur):
                # Index on from_coord for neighbor lookups
                cur.execute(
                    SQL("CREATE INDEX IF NOT EXISTS idx_{}_from ON {} (from_coord);").format(
                        Identifier(self._EDGES_TABLE), Identifier(self._EDGES_TABLE)
                    )
                )
                # Index on to_coord for reverse lookups
                cur.execute(
                    SQL("CREATE INDEX IF NOT EXISTS idx_{}_to ON {} (to_coord);").format(
                        Identifier(self._EDGES_TABLE), Identifier(self._EDGES_TABLE)
                    )
                )
                # Index on tenant for isolation
                cur.execute(
                    SQL("CREATE INDEX IF NOT EXISTS idx_{}_tenant ON {} (tenant);").format(
                        Identifier(self._EDGES_TABLE), Identifier(self._EDGES_TABLE)
                    )
                )
                cur.execute(
                    SQL("CREATE INDEX IF NOT EXISTS idx_{}_tenant ON {} (tenant);").format(
                        Identifier(self._NODES_TABLE), Identifier(self._NODES_TABLE)
                    )
                )
                # Index on link_type for filtered queries
                cur.execute(
                    SQL("CREATE INDEX IF NOT EXISTS idx_{}_type ON {} (link_type);").format(
                        Identifier(self._EDGES_TABLE), Identifier(self._EDGES_TABLE)
                    )
                )

            self._execute(_create_indexes)
        except Exception:
            # Non-fatal if permissions are restricted
            pass

    def _coord_to_str(self, coord: tuple[float, ...]) -> str:
        """Convert coordinate tuple to string for storage."""
        return ",".join(str(c) for c in coord)

    def _str_to_coord(self, coord_str: str) -> tuple[float, ...]:
        """Convert string back to coordinate tuple."""
        return tuple(float(c) for c in coord_str.split(","))

    def add_memory(self, coordinate: tuple[float, ...], memory_data: dict[str, Any]):
        """Add a memory node to the graph (V2.3).

        Args:
            coordinate: The memory coordinate.
            memory_data: Associated data for the node.
        """
        coord_str = self._coord_to_str(coordinate)
        tenant = memory_data.get("tenant", "default")

        def _insert(cur):
            cur.execute(
                SQL(
                    """
                    INSERT INTO {} (coord, data, tenant)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (coord) DO UPDATE SET data = EXCLUDED.data;
                    """
                ).format(Identifier(self._NODES_TABLE)),
                (coord_str, Json(memory_data), tenant),
            )

        self._execute(_insert)

    def add_link(
        self,
        from_coord: tuple[float, ...],
        to_coord: tuple[float, ...],
        link_data: dict[str, Any],
    ):
        """Add a directed link between two coordinates (V2.4).

        Args:
            from_coord: Source coordinate.
            to_coord: Target coordinate.
            link_data: Link metadata including 'type', 'strength', 'tenant'.
        """
        from_str = self._coord_to_str(from_coord)
        to_str = self._coord_to_str(to_coord)
        link_type = link_data.get("type", "related")
        strength = float(link_data.get("strength", 1.0))
        tenant = link_data.get("tenant", "default")
        # Remove known fields from metadata
        metadata = {k: v for k, v in link_data.items() if k not in ("type", "strength", "tenant")}

        def _insert(cur):
            cur.execute(
                SQL(
                    """
                    INSERT INTO {} (from_coord, to_coord, link_type, strength, metadata, tenant)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (from_coord, to_coord, link_type, tenant)
                    DO UPDATE SET strength = EXCLUDED.strength, metadata = EXCLUDED.metadata;
                    """
                ).format(Identifier(self._EDGES_TABLE)),
                (from_str, to_str, link_type, strength, Json(metadata), tenant),
            )

        self._execute(_insert)

    def get_neighbors(
        self,
        coordinate: tuple[float, ...],
        link_type: str | None = None,
        limit: int | None = None,
    ) -> list[tuple[Any, dict[str, Any]]]:
        """Get neighbors of a coordinate (V2.5).

        Args:
            coordinate: The source coordinate.
            link_type: Optional filter by link type.
            limit: Maximum number of neighbors to return.

        Returns:
            List of (neighbor_coord, edge_data) tuples.
        """
        coord_str = self._coord_to_str(coordinate)

        def _query(cur):
            if link_type is not None:
                sql = SQL(
                    """
                    SELECT to_coord, link_type, strength, metadata
                    FROM {}
                    WHERE from_coord = %s AND link_type = %s
                    ORDER BY strength DESC
                    """
                ).format(Identifier(self._EDGES_TABLE))
                params: list[Any] = [coord_str, link_type]
            else:
                sql = SQL(
                    """
                    SELECT to_coord, link_type, strength, metadata
                    FROM {}
                    WHERE from_coord = %s
                    ORDER BY strength DESC
                    """
                ).format(Identifier(self._EDGES_TABLE))
                params = [coord_str]

            if limit is not None:
                sql = SQL("{} LIMIT %s").format(sql)
                params.append(limit)

            cur.execute(sql, tuple(params))
            return cur.fetchall()

        rows = self._execute(_query)
        neighbors: list[tuple[Any, dict[str, Any]]] = []
        for to_coord_str, ltype, strength, metadata in rows:
            neighbor_coord = self._str_to_coord(to_coord_str)
            edge_data = {
                "type": ltype,
                "strength": strength,
                **(metadata if isinstance(metadata, dict) else {}),
            }
            neighbors.append((neighbor_coord, edge_data))
        return neighbors

    def find_shortest_path(
        self,
        from_coord: tuple[float, ...],
        to_coord: tuple[float, ...],
        link_type: str | None = None,
        max_length: int = 10,
    ) -> list[Any]:
        """Find shortest path between two coordinates.

        Uses BFS with optional link_type filter.

        Args:
            from_coord: Start coordinate.
            to_coord: End coordinate.
            link_type: Optional filter by link type.
            max_length: Maximum path length to search.

        Returns:
            List of coordinates forming the path, or empty list if no path.
        """
        from_str = self._coord_to_str(from_coord)
        to_str = self._coord_to_str(to_coord)

        if from_str == to_str:
            return [from_coord]

        # BFS implementation
        visited: set[str] = {from_str}
        queue: list[tuple[str, list[str]]] = [(from_str, [from_str])]

        while queue and len(queue[0][1]) <= max_length:
            current, path = queue.pop(0)

            # Get neighbors from database - use factory to capture current value
            def _make_query(coord_val: str, ltype: str | None):
                def _query(cur):
                    if ltype is not None:
                        cur.execute(
                            SQL(
                                "SELECT to_coord FROM {} WHERE from_coord = %s AND link_type = %s"
                            ).format(Identifier(self._EDGES_TABLE)),
                            (coord_val, ltype),
                        )
                    else:
                        cur.execute(
                            SQL("SELECT to_coord FROM {} WHERE from_coord = %s").format(
                                Identifier(self._EDGES_TABLE)
                            ),
                            (coord_val,),
                        )
                    return [row[0] for row in cur.fetchall()]

                return _query

            neighbors = self._execute(_make_query(current, link_type))

            for neighbor in neighbors:
                if neighbor == to_str:
                    # Found path
                    result_path = path + [neighbor]
                    return [self._str_to_coord(c) for c in result_path]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []  # No path found

    def remove_memory(self, coordinate: tuple[float, ...]):
        """Remove a memory node and all its edges.

        Args:
            coordinate: The coordinate to remove.
        """
        coord_str = self._coord_to_str(coordinate)

        def _delete(cur):
            # Delete all edges involving this node
            cur.execute(
                SQL("DELETE FROM {} WHERE from_coord = %s OR to_coord = %s;").format(
                    Identifier(self._EDGES_TABLE)
                ),
                (coord_str, coord_str),
            )
            # Delete the node
            cur.execute(
                SQL("DELETE FROM {} WHERE coord = %s;").format(Identifier(self._NODES_TABLE)),
                (coord_str,),
            )

        self._execute(_delete)

    def clear(self):
        """Clear all nodes and edges from the graph."""

        def _truncate(cur):
            cur.execute(SQL("TRUNCATE {} CASCADE;").format(Identifier(self._EDGES_TABLE)))
            cur.execute(SQL("TRUNCATE {} CASCADE;").format(Identifier(self._NODES_TABLE)))

        self._execute(_truncate)

    def export_graph(self, path: str):
        """Export graph to a JSON file.

        Args:
            path: File path to write to.
        """

        def _export(cur):
            # Get all nodes
            cur.execute(
                SQL("SELECT coord, data, tenant FROM {};").format(Identifier(self._NODES_TABLE))
            )
            nodes = [{"coord": row[0], "data": row[1], "tenant": row[2]} for row in cur.fetchall()]

            # Get all edges
            cur.execute(
                SQL(
                    "SELECT from_coord, to_coord, link_type, strength, metadata, tenant FROM {};"
                ).format(Identifier(self._EDGES_TABLE))
            )
            edges = [
                {
                    "from_coord": row[0],
                    "to_coord": row[1],
                    "link_type": row[2],
                    "strength": row[3],
                    "metadata": row[4],
                    "tenant": row[5],
                }
                for row in cur.fetchall()
            ]

            return {"nodes": nodes, "edges": edges}

        data = self._execute(_export)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def import_graph(self, path: str):
        """Import graph from a JSON file.

        Args:
            path: File path to read from.
        """
        with open(path) as f:
            data = json.load(f)

        def _import(cur):
            # Import nodes
            for node in data.get("nodes", []):
                cur.execute(
                    SQL(
                        """
                        INSERT INTO {} (coord, data, tenant)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (coord) DO UPDATE SET data = EXCLUDED.data;
                        """
                    ).format(Identifier(self._NODES_TABLE)),
                    (node["coord"], Json(node.get("data", {})), node.get("tenant", "default")),
                )

            # Import edges
            for edge in data.get("edges", []):
                cur.execute(
                    SQL(
                        """
                        INSERT INTO {} (from_coord, to_coord, link_type, strength, metadata, tenant)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (from_coord, to_coord, link_type, tenant)
                        DO UPDATE SET strength = EXCLUDED.strength, metadata = EXCLUDED.metadata;
                        """
                    ).format(Identifier(self._EDGES_TABLE)),
                    (
                        edge["from_coord"],
                        edge["to_coord"],
                        edge.get("link_type", "related"),
                        edge.get("strength", 1.0),
                        Json(edge.get("metadata", {})),
                        edge.get("tenant", "default"),
                    ),
                )

        self._execute(_import)

    def health_check(self) -> bool:
        """Check if the graph store is healthy.

        Returns:
            True if both tables are accessible.
        """
        try:

            def _check(cur):
                cur.execute(SQL("SELECT 1 FROM {} LIMIT 1;").format(Identifier(self._NODES_TABLE)))
                cur.execute(SQL("SELECT 1 FROM {} LIMIT 1;").format(Identifier(self._EDGES_TABLE)))
                return True

            return self._execute(_check)
        except Exception:
            return False

    def get_node_count(self) -> int:
        """Get total number of nodes in the graph."""

        def _count(cur):
            cur.execute(SQL("SELECT COUNT(*) FROM {};").format(Identifier(self._NODES_TABLE)))
            return cur.fetchone()[0]

        return self._execute(_count)

    def get_edge_count(self) -> int:
        """Get total number of edges in the graph."""

        def _count(cur):
            cur.execute(SQL("SELECT COUNT(*) FROM {};").format(Identifier(self._EDGES_TABLE)))
            return cur.fetchone()[0]

        return self._execute(_count)

    def get_neighbors_by_tenant(
        self,
        coordinate: tuple[float, ...],
        tenant: str,
        link_type: str | None = None,
        limit: int | None = None,
    ) -> list[tuple[Any, dict[str, Any]]]:
        """Get neighbors filtered by tenant for isolation.

        Args:
            coordinate: The source coordinate.
            tenant: Tenant ID for isolation.
            link_type: Optional filter by link type.
            limit: Maximum number of neighbors to return.

        Returns:
            List of (neighbor_coord, edge_data) tuples.
        """
        coord_str = self._coord_to_str(coordinate)

        def _query(cur):
            params: list[Any] = [coord_str, tenant]
            if link_type is not None:
                sql = SQL(
                    """
                    SELECT to_coord, link_type, strength, metadata
                    FROM {}
                    WHERE from_coord = %s AND tenant = %s AND link_type = %s
                    ORDER BY strength DESC
                    """
                ).format(Identifier(self._EDGES_TABLE))
                params.append(link_type)
            else:
                sql = SQL(
                    """
                    SELECT to_coord, link_type, strength, metadata
                    FROM {}
                    WHERE from_coord = %s AND tenant = %s
                    ORDER BY strength DESC
                    """
                ).format(Identifier(self._EDGES_TABLE))

            if limit is not None:
                sql = SQL("{} LIMIT %s").format(sql)
                params.append(limit)

            cur.execute(sql, tuple(params))
            return cur.fetchall()

        rows = self._execute(_query)
        neighbors: list[tuple[Any, dict[str, Any]]] = []
        for to_coord_str, ltype, strength, metadata in rows:
            neighbor_coord = self._str_to_coord(to_coord_str)
            edge_data = {
                "type": ltype,
                "strength": strength,
                **(metadata if isinstance(metadata, dict) else {}),
            }
            neighbors.append((neighbor_coord, edge_data))
        return neighbors
