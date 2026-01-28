"""
SomaFractalMemory AAAS Models.

API key authentication and usage tracking.
Can work standalone or integrate with SomaBrain.
"""

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from django.db import models
from django.db.models import F

# =============================================================================
# API KEY MODEL (Standalone Mode)
# =============================================================================


class APIKey(models.Model):
    """
    API key for SomaFractalMemory access.

    Can run standalone or defer to SomaBrain's central auth.
    Format: sfm_live_a1b2c3... or sfm_test_a1b2c3...
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    # Owner
    tenant = models.CharField(max_length=255, db_index=True)
    name = models.CharField(max_length=255)

    # Key
    key_prefix = models.CharField(max_length=12, db_index=True)
    key_hash = models.CharField(max_length=64)

    # Permissions (namespaces this key can access)
    allowed_namespaces = models.JSONField(default=list, blank=True)
    permissions = models.JSONField(default=list, blank=True)

    # Rate limiting
    rate_limit_rps = models.IntegerField(default=10)

    # Status
    is_active = models.BooleanField(default=True)
    is_test = models.BooleanField(default=False)

    # Usage
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)
    usage_count = models.BigIntegerField(default=0)

    # Lifecycle
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Meta class implementation."""

        db_table = "sfm_api_keys"
        ordering = ["-created_at"]
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
            models.Index(fields=["key_prefix", "key_hash"]),
        ]

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.name} ({self.key_prefix}...)"

    @classmethod
    def generate_key(cls, is_test: bool = False) -> tuple[str, str, str]:
        """Generate a new SFM API key."""
        mode = "test" if is_test else "live"
        random_part = secrets.token_hex(24)
        full_key = f"sfm_{mode}_{random_part}"
        prefix = f"sfm_{mode}_"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        return full_key, prefix, key_hash

    @classmethod
    def verify_key(cls, full_key: str) -> "APIKey | None":
        """Verify an API key and return the object if valid."""
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        try:
            api_key = cls.objects.get(key_hash=key_hash, is_active=True)
            if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
                return None
            return api_key
        except cls.DoesNotExist:
            return None

    def touch(self, ip_address: str | None = None) -> None:
        """Update usage stats."""
        self.last_used_at = datetime.now(timezone.utc)
        if ip_address:
            self.last_used_ip = str(ip_address)
        # Use F() expression for atomic increment to avoid race conditions
        self.usage_count = F("usage_count") + 1
        self.save(update_fields=["last_used_at", "last_used_ip", "usage_count"])


# =============================================================================
# USAGE RECORD
# =============================================================================


class UsageRecord(models.Model):
    """Usage tracking for billing integration."""

    class OperationType(models.TextChoices):
        """Operationtype class implementation."""

        MEMORY_STORE = "memory_store", "Memory Store"
        MEMORY_RECALL = "memory_recall", "Memory Recall"
        MEMORY_DELETE = "memory_delete", "Memory Delete"
        GRAPH_LINK = "graph_link", "Graph Link"
        GRAPH_QUERY = "graph_query", "Graph Query"
        VECTOR_SEARCH = "vector_search", "Vector Search"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.CharField(max_length=255, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    hour_bucket = models.DateTimeField(db_index=True)
    operation = models.CharField(max_length=50, choices=OperationType.choices)
    count = models.IntegerField(default=1)
    bytes_processed = models.BigIntegerField(default=0)
    api_key_id = models.UUIDField(null=True, blank=True)

    # Billing sync
    synced_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        """Meta class implementation."""

        db_table = "sfm_usage_records"
        ordering = ["-timestamp"]
        verbose_name = "Usage Record"
        verbose_name_plural = "Usage Records"
        indexes = [
            models.Index(fields=["tenant", "hour_bucket"]),
            models.Index(fields=["tenant", "operation", "hour_bucket"]),
        ]

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.tenant}:{self.operation} ({self.count})"

    @classmethod
    def record(
        cls,
        tenant: str,
        operation: str,
        count: int = 1,
        bytes_processed: int = 0,
        api_key_id: "str | None" = None,
    ) -> "UsageRecord":
        """Record a usage event."""
        now = datetime.now(timezone.utc)
        hour_bucket = now.replace(minute=0, second=0, microsecond=0)
        return cls.objects.create(
            tenant=tenant,
            operation=operation,
            count=count,
            bytes_processed=bytes_processed,
            hour_bucket=hour_bucket,
            api_key_id=api_key_id,
        )
