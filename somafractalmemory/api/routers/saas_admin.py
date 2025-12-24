"""
SaaS Admin Router for SomaFractalMemory.

API Key management endpoints for standalone mode.
Namespace-level access control.

VIBE Coding Rules v5.2 - ALL 7 PERSONAS.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from somafractalmemory.saas.auth import APIKeyAuth, has_permission
from somafractalmemory.saas.models import APIKey, UsageRecord

logger = logging.getLogger(__name__)

router = Router(tags=["SaaS Admin"])


# =============================================================================
# SCHEMAS
# =============================================================================


class APIKeyCreateSchema(Schema):
    """Create API key request."""

    name: str
    tenant: str
    allowed_namespaces: list[str] = []
    permissions: list[str] = ["read", "write"]
    expires_days: int | None = None
    is_test: bool = False


class APIKeyResponseSchema(Schema):
    """API key response (without full key)."""

    id: UUID
    name: str
    tenant: str
    key_prefix: str
    permissions: list
    allowed_namespaces: list
    is_active: bool
    is_test: bool
    last_used_at: datetime | None
    created_at: datetime


class APIKeyCreatedSchema(Schema):
    """Response when API key is created (includes full key ONCE)."""

    id: UUID
    name: str
    key: str
    key_prefix: str
    permissions: list


class UsageStatsSchema(Schema):
    """Usage statistics."""

    tenant: str
    period_start: datetime
    period_end: datetime
    total_operations: int
    by_operation: dict


# =============================================================================
# API KEY ENDPOINTS
# =============================================================================


@router.get("/api-keys", response=list[APIKeyResponseSchema], auth=APIKeyAuth())
def list_api_keys(request, tenant: str | None = None):
    """
    List API keys.

    If tenant specified, filter by tenant.
    Requires admin permission.
    """
    if not has_permission(request, "admin"):
        raise HttpError(403, "Admin permission required")

    queryset = APIKey.objects.all()

    if tenant:
        queryset = queryset.filter(tenant=tenant)

    keys = queryset.order_by("-created_at")[:100]

    return [
        {
            "id": k.id,
            "name": k.name,
            "tenant": k.tenant,
            "key_prefix": k.key_prefix,
            "permissions": k.permissions,
            "allowed_namespaces": k.allowed_namespaces,
            "is_active": k.is_active,
            "is_test": k.is_test,
            "last_used_at": k.last_used_at,
            "created_at": k.created_at,
        }
        for k in keys
    ]


@router.post("/api-keys", response=APIKeyCreatedSchema, auth=APIKeyAuth())
def create_api_key(request, data: APIKeyCreateSchema):
    """
    Create a new API key.

    ⚠️ The full key is only returned ONCE!
    """
    if not has_permission(request, "admin"):
        raise HttpError(403, "Admin permission required")

    # Generate key
    full_key, prefix, key_hash = APIKey.generate_key(is_test=data.is_test)

    # Calculate expiration
    expires_at = None
    if data.expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_days)

    # Create key
    api_key = APIKey.objects.create(
        tenant=data.tenant,
        name=data.name,
        key_prefix=prefix,
        key_hash=key_hash,
        permissions=data.permissions,
        allowed_namespaces=data.allowed_namespaces,
        is_test=data.is_test,
        expires_at=expires_at,
    )

    logger.info(f"Created SFM API key: {api_key.name} for tenant {data.tenant}")

    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": full_key,
        "key_prefix": prefix,
        "permissions": api_key.permissions,
    }


@router.delete("/api-keys/{key_id}", auth=APIKeyAuth())
def revoke_api_key(request, key_id: UUID):
    """Revoke an API key."""
    if not has_permission(request, "admin"):
        raise HttpError(403, "Admin permission required")

    try:
        api_key = APIKey.objects.get(id=key_id)
        api_key.is_active = False
        api_key.revoked_at = datetime.now(timezone.utc)
        api_key.save()

        logger.info(f"Revoked SFM API key: {api_key.name}")

        return {"status": "revoked", "key_id": str(key_id)}
    except APIKey.DoesNotExist as e:
        raise HttpError(404, "API key not found") from e


# =============================================================================
# USAGE STATS ENDPOINTS
# =============================================================================


@router.get("/usage/{tenant}", response=UsageStatsSchema, auth=APIKeyAuth())
def get_usage_stats(
    request,
    tenant: str,
    days: int = 30,
):
    """Get usage statistics for a tenant."""
    auth = getattr(request, "auth", {})

    # Check access
    if auth.get("tenant") != tenant and not has_permission(request, "admin"):
        raise HttpError(403, "Access denied")

    # Calculate period
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    # Aggregate usage
    from django.db.models import Sum
    from django.db.models.functions import Coalesce

    total = UsageRecord.objects.filter(
        tenant=tenant,
        timestamp__gte=start,
        timestamp__lte=end,
    ).aggregate(total=Coalesce(Sum("count"), 0))["total"]

    by_operation = {}
    for op in UsageRecord.OperationType.values:
        count = UsageRecord.objects.filter(
            tenant=tenant,
            operation=op,
            timestamp__gte=start,
        ).aggregate(total=Coalesce(Sum("count"), 0))["total"]
        by_operation[op] = count

    return {
        "tenant": tenant,
        "period_start": start,
        "period_end": end,
        "total_operations": total,
        "by_operation": by_operation,
    }
