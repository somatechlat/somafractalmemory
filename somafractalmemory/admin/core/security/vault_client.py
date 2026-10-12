"""Vault Client for SomaFractalMemory.

ALL secrets fetched from HashiCorp Vault. NO secrets in ENV or DB.

The Vault *token* is a credential and is delivered as a file only
(``VAULT_TOKEN_FILE``). The file path is topology and may live in the
environment; the token value never does (VIBE Rule 164). Exporting a token
into a shell leaves it in ``ps``, ``/proc/*/environ`` and every crash dump.
"""

import logging
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

# The token is a FILE, never an environment variable (VIBE Rule 164).
# There is deliberately no ``VAULT_TOKEN`` / ``SOMA_VAULT_TOKEN`` read anywhere
# in this module.
DEFAULT_TOKEN_FILE_ENV = "VAULT_TOKEN_FILE"


class VaultNotConfigured(ImproperlyConfigured):
    """Vault is not part of this deployment (missing address or token file)."""


class VaultAuthError(ImproperlyConfigured):
    """Vault could not be authenticated to or reached.

    This is an infrastructure failure, NOT a missing secret. It must never be
    reported as ``None``: a caller that cannot reach Vault has no idea whether
    the secret exists, and returning ``None`` turns "I cannot tell" into "it is
    absent" — which then looks like a legitimately optional secret.
    """


class SecretNotFound(ImproperlyConfigured):
    """Secret not found in Vault."""


def _vault_addr() -> str | None:
    """Return the Vault API address (topology, not a credential).

    Django settings (``SOMA_VAULT_URL``) is the deployment authority once
    settings are configured. Before that — during the settings bootstrap that
    imports this module — the environment names (``SOMA_VAULT_ADDR`` /
    ``VAULT_ADDR``) are the only channel available. Those names are read here
    and nowhere else in application code.
    """
    from django.conf import settings

    if settings.configured:
        value = getattr(settings, "SOMA_VAULT_URL", None)
        if value:
            return str(value)
    return os.environ.get("SOMA_VAULT_ADDR") or os.environ.get("VAULT_ADDR")


def vault_topology_present() -> bool:
    """True when this deployment claims a Vault (address or token-file path).

    Presence of either side of the topology means Vault is the secret source
    and must be treated as mandatory. Neither present means the deployment
    uses the injection channel documented in ``settings.django_core``.
    """
    return bool(_vault_addr()) or bool(os.environ.get(DEFAULT_TOKEN_FILE_ENV))


def _resolve_vault_token() -> str:
    """Return the Vault token from ``VAULT_TOKEN_FILE``. Never from ENV values.

    Resolution: the path named by ``VAULT_TOKEN_FILE`` is read as UTF-8 text
    and stripped. A missing path, an unreadable file or an empty file is fatal.

    Raises:
        VaultNotConfigured: path unset, file unreadable, or file empty.
    """
    path = os.environ.get(DEFAULT_TOKEN_FILE_ENV)
    if not path:
        raise VaultNotConfigured(
            "VIBE Rule 164 VIOLATION: VAULT_TOKEN_FILE is not set. Point it at "
            "a file containing the Vault token. The token is never taken from "
            "the environment and there is no fallback."
        )
    try:
        resolved = Path(path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise VaultNotConfigured(
            f"VIBE Rule 164 VIOLATION: cannot read the Vault token file at "
            f"{path!r}: {exc.strerror or exc}. Fix the path or the file's "
            f"permissions (0600); the token is never read from the environment."
        ) from None
    if not resolved:
        raise VaultNotConfigured(
            f"VIBE Rule 164 VIOLATION: the Vault token file at {path!r} is "
            f"empty. An empty token is not a valid credential and must not be "
            f"treated as 'no secrets'."
        )
    return resolved


@lru_cache(maxsize=1)
def _get_vault_client():
    """Get Vault client singleton. Token comes from file only.

    Uses stdlib urllib against the KV v2 HTTP API — no hvac version traps,
    no SDK default drift. Same path the agent templates use.
    """
    vault_addr = _vault_addr()
    if not vault_addr:
        raise VaultNotConfigured(
            "Vault not configured. Set SOMA_VAULT_ADDR or VAULT_ADDR "
            "(topology). The token comes from VAULT_TOKEN_FILE."
        )
    vault_token = _resolve_vault_token()

    import json
    import urllib.error
    import urllib.request

    class _VaultKV2:
        def __init__(self, addr: str, token: str) -> None:
            self._base = addr.rstrip("/") + "/v1/"
            self._token = token

        def read(self, mount: str, path: str) -> dict[str, Any]:
            url = f"{self._base}{mount}/data/{path}"
            req = urllib.request.Request(url, method="GET")
            req.add_header("X-Vault-Token", self._token)
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    payload = json.loads(resp.read() or b"{}")
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    raise SecretNotFound(f"path {mount}/{path} not in Vault") from exc
                raise VaultAuthError(f"Vault read {mount}/{path} -> HTTP {exc.code}") from exc
            except Exception as exc:
                raise VaultAuthError(f"Vault read {mount}/{path} failed: {exc}") from exc
            data = (payload.get("data") or {}).get("data") or {}
            return data

        def is_authenticated(self) -> bool:
            req = urllib.request.Request(self._base + "auth/token/lookup-self", method="GET")
            req.add_header("X-Vault-Token", self._token)
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return resp.status == 200
            except Exception:
                return False

    client = _VaultKV2(vault_addr, vault_token)
    if not client.is_authenticated():
        raise VaultAuthError("Vault authentication failed.")
    logger.info(f"Vault client connected to {vault_addr}")
    return client


# Result cache for secrets: (path, key) -> (data, expiry)
_secret_cache: dict[tuple[str, str | None], tuple[Any, float]] = {}
CACHE_TTL = 300  # 5 minutes


def get_secret(path: str, key: str | None = None) -> Any:
    """Get secret from Vault with 5-minute TTL caching to prevent DDOSing Vault.

    Returns the secret value. Never ``None`` for a failed lookup: inability to
    reach or authenticate to Vault raises ``VaultAuthError``; a key Vault
    answered for and did not have raises ``SecretNotFound``.
    """
    now = time.time()
    cache_key = (path, key)

    # Check cache
    if cache_key in _secret_cache:
        data, expiry = _secret_cache[cache_key]
        if now < expiry:
            return data

    client = _get_vault_client()

    try:
        # Split path to extract mount point if present (e.g., 'somafractalmemory/database')
        parts = path.split("/")
        if len(parts) > 1:
            mount_point = parts[0]
            secret_path = "/".join(parts[1:])
        else:
            mount_point = "secret"
            secret_path = path

        data = client.read(mount_point, secret_path)

        result = data
        if key:
            if key not in data:
                raise SecretNotFound(f"Key '{key}' not found at path '{path}'")
            result = data[key]

        # Update cache
        _secret_cache[cache_key] = (result, now + CACHE_TTL)
        return result

    except (SecretNotFound, VaultAuthError, VaultNotConfigured):
        raise
    except Exception as e:
        raise VaultAuthError(f"Vault lookup failed for '{path}': {e}") from e


def get_db_credentials() -> dict:
    """Get database credentials from Vault."""
    return get_secret("somafractalmemory/database")


def get_redis_credentials() -> dict:
    """Get redis credentials from Vault."""
    return get_secret("somafractalmemory/redis")
