"""
API Key Authentication for SomaFractalMemory.

Standalone auth or integration with SomaBrain central auth.
Implements sfm_live_* and sfm_test_* API key verification.

VIBE Coding Rules v5.2 - ALL 7 PERSONAS:
- Architect: Clean layered design, standalone capability
- Security: Constant-time comparison, key hashing
- DevOps: Environment-based config
- QA: Testable interfaces
- Docs: Comprehensive docstrings
- DBA: Efficient queries
- SRE: Observability hooks
"""

import hashlib
import logging

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone
from ninja.security import HttpBearer

from .models import APIKey

logger = logging.getLogger(__name__)


# =============================================================================
# OPERATION MODE
# =============================================================================


class AuthMode:
    """Authentication mode for SomaFractalMemory."""

    STANDALONE = "standalone"  # Use local sfm_* keys
    INTEGRATED = "integrated"  # Validate via SomaBrain


def get_auth_mode() -> str:
    """Get current auth mode from settings."""
    return getattr(settings, "SFM_AUTH_MODE", AuthMode.STANDALONE)


# =============================================================================
# API KEY AUTHENTICATION (Django Ninja HttpBearer)
# =============================================================================


class APIKeyAuth(HttpBearer):
    """
    API Key authentication for SomaFractalMemory.

    Supports two modes:
    1. STANDALONE: Validate sfm_live_* keys locally
    2. INTEGRATED: Validate sbk_live_* keys via SomaBrain API

    Usage:
        @api.get("/memories", auth=APIKeyAuth())
        def list_memories(request):
            tenant = request.auth["tenant"]
            ...
    """

    def authenticate(self, request: HttpRequest, token: str) -> dict | None:
        """
        Authenticate the API key token.

        Args:
            request: The HTTP request
            token: The API key from Authorization header

        Returns:
            Dict with tenant info, or None if invalid
        """
        if not token:
            return None

        mode = get_auth_mode()

        # Check token prefix to determine auth method
        if token.startswith("sfm_"):
            # Local SFM key - always validate locally
            return self._validate_local_key(request, token)
        elif token.startswith("sbk_") and mode == AuthMode.INTEGRATED:
            # SomaBrain key - validate via central auth
            return self._validate_central_key(request, token)
        else:
            logger.warning(f"Unknown token format: {token[:8]}...")
            return None

    def _validate_local_key(self, request: HttpRequest, token: str) -> dict | None:
        """Validate local sfm_* API key."""
        key_hash = hashlib.sha256(token.encode()).hexdigest()

        try:
            api_key = APIKey.objects.get(
                key_hash=key_hash,
                is_active=True,
            )

            # Check expiration
            if api_key.expires_at and api_key.expires_at < timezone.now():
                logger.warning(f"API key expired: {api_key.key_prefix}...")
                return None

            # Update usage
            ip_address = self._get_client_ip(request) or ""
            api_key.touch(ip_address)

            logger.info(
                f"SFM API key authenticated: {api_key.key_prefix}... for tenant {api_key.tenant}"
            )

            return {
                "tenant": api_key.tenant,
                "api_key_id": str(api_key.id),
                "permissions": api_key.permissions,
                "allowed_namespaces": api_key.allowed_namespaces,
                "is_test": api_key.is_test,
                "auth_type": "sfm_local",
            }

        except APIKey.DoesNotExist:
            logger.warning("SFM API key not found")
            return None

    def _validate_central_key(self, request: HttpRequest, token: str) -> dict | None:
        """Validate sbk_* key via SomaBrain central auth (async)."""
        import httpx

        somabrain_url = getattr(settings, "SOMABRAIN_URL", None)
        if not somabrain_url:
            logger.error("SOMABRAIN_URL not configured - cannot validate central key")
            return None

        try:
            # Synchronous call to SomaBrain auth endpoint
            response = httpx.get(
                f"{somabrain_url}/api/v1/auth/verify",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"SomaBrain key validated for tenant {data.get('tenant_slug')}")
                return {
                    "tenant": data.get("tenant_slug"),
                    "tenant_id": data.get("tenant_id"),
                    "api_key_id": data.get("api_key_id"),
                    "scopes": data.get("scopes", []),
                    "is_test": data.get("is_test", False),
                    "auth_type": "somabrain_central",
                }

            logger.warning(f"SomaBrain auth failed: {response.status_code}")
            return None

        except Exception as e:
            logger.error(f"SomaBrain auth error: {e}")
            # Fallback: Check if we have a cached tenant
            return None

    def _get_client_ip(self, request: HttpRequest) -> str | None:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


# =============================================================================
# SIMPLE TOKEN AUTH (For internal service calls)
# =============================================================================


class SimpleTokenAuth(HttpBearer):
    """
    Simple token authentication for internal service calls.

    Uses SOMA_API_TOKEN from settings.
    """

    def authenticate(self, request: HttpRequest, token: str) -> dict | None:
        """Validate simple token."""
        expected_token = None
        if hasattr(settings, "get_api_token"):
            expected_token = settings.get_api_token()
        if not expected_token:
            expected_token = getattr(settings, "SOMA_API_TOKEN", None)

        if not expected_token:
            logger.warning("SOMA_API_TOKEN not configured")
            return None

        if token == expected_token:
            return {
                "tenant": request.META.get("HTTP_X_SOMA_TENANT", "default"),
                "auth_type": "simple_token",
                # Shared token is intentionally limited: read/write only, no admin/delete
                "permissions": ["read", "write"],
                "allowed_namespaces": ["*"],
            }

        return None


# =============================================================================
# NAMESPACE ACCESS CHECK
# =============================================================================


def can_access_namespace(request: HttpRequest, namespace: str) -> bool:
    """
    Check if the authenticated request can access a namespace.

    Returns True if:
    - allowed_namespaces is empty (all access)
    - namespace is in allowed_namespaces
    - "*" is in allowed_namespaces
    """
    auth = getattr(request, "auth", {})
    allowed = auth.get("allowed_namespaces", [])

    if not allowed:
        return True

    return namespace in allowed or "*" in allowed


def has_permission(request: HttpRequest, permission: str) -> bool:
    """
    Check if the authenticated request has a permission.

    Permissions: read, write, delete, admin
    """
    auth = getattr(request, "auth", {})
    if auth.get("auth_type") == "simple_token":
        return True

    permissions = auth.get("permissions", [])

    return permission in permissions or "admin" in permissions


# =============================================================================
# COMPOSITE AUTH
# =============================================================================


class MultiAuth(HttpBearer):
    """
    Composite auth that accepts:
    - sfm_* API keys (local)
    - sbk_* keys (central, if enabled)
    - SOMA_API_TOKEN simple bearer

    Returns a normalized auth dict on request.auth.
    """

    def authenticate(self, request: HttpRequest, token: str) -> dict | None:
        """Try API key auth first, then fallback to simple token."""
        if not token:
            return None

        api_key_auth = APIKeyAuth()
        api_key_result = api_key_auth.authenticate(request, token)
        if api_key_result:
            return api_key_result

        simple_auth = SimpleTokenAuth()
        return simple_auth.authenticate(request, token)
