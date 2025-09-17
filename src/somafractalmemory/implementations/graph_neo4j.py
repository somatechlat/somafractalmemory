from typing import Any

from somafractalmemory.interfaces.graph import IGraphStore


class Neo4jGraphStore(IGraphStore):
    """Neo4j implementation of the graph store interface.

    Requires the neo4j Python driver. If unavailable, importing this module will raise an ImportError.
    """

    def __init__(self, uri: str, user: str, password: str) -> None:
        try:
            from neo4j import GraphDatabase
        except Exception as e:
            raise ImportError("neo4j driver is required for Neo4jGraphStore") from e
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def _run(self, query: str, **params: Any) -> Any:
        """Execute a query with proper error handling and transaction management."""
        try:
            with self._driver.session() as session:
                return session.run(query, **params)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Neo4j query failed: {query[:100]}... Error: {e}")
            raise

    def _run_in_transaction(
        self, queries_with_params: list[tuple[str, dict[str, Any]]]
    ) -> list[Any]:
        """Execute multiple queries in a single transaction for atomicity."""
        try:
            with self._driver.session() as session:
                with session.begin_transaction() as tx:
                    results = []
                    for query, params in queries_with_params:
                        result = tx.run(query, **params)
                        results.append(result)
                    tx.commit()
                    return results
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Neo4j transaction failed: {e}")
            raise

    def add_memory(self, coordinate: tuple[float, ...], memory_data: dict[str, Any]) -> None:
        self._run(
            """
            MERGE (n:Memory {coordinate: $coord})
            SET n += $props
            """,
            coord=list(coordinate),
            props=memory_data,
        )

    def add_link(
        self, from_coord: tuple[float, ...], to_coord: tuple[float, ...], link_data: dict[str, Any]
    ) -> None:
        self._run(
            """
            MERGE (a:Memory {coordinate: $from_coord})
            MERGE (b:Memory {coordinate: $to_coord})
            MERGE (a)-[r:LINK {type: $link_type}]->(b)
            SET r += $props
            """,
            from_coord=list(from_coord),
            to_coord=list(to_coord),
            link_type=link_data.get("type"),
            props=link_data,
        )

    def get_neighbors(
        self,
        coordinate: tuple[float, ...],
        link_type: str | None = None,
        limit: int | None = None,
    ) -> list[tuple[Any, dict[str, Any]]]:
        if link_type:
            query = "MATCH (a:Memory {coordinate:$coord})-[r:LINK {type:$type}]->(b) RETURN b.coordinate AS c, r AS r LIMIT $limit"
            params = {"coord": list(coordinate), "type": link_type, "limit": limit or 100}
        else:
            query = "MATCH (a:Memory {coordinate:$coord})-[r:LINK]->(b) RETURN b.coordinate AS c, r AS r LIMIT $limit"
            params = {"coord": list(coordinate), "limit": limit or 100}
        res = self._run(query, **params)
        out: list[tuple[Any, dict[str, Any]]] = []
        for rec in res:
            out.append((tuple(rec["c"]), dict(rec["r"])))
        return out

    def find_shortest_path(
        self,
        from_coord: tuple[float, ...],
        to_coord: tuple[float, ...],
        link_type: str | None = None,
    ) -> list[Any]:
        # Basic unweighted shortest path using variable length traversal; for weighted paths, use GDS offline
        if link_type:
            query = (
                "MATCH (a:Memory {coordinate:$from}),(b:Memory {coordinate:$to}), "
                "p = shortestPath((a)-[:LINK {type:$type}*..10]->(b)) "
                "RETURN [x IN nodes(p) | x.coordinate] AS path"
            )
            params = {"from": list(from_coord), "to": list(to_coord), "type": link_type}
        else:
            query = (
                "MATCH (a:Memory {coordinate:$from}),(b:Memory {coordinate:$to}), "
                "p = shortestPath((a)-[:LINK*..10]->(b)) "
                "RETURN [x IN nodes(p) | x.coordinate] AS path"
            )
            params = {"from": list(from_coord), "to": list(to_coord)}
        res = self._run(query, **params)
        rec = res.single()
        if not rec:
            return []
        return [tuple(c) for c in rec["path"]]

    def remove_memory(self, coordinate: tuple[float, ...]) -> None:
        self._run("MATCH (n:Memory {coordinate:$coord}) DETACH DELETE n", coord=list(coordinate))

    def clear(self) -> None:
        self._run("MATCH (n:Memory) DETACH DELETE n")

    def export_graph(self, path: str) -> None:
        # For Neo4j, exporting to GraphML is typically done via APOC; skip here
        pass

    def import_graph(self, path: str) -> None:
        # For Neo4j, importing GraphML is typically done via APOC; skip here
        pass

    def health_check(self) -> bool:
        try:
            self._run("RETURN 1 AS ok")
            return True
        except Exception:
            return False
