"""Vault Client for SomaFractalMemory.

ALL secrets fetched from HashiCorp Vault. NO secrets in ENV or DB.
"""

import logging
import os
from functools import lru_cache
from typing import Any

from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class VaultNotConfigured(ImproperlyConfigured):
    """Vault not configured - secrets cannot be fetched."""

    pass


class SecretNotFound(ImproperlyConfigured):
    """Secret not found in Vault."""

    pass


@lru_cache(maxsize=1)
def _get_vault_client():
    """Get Vault client singleton."""
    vault_addr = os.environ.get("SOMA_VAULT_ADDR") or os.environ.get("VAULT_ADDR")
    vault_token = os.environ.get("SOMA_VAULT_TOKEN") or os.environ.get("VAULT_TOKEN")

    if not vault_addr or not vault_token:
        raise VaultNotConfigured("Vault not configured. Set SOMA_VAULT_ADDR and SOMA_VAULT_TOKEN.")

    try:
        import hvac

        client = hvac.Client(url=vault_addr, token=vault_token)
        if not client.is_authenticated():
            raise VaultNotConfigured("Vault authentication failed.")
        logger.info(f"Vault client connected to {vault_addr}")
        return client
    except ImportError:
        raise VaultNotConfigured("hvac library not installed.")
    except Exception as e:
        raise VaultNotConfigured(f"Vault connection failed: {e}")


def get_secret(path: str, key: str | None = None) -> Any:
    """Get secret from Vault."""
    client = _get_vault_client()
    if client is None:
        return None

    try:
        # Split path to extract mount point if present (e.g., 'somafractalmemory/database')
        parts = path.split("/")
        if len(parts) > 1:
            mount_point = parts[0]
            secret_path = "/".join(parts[1:])
        else:
            mount_point = "secret"
            secret_path = path

        secret = client.secrets.kv.v2.read_secret_version(mount_point=mount_point, path=secret_path)
        data = secret["data"]["data"]

        if key:
            if key not in data:
                raise SecretNotFound(f"Key '{key}' not found at path '{path}'")
            return data[key]
        return data

    except Exception as e:
        if "SecretNotFound" in str(type(e)):
            raise
        raise SecretNotFound(f"Secret at '{path}' not found: {e}")


def get_db_credentials() -> dict:
    """Get database credentials from Vault."""
    return get_secret("somafractalmemory/database")


def get_redis_credentials() -> dict:
    """Get redis credentials from Vault."""
    return get_secret("somafractalmemory/redis")
