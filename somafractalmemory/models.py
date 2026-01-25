"""Django ORM models for SomaFractalMemory.

100% Django ORM - replaces raw psycopg2.
All database access goes through these models.
"""

import uuid
from datetime import datetime, timezone

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models


class Memory(models.Model):
    """Memory storage model.

    Stores episodic and semantic memories with coordinates and payloads.
    """

    class MemoryType(models.TextChoices):
        """Memorytype class implementation."""

        EPISODIC = "episodic", "Episodic"
        SEMANTIC = "semantic", "Semantic"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    namespace = models.CharField(max_length=255, db_index=True)
    coordinate = ArrayField(models.FloatField(), help_text="Memory coordinate as float array")
    coordinate_key = models.CharField(
        max_length=512, db_index=True, help_text="Stringified coordinate for lookups"
    )
    memory_type = models.CharField(
        max_length=20, choices=MemoryType.choices, default=MemoryType.EPISODIC
    )
    payload = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict, blank=True)
    tenant = models.CharField(max_length=255, default="default", db_index=True)
    importance = models.FloatField(default=0.0, db_index=True)
    access_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta class implementation."""

        db_table = "sfm_memories"
        verbose_name = "Memory"
        verbose_name_plural = "Memories"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["namespace", "coordinate_key"]),
            models.Index(fields=["namespace", "memory_type"]),
            models.Index(fields=["tenant", "namespace"]),
            GinIndex(fields=["payload"], name="sfm_memories_payload_gin"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["namespace", "coordinate_key"],
                name="unique_namespace_coordinate",
            ),
        ]

    def __str__(self):
        """Return string representation."""

        return f"Memory({self.coordinate_key}, {self.memory_type})"

    @classmethod
    def coord_to_key(cls, coord: tuple[float, ...] | list[float]) -> str:
        """Convert coordinate tuple to string key."""
        return ",".join(str(c) for c in coord)

    @classmethod
    def key_to_coord(cls, key: str) -> tuple[float, ...]:
        """Convert string key to coordinate tuple."""
        return tuple(float(p.strip()) for p in key.split(",") if p.strip())

    def touch(self):
        """Update access count and timestamp."""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)
        self.save(update_fields=["access_count", "last_accessed", "updated_at"])


class GraphLink(models.Model):
    """Graph link model.

    Stores relationships between memory coordinates.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    namespace = models.CharField(max_length=255, db_index=True)
    from_coordinate = ArrayField(models.FloatField())
    from_coordinate_key = models.CharField(max_length=512)
    to_coordinate = ArrayField(models.FloatField())
    to_coordinate_key = models.CharField(max_length=512)
    link_type = models.CharField(max_length=100, default="related", db_index=True)
    strength = models.FloatField(default=1.0)
    metadata = models.JSONField(default=dict, blank=True)
    tenant = models.CharField(max_length=255, default="default", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta class implementation."""

        db_table = "sfm_graph_links"
        verbose_name = "Graph Link"
        verbose_name_plural = "Graph Links"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["namespace", "from_coordinate_key"]),
            models.Index(fields=["namespace", "to_coordinate_key"]),
            models.Index(fields=["namespace", "link_type"]),
            models.Index(fields=["tenant", "namespace"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["namespace", "from_coordinate_key", "to_coordinate_key", "link_type"],
                name="unique_graph_link",
            ),
        ]

    def __str__(self):
        """Return string representation."""

        return f"Link({self.from_coordinate_key} -> {self.to_coordinate_key}, {self.link_type})"


class VectorEmbedding(models.Model):
    """Vector embedding metadata model.

    Tracks vector embeddings stored in Milvus.
    Metadata is stored here, vectors are in Milvus.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    memory = models.ForeignKey(Memory, on_delete=models.CASCADE, related_name="embeddings")
    collection_name = models.CharField(max_length=255)
    milvus_id = models.BigIntegerField(null=True, help_text="ID in Milvus collection")
    vector_dim = models.IntegerField(default=768)
    model_name = models.CharField(max_length=255, default="microsoft/codebert-base")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta class implementation."""

        db_table = "sfm_vector_embeddings"
        verbose_name = "Vector Embedding"
        verbose_name_plural = "Vector Embeddings"
        indexes = [
            models.Index(fields=["collection_name", "milvus_id"]),
        ]

    def __str__(self):
        """Return string representation."""

        return f"Embedding({self.memory_id}, milvus={self.milvus_id})"


class MemoryNamespace(models.Model):
    """Memory namespace configuration.

    Stores namespace-level settings and statistics.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    tenant = models.CharField(max_length=255, default="default", db_index=True)
    description = models.TextField(blank=True)
    config = models.JSONField(default=dict, help_text="Namespace-specific configuration")
    total_memories = models.IntegerField(default=0)
    episodic_count = models.IntegerField(default=0)
    semantic_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta class implementation."""

        db_table = "sfm_namespaces"
        verbose_name = "Memory Namespace"
        verbose_name_plural = "Memory Namespaces"

    def __str__(self):
        """Return string representation."""

        return f"Namespace({self.name})"

    def update_stats(self):
        """Update namespace statistics from actual counts."""
        from django.db.models import Count, Q

        stats = Memory.objects.filter(namespace=self.name).aggregate(
            total=Count("id"),
            episodic=Count("id", filter=Q(memory_type=Memory.MemoryType.EPISODIC)),
            semantic=Count("id", filter=Q(memory_type=Memory.MemoryType.SEMANTIC)),
        )
        self.total_memories = stats["total"] or 0
        self.episodic_count = stats["episodic"] or 0
        self.semantic_count = stats["semantic"] or 0
        self.save(
            update_fields=["total_memories", "episodic_count", "semantic_count", "updated_at"]
        )


class AuditLog(models.Model):
    """Audit log for memory operations.

    Tracks all CRUD operations for compliance.
    """

    class Action(models.TextChoices):
        """Action class implementation."""

        CREATE = "create", "Create"
        READ = "read", "Read"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        SEARCH = "search", "Search"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=20, choices=Action.choices)
    namespace = models.CharField(max_length=255, db_index=True)
    coordinate_key = models.CharField(max_length=512, blank=True)
    tenant = models.CharField(max_length=255, default="default", db_index=True)
    user_id = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        """Meta class implementation."""

        db_table = "sfm_audit_log"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["namespace", "action", "timestamp"]),
            models.Index(fields=["tenant", "timestamp"]),
        ]

    def __str__(self):
        """Return string representation."""

        return f"Audit({self.action}, {self.coordinate_key}, {self.timestamp})"
