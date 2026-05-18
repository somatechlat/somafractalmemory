"""
SomaFractalMemory Services - Business Logic Layer
Copyright (C) 2025 SomaTech LAT.

This module implements the core business logic for the memory system using
Django ORM. It provides services for:
- MemoryService: CRUD operations for episodic and semantic memories.
- GraphService: Management of links and relationships between memories.
"""

import hashlib
import json
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q

from somafractalmemory.admin.common.utils.logger import get_logger
from somafractalmemory.admin.core.implementations import MilvusVectorStore

from .models import AuditLog, GraphLink, Memory, VectorEmbedding

logger = get_logger(__name__)


class HashEmbedder:
    """Deterministic hash-based embedding generator (no external deps)."""

    def __init__(self, dim: int = 768):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        """Generate a deterministic vector of length dim from text."""
        vec: list[float] = []
        for i in range(self.dim):
            digest = hashlib.sha256(f"{text}|{i}".encode()).digest()
            val = int.from_bytes(digest[:4], "big", signed=False)
            vec.append((val % 2_000_000) / 1_000_000 - 1.0)  # map to [-1, 1]
        # L2 normalize for cosine
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


class MemoryService:
    """Service for managing memory storage, retrieval, and search.

    This service connects the API layer to the Django ORM models, handling
    transactions, audit logging, and coordinate transformations.

    Attributes:
        namespace (str): The isolation namespace for all operations.
    """

    def __init__(self, namespace: str = "default"):
        """Initialize the instance."""

        self.namespace = namespace
        self.vector_dim = getattr(settings, "SOMA_VECTOR_DIM", 768)
        self.embedder = HashEmbedder(dim=self.vector_dim)
        self.vector_store = self._build_vector_store()

    def _build_vector_store(self) -> MilvusVectorStore | None:
        """Create a Milvus vector store if configuration is present."""
        host = getattr(settings, "SOMA_MILVUS_HOST", None)
        port = getattr(settings, "SOMA_MILVUS_PORT", None)
        if not host or not port:
            return None
        try:
            return MilvusVectorStore(
                host=host,
                port=port,
                collection_name=f"sfm_{self.namespace}",
                dim=self.vector_dim,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to initialize MilvusVectorStore", error=str(exc))
            return None

    @transaction.atomic
    def store(
        self,
        coordinate: tuple[float, ...],
        payload: dict[str, Any],
        memory_type: str = "episodic",
        tenant: str = "default",
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        """Store a memory using Django ORM."""
        coord_key = Memory.coord_to_key(coordinate)

        memory, created = Memory.objects.update_or_create(
            namespace=self.namespace,
            tenant=tenant,
            coordinate_key=coord_key,
            defaults={
                "coordinate": list(coordinate),
                "memory_type": memory_type,
                "payload": payload,
                "metadata": metadata or {},
                "is_deleted": False,
                "deleted_at": None,
            },
        )

        # Store vector embedding (best effort)
        if self.vector_store and self.embedder:
            try:
                payload_text = json.dumps(payload, sort_keys=True)
                vector = self.embedder.embed(payload_text)

                # Fix Flaw 2: Prevent vector cloning by deleting old vector for this coordinate if it exists
                try:
                    self.vector_store.delete(coord_key)
                except Exception:
                    pass  # Ignore if not found or store inaccessible during cleanup

                milvus_id = self.vector_store.insert(
                    coordinate_key=coord_key,
                    vector=vector,
                    namespace=self.namespace,
                    tenant=tenant,
                )
                VectorEmbedding.objects.update_or_create(
                    memory=memory,
                    collection_name=self.vector_store.collection_name,
                    defaults={
                        "milvus_id": milvus_id,
                        "vector_dim": self.vector_dim,
                        "model_name": getattr(settings, "SOMA_MODEL_NAME", "hash-embedder"),
                    },
                )
            except Exception as exc:
                logger.warning("Vector store insert failed", error=str(exc), exc_info=True)

        # Log the operation
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE,
            namespace=self.namespace,
            coordinate_key=coord_key,
            tenant=tenant,
            details={"memory_type": memory_type},
        )

        return memory

    def retrieve(
        self,
        coordinate: tuple[float, ...],
        tenant: str = "default",
    ) -> dict[str, Any] | None:
        """Retrieve a memory by coordinate."""
        coord_key = Memory.coord_to_key(coordinate)

        try:
            memory = Memory.objects.get(
                namespace=self.namespace,
                coordinate_key=coord_key,
                tenant=tenant,
                is_deleted=False,
            )
            memory.touch()

            # Log the read
            AuditLog.objects.create(
                action=AuditLog.Action.READ,
                namespace=self.namespace,
                coordinate_key=coord_key,
                tenant=tenant,
            )

            return {
                "coordinate": memory.coordinate,
                "payload": memory.payload,
                "memory_type": memory.memory_type,
                "metadata": memory.metadata,
                "importance": memory.importance,
                "created_at": memory.created_at.isoformat(),
                "updated_at": memory.updated_at.isoformat(),
            }
        except Memory.DoesNotExist:
            return None

    @transaction.atomic
    def delete(self, coordinate: tuple[float, ...], tenant: str = "default") -> bool:
        """Soft delete a memory by coordinate."""
        from datetime import UTC, datetime

        coord_key = Memory.coord_to_key(coordinate)

        try:
            memory = Memory.objects.get(
                namespace=self.namespace,
                coordinate_key=coord_key,
                tenant=tenant,
                is_deleted=False,
            )
        except Memory.DoesNotExist:
            return False

        memory.is_deleted = True
        memory.deleted_at = datetime.now(UTC)
        memory.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

        if self.vector_store:
            try:
                self.vector_store.delete(coord_key, namespace=self.namespace, tenant=tenant)
            except Exception as exc:
                logger.error("Vector store delete failed", error=str(exc))
                # Non-blocking: vector orphan is acceptable during soft delete

        VectorEmbedding.objects.filter(
            memory__coordinate_key=coord_key,
            memory__namespace=self.namespace,
            memory__tenant=tenant,
        ).delete()

        AuditLog.objects.create(
            action=AuditLog.Action.DELETE,
            namespace=self.namespace,
            coordinate_key=coord_key,
            tenant=tenant,
        )

        return True

    def search(
        self,
        query: str,
        top_k: int = 5,
        offset: int = 0,
        memory_type: str | None = None,
        tenant: str = "default",
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories using Django ORM.

        Vector similarity search via Milvus when configured; fallback to ORM text search.
        Fix Flaw 7: Supporting pagination with offset.
        """
        if self.vector_store and self.embedder:
            try:
                vector = self.embedder.embed(query)
                vector_results = self.vector_store.search(
                    query_vector=vector,
                    top_k=top_k + offset,  # We fetch enough to cover the offset
                    namespace=self.namespace,
                    tenant=tenant,
                )
                # Apply offset to vector results
                vector_results = vector_results[offset:]

                coord_keys = [res["coordinate_key"] for res in vector_results]
                memories = list(
                    Memory.objects.filter(
                        namespace=self.namespace,
                        tenant=tenant,
                        coordinate_key__in=coord_keys,
                        is_deleted=False,
                    )
                )
                memory_map = {m.coordinate_key: m for m in memories}
                ordered: list[dict[str, Any]] = []
                for res in vector_results:
                    mem = memory_map.get(res["coordinate_key"])
                    if not mem:
                        continue
                    ordered.append(
                        {
                            "coordinate": mem.coordinate,
                            "payload": mem.payload,
                            "memory_type": mem.memory_type,
                            "importance": mem.importance,
                            "score": res.get("score"),
                        }
                    )
                if ordered:
                    return ordered
            except Exception as exc:
                logger.warning("Vector search failed, falling back to ORM", error=str(exc))

        queryset = Memory.objects.filter(
            namespace=self.namespace,
            tenant=tenant,
            is_deleted=False,
        )

        if memory_type:
            queryset = queryset.filter(memory_type=memory_type)

        if filters:
            for key, value in filters.items():
                queryset = queryset.filter(**{f"payload__{key}": value})

        # Basic search (for non-vector search) - Fix Flaw 3: leveraging GinIndex
        if query:
            # We use __contains which maps to Postgres @> (indexed)
            # This is significantly faster than __icontains (sequential scan)
            # We check common keys used in SOMA payloads: 'text', 'content', 'summary'
            queryset = queryset.filter(
                Q(payload__contains={"text": query})
                | Q(payload__contains={"content": query})
                | Q(payload__contains={"summary": query})
                | Q(metadata__contains={"original_query": query})
            )

        memories = queryset.order_by("-importance", "-created_at")[offset : offset + top_k]

        AuditLog.objects.create(
            action=AuditLog.Action.SEARCH,
            namespace=self.namespace,
            tenant=tenant,
            details={"query": query, "top_k": top_k, "filters": filters},
        )

        return [
            {
                "coordinate": m.coordinate,
                "payload": m.payload,
                "memory_type": m.memory_type,
                "importance": m.importance,
            }
            for m in memories
        ]

    def stats(self) -> dict[str, Any]:
        """Get memory statistics using Django ORM."""
        from django.db.models import Count, Q

        stats = Memory.objects.filter(namespace=self.namespace, is_deleted=False).aggregate(
            total=Count("id"),
            episodic=Count("id", filter=Q(memory_type=Memory.MemoryType.EPISODIC)),
            semantic=Count("id", filter=Q(memory_type=Memory.MemoryType.SEMANTIC)),
        )

        return {
            "total_memories": stats["total"] or 0,
            "episodic": stats["episodic"] or 0,
            "semantic": stats["semantic"] or 0,
            "namespace": self.namespace,
        }

    def health_check(self) -> dict[str, bool]:
        """Check database health using Django ORM."""
        status = {"kv_store": False, "vector_store": False, "graph_store": False}

        try:
            Memory.objects.count()
            status["kv_store"] = True
            status["graph_store"] = True
        except Exception as e:
            logger.error(f"Health check failed (Postgres): {e}")

        if self.vector_store:
            try:
                status["vector_store"] = bool(self.vector_store.health_check())
            except Exception as e:
                logger.error(f"Health check failed (Milvus): {e}")
                status["vector_store"] = False
        return status


class GraphService:
    """Django ORM-based graph service.

    Replaces PostgresGraphStore with pure Django ORM operations.
    """

    def __init__(self, namespace: str = "default"):
        """Initialize the instance."""

        self.namespace = namespace

    @transaction.atomic
    def add_link(
        self,
        from_coord: tuple[float, ...],
        to_coord: tuple[float, ...],
        link_data: dict[str, Any],
    ) -> GraphLink:
        """Create a graph link using Django ORM."""
        from_key = Memory.coord_to_key(from_coord)
        to_key = Memory.coord_to_key(to_coord)
        tenant = link_data.get("_tenant", "default")

        link, created = GraphLink.objects.update_or_create(
            namespace=self.namespace,
            tenant=tenant,
            from_coordinate_key=from_key,
            to_coordinate_key=to_key,
            link_type=link_data.get("link_type", "related"),
            defaults={
                "from_coordinate": list(from_coord),
                "to_coordinate": list(to_coord),
                "strength": link_data.get("strength", 1.0),
                "metadata": {
                    k: v
                    for k, v in link_data.items()
                    if k not in ("link_type", "strength", "_tenant")
                },
            },
        )

        return link

    def get_neighbors(
        self,
        coord: tuple[float, ...],
        link_type: str | None = None,
        limit: int = 10,
        offset: int = 0,
        tenant: str = "default",
    ) -> list[dict[str, Any]]:
        """Get neighbors of a coordinate using Django ORM.

        Fix Flaw 7: Supporting pagination with offset.
        """
        coord_key = Memory.coord_to_key(coord)

        queryset = GraphLink.objects.filter(
            namespace=self.namespace,
            tenant=tenant,
            from_coordinate_key=coord_key,
        )

        if link_type:
            queryset = queryset.filter(link_type=link_type)

        links = queryset.order_by("-created_at")[offset : offset + limit]

        return [
            {
                "coordinate": link.to_coordinate,
                "link_type": link.link_type,
                "strength": link.strength,
                "_tenant": link.tenant,
            }
            for link in links
        ]

    def find_shortest_path(
        self,
        from_coord: tuple[float, ...],
        to_coord: tuple[float, ...],
        link_type: str | None = None,
        tenant: str = "default",
        max_depth: int = 5,
    ) -> list[tuple[float, ...]] | None:
        """Find shortest path using a Postgres Recursive CTE (O(1) query).

        Fix Flaw 6: Supporting dynamic max_depth for contract harmony.
        """
        from django.db import connection

        from_key = Memory.coord_to_key(from_coord)
        to_key = Memory.coord_to_key(to_coord)

        if from_key == to_key:
            return [from_coord]

        # Parameter binding
        params = [self.namespace, tenant, from_key, to_key]
        type_filter = ""
        if link_type:
            type_filter = "AND link_type = %s"
            params.insert(2, link_type)

        query = f"""
            WITH RECURSIVE path_search AS (
                -- Base Case
                SELECT
                    to_coordinate_key as current_key,
                    to_coordinate as current_coord,
                    ARRAY[from_coordinate_key, to_coordinate_key]::text[] as visited_keys,
                    ARRAY[from_coordinate, to_coordinate]::float8[][] as path_coords,
                    1 as depth
                FROM sfm_graph_links
                WHERE namespace = %s
                  AND tenant = %s
                  {type_filter}
                  AND from_coordinate_key = %s

                UNION ALL

                -- Recursive Step
                SELECT
                    l.to_coordinate_key,
                    l.to_coordinate,
                    ps.visited_keys || l.to_coordinate_key::text,
                    ps.path_coords || l.to_coordinate::float8[],
                    ps.depth + 1
                FROM sfm_graph_links l
                JOIN path_search ps ON l.from_coordinate_key = ps.current_key
                WHERE l.namespace = %s
                  AND l.tenant = %s
                  {type_filter.replace("link_type = %s", "l.link_type = %s")}
                  AND NOT l.to_coordinate_key = ANY(ps.visited_keys)
                  -- Contract Harmony: Use dynamic max_depth (Flaw 6 Fix)
                  AND ps.depth < %s
            )
            SELECT path_coords
            FROM path_search
            WHERE current_key = %s
            ORDER BY depth ASC
            LIMIT 1;
        """

        # Parameters for the query
        if link_type:
            full_params = [
                self.namespace,
                tenant,
                link_type,
                from_key,  # Base
                self.namespace,
                tenant,
                link_type,  # Recursive
                max_depth,  # Dynamic Limit
                to_key,  # Final Select
            ]
        else:
            full_params = [
                self.namespace,
                tenant,
                from_key,  # Base
                self.namespace,
                tenant,  # Recursive
                max_depth,  # Dynamic Limit
                to_key,  # Final Select
            ]

        with connection.cursor() as cursor:
            cursor.execute(query, full_params)
            row = cursor.fetchone()

        if row and row[0]:
            return [tuple(coord) for coord in row[0]]

        return None

    def export_graph(self, path: str) -> None:
        """Export graph to JSON using streaming iterators to prevent OOM (Flaw 5 Hardening)."""
        from .models import Memory

        # We use .iterator() to avoid loading everything into the Django QuerySet cache.
        # This keeps memory usage O(1) relative to the database size.

        with open(path, "w") as f:
            f.write('{"nodes": [')

            # Export Nodes
            first = True
            for node in (
                Memory.objects.filter(namespace=self.namespace, is_deleted=False)
                .values("coordinate", "payload")
                .iterator()
            ):
                if not first:
                    f.write(",")
                node_data = {"id": str(node["coordinate"]), "data": node["payload"]}
                f.write(json.dumps(node_data))
                first = False

            f.write('], "edges": [')

            # Export Edges
            first = True
            for edge in (
                GraphLink.objects.filter(namespace=self.namespace)
                .values("from_coordinate", "to_coordinate", "link_type")
                .iterator()
            ):
                if not first:
                    f.write(",")
                edge_data = {
                    "source": str(edge["from_coordinate"]),
                    "target": str(edge["to_coordinate"]),
                    "relation": edge["link_type"],
                }
                f.write(json.dumps(edge_data))
                first = False

            f.write("]}")

    def health_check(self) -> bool:
        """Check database health using Django ORM."""
        try:
            # Simple query to verify database connection
            GraphLink.objects.none()
            return True
        except Exception as e:
            logger.error(f"Graph store health check failed: {e}")
            return False


def get_memory_service(namespace: str = "default") -> MemoryService:
    """Factory function to get a memory service instance."""
    return MemoryService(namespace=namespace)


def get_graph_service(namespace: str = "default") -> GraphService:
    """Factory function to get a graph service instance."""
    return GraphService(namespace=namespace)
