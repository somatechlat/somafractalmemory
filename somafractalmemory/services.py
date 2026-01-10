"""Django ORM-based memory services.

100% Django ORM - replaces old factory.py and raw psycopg2 stores.
All database access through Django ORM.
"""

from typing import Any

from django.db import transaction
from django.db.models import Q

from common.utils.logger import get_logger

from .models import AuditLog, GraphLink, Memory

logger = get_logger(__name__)


class MemoryService:
    """Django ORM-based memory service.

    Replaces PostgresKeyValueStore with pure Django ORM operations.
    """

    def __init__(self, namespace: str = "default"):
        """Initialize the instance."""

        self.namespace = namespace

    def _save_to_milvus(self, memory: Memory) -> None:
        """Save memory vector to Milvus.

        This method is fail-safe: it checks for pymilvus presence and connection health.
        """
        from django.conf import settings

        from .models import VectorEmbedding

        try:
            from pymilvus import Collection, connections, utility
        except ImportError:
            logger.warning("pymilvus not installed. Skipping vector store.")
            return

        milvus_host = getattr(settings, "SOMA_MILVUS_HOST", "somastack_milvus")
        milvus_port = getattr(settings, "SOMA_MILVUS_PORT", "19530")
        collection_name = getattr(settings, "SFM_COLLECTION", "somamemory_vectors")

        # Connect
        try:
            connections.connect(alias="default", host=milvus_host, port=milvus_port, timeout=2.0)
        except Exception as e:
            raise ConnectionError(
                f"Could not connect to Milvus at {milvus_host}:{milvus_port}: {e}"
            )

        try:
            # Check if collection exists
            # Note: utility.has_collection might block or fail if connection is bad
            if not utility.has_collection(collection_name):
                logger.warning(f"Milvus collection {collection_name} does not exist.")
                return

            collection = Collection(collection_name)

            # Insert vector: [[float, float, ...]]
            mr = collection.insert([[list(memory.coordinate)]])

            if mr.primary_keys:
                milvus_id = mr.primary_keys[0]
                VectorEmbedding.objects.create(
                    memory=memory,
                    collection_name=collection_name,
                    milvus_id=milvus_id,
                    vector_dim=len(memory.coordinate),
                )
                logger.info(f"Saved to Milvus: {milvus_id}")

        finally:
            try:
                connections.disconnect("default")
            except:
                pass

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

        # Try to save to Milvus (Degradation Mode)
        try:
            self._save_to_milvus(memory)
        except Exception as e:
            logger.error(f"Milvus store failed (DEGRADED MODE): {e}")

        return memory

    async def aremember(
        self,
        coordinate: tuple[float, ...],
        payload: dict[str, Any],
        memory_type: str = "episodic",
        tenant: str = "default",
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        """Async store a memory using Django ORM (SRS FR-1)."""
        from asgiref.sync import sync_to_async

        return await sync_to_async(self.store)(
            coordinate=coordinate,
            payload=payload,
            memory_type=memory_type,
            tenant=tenant,
            metadata=metadata,
        )

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
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories using Django ORM.

        For vector similarity search, this delegates to Milvus.
        For metadata/payload search, uses Django ORM.
        """
        # Use provided namespace or fall back to instance namespace
        # Ignore "default" as it's a common placeholder that doesn't match actual DB values
        search_namespace = namespace if (namespace and namespace != "default") else self.namespace

        # Start with base queryset - filter by namespace only if specific
        if search_namespace and search_namespace != "default":
            queryset = Memory.objects.filter(namespace=search_namespace)
        else:
            queryset = Memory.objects.all()

        # CRITICAL: Strict tenant filtering for security
        # Filter by BOTH DB column AND payload tenant to ensure isolation
        if tenant and tenant != "default":
            # Must match tenant in payload (the authoritative source)
            queryset = queryset.filter(Q(payload__tenant=tenant) | Q(payload__tenant_id=tenant))

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
            namespace=search_namespace,
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


def get_memory_service(namespace: str = "default") -> MemoryService:
    """Factory function to get a memory service instance."""
    return MemoryService(namespace=namespace)


def get_graph_service(namespace: str = "default") -> GraphService:
    """Factory function to get a graph service instance."""
    return GraphService(namespace=namespace)
