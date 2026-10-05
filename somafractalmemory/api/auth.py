"""Standalone Authentication Facade for SomaFractalMemory.

This module provides authentication for STANDALONE mode only.
AAAS (Agent-as-a-Service) auth is a separate deployment concern
and is NOT loaded in standalone mode.

Auth strategy:
  - Bearer token compared against ``settings.SOMA_API_TOKEN`` (the value the
    settings modules resolve at boot — Vault is the system of record)
  - No API key management, no SomaBrain integration
  - Tenant derived from auth context or X-Soma-Tenant header
"""

import hmac
import logging

from django.conf import settings
from django.http import HttpRequest
from ninja.security import HttpBearer

logger = logging.getLogger(__name__)


class StandaloneAuth(HttpBearer):
    """Standalone bearer token authentication.

    Validates requests against ``settings.SOMA_API_TOKEN`` — the single
    resolved credential. All authenticated requests are bound to the
    'standalone' tenant.

    Security:
        - Uses hmac.compare_digest for constant-time token comparison
        - Prevents timing attacks on token validation
        - An absent expected token fail-closes every caller
    """

    def authenticate(self, request: HttpRequest, token: str) -> dict | None:
        """Validate the bearer token against the resolved API token.

        Args:
            request: The HTTP request
            token: The bearer token from Authorization header

        Returns:
            Auth context dict if valid, None if invalid
        """
        if not token:
            return None

        expected_token = _get_expected_token()
        if not expected_token:
            logger.warning("SOMA_API_TOKEN not configured — rejecting all callers (fail-closed)")
            return None

        if hmac.compare_digest(token.encode("utf-8"), expected_token.encode("utf-8")):
            return {
                "tenant": "standalone",
                "auth_type": "standalone_token",
                "permissions": ["read", "write", "delete"],
                "allowed_namespaces": ["*"],
            }

        return None


def _get_expected_token() -> str | None:
    """Return the expected API token from Django settings.

    One source of truth (R-VAL-03): the settings modules already resolve the
    credential (Vault first, deployment injection second, never a code
    default). This reader adds no second lookup path and no fallback.
    """
    return getattr(settings, "SOMA_API_TOKEN", None)


def can_access_namespace(request: HttpRequest, namespace: str) -> bool:
    """Check if the authenticated request can access a namespace.

    Fail-closed (R-05 / F-07, T-5): an empty allow-list grants nothing.
    Standalone auth always sets ``["*"]``, so the happy path is unaffected.

    Args:
        request: The HTTP request with auth context
        namespace: The target namespace

    Returns:
        True if access is permitted
    """
    auth = getattr(request, "auth", {})
    allowed = auth.get("allowed_namespaces", [])

    if not allowed:
        return False

    return namespace in allowed or "*" in allowed


def has_permission(request: HttpRequest, permission: str) -> bool:
    """Check if the authenticated request has a specific permission.

    Args:
        request: The HTTP request with auth context
        permission: Required permission (read, write, delete)

    Returns:
        True if permission is granted
    """
    auth = getattr(request, "auth", {})
    permissions = auth.get("permissions", [])
    return permission in permissions
