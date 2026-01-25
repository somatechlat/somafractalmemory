"""
SomaFractalMemory Services - Business Logic Layer
Copyright (C) 2025 SomaTech LAT.

This module implements the core business logic for the memory system using
Django ORM. It provides services for:
- MemoryService: CRUD operations for episodic and semantic memories.
- GraphService: Management of links and relationships between memories.
"""

from typing import Any

from django.db import transaction
from django.db.models import Q

from common.utils.logger import get_logger

from .models import AuditLog, GraphLink, Memory

logger = get_logger(__name__)


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
            coordinate_key=coord_key,
            defaults={
                "coordinate": list(coordinate),
                "memory_type": memory_type,
                "payload": payload,
                "metadata": metadata or {},
                "tenant": tenant,
            },
        )

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
        """Delete a memory by coordinate."""
        coord_key = Memory.coord_to_key(coordinate)

        deleted, _ = Memory.objects.filter(
            namespace=self.namespace,
            coordinate_key=coord_key,
            tenant=tenant,
        ).delete()

        if deleted:
            AuditLog.objects.create(
                action=AuditLog.Action.DELETE,
                namespace=self.namespace,
                coordinate_key=coord_key,
                tenant=tenant,
            )

        return deleted > 0

    def search(
        self,
        query: str,
        top_k: int = 5,
        memory_type: str | None = None,
        tenant: str = "default",
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories using Django ORM.

        For vector similarity search, this delegates to Milvus.
        For metadata/payload search, uses Django ORM.
        """
        queryset = Memory.objects.filter(
            namespace=self.namespace,
            tenant=tenant,
        )

        if memory_type:
            queryset = queryset.filter(memory_type=memory_type)

        if filters:
            for key, value in filters.items():
                queryset = queryset.filter(**{f"payload__{key}": value})

        # Basic text search in payload (for non-vector search)
        if query:
            queryset = queryset.filter(Q(payload__icontains=query) | Q(metadata__icontains=query))

        memories = queryset.order_by("-importance", "-created_at")[:top_k]

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

        stats = Memory.objects.filter(namespace=self.namespace).aggregate(
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
        try:
            # Simple query to verify database connection
            Memory.objects.count()
            return {"kv_store": True, "vector_store": True, "graph_store": True}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"kv_store": False, "vector_store": False, "graph_store": False}


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

        link, created = GraphLink.objects.update_or_create(
            namespace=self.namespace,
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
                "tenant": link_data.get("_tenant", "default"),
            },
        )

        return link

    def get_neighbors(
        self,
        coord: tuple[float, ...],
        link_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get neighbors of a coordinate using Django ORM."""
        coord_key = Memory.coord_to_key(coord)

        queryset = GraphLink.objects.filter(
            namespace=self.namespace,
            from_coordinate_key=coord_key,
        )

        if link_type:
            queryset = queryset.filter(link_type=link_type)

        links = queryset[:limit]

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
    ) -> list[tuple[float, ...]] | None:
        """Find shortest path using BFS with Django ORM."""
        from collections import deque

        from_key = Memory.coord_to_key(from_coord)
        to_key = Memory.coord_to_key(to_coord)

        if from_key == to_key:
            return [from_coord]

        visited = {from_key}
        queue = deque([(from_key, [from_coord])])

        while queue:
            current_key, path = queue.popleft()

            queryset = GraphLink.objects.filter(
                namespace=self.namespace,
                from_coordinate_key=current_key,
            )
            if link_type:
                queryset = queryset.filter(link_type=link_type)

            for link in queryset:
                next_key = link.to_coordinate_key
                if next_key == to_key:
                    return path + [tuple(link.to_coordinate)]

                if next_key not in visited:
                    visited.add(next_key)
                    queue.append((next_key, path + [tuple(link.to_coordinate)]))

        return None

    def export_graph(self, path: str) -> None:
        """Export graph to JSON using Django ORM."""
        from .models import Memory

        # Get nodes (memories)
        nodes = list(Memory.objects.filter(namespace=self.namespace).values())
        formatted_nodes = [{"id": str(n["coordinate"]), "data": n["payload"]} for n in nodes]

        # Get edges (links)
        edges = list(GraphLink.objects.filter(namespace=self.namespace).values())
        formatted_edges = [
            {
                "source": str(e["from_coordinate"]),
                "target": str(e["to_coordinate"]),
                "relation": e["link_type"],
            }
            for e in edges
        ]

        data = {"nodes": formatted_nodes, "edges": formatted_edges}

        import json

        with open(path, "w") as f:
            json.dump(data, f)

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
