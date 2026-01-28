"""Vault Client for runtime secret fetching.

Implements secure secret retrieval from HashiCorp Vault to avoid
storing sensitive credentials in environment variables.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

try:
    import hvac
except ImportError:
    hvac = None  # Handle missing dependency gracefully for tests


class VaultSecretManager:
    """Manages secret retrieval from HashiCorp Vault."""

    def __init__(self) -> None:
        self.url = os.environ.get("SOMA_VAULT_URL")
        self.secrets_path = os.environ.get("SOMA_SECRETS_PATH")
        self.role = os.environ.get("SOMA_VAULT_ROLE")
        self.mount_point = os.environ.get("SOMA_VAULT_K8S_MOUNT", "kubernetes")
        self.token = os.environ.get("VAULT_TOKEN")
        self.client: hvac.Client | None = None

    def get_secrets(self) -> dict[str, Any]:
        """Fetch secrets from Vault if configured, otherwise return empty dict."""
        if not self.url or not hvac:
            if self.url and not hvac:
                logger.warning("SOMA_VAULT_URL set but hvac library not installed.")
            return {}

        try:
            self.client = hvac.Client(url=self.url)

            # Authenticate
            if self.token:
                self.client.token = self.token
            elif self.role:
                # Kubernetes Auth
                f = open("/var/run/secrets/kubernetes.io/serviceaccount/token")
                jwt = f.read()
                f.close()
                self.client.auth.kubernetes.login(
                    role=self.role,
                    jwt=jwt,
                    mount_point=self.mount_point,
                )

            if not self.client.is_authenticated():
                logger.error("Vault authentication failed.")
                return {}

            # Read Secrets
            if not self.secrets_path:
                logger.warning("Vault authenticated but SOMA_SECRETS_PATH not set.")
                return {}

            # Assuming KV v2
            read_response = self.client.secrets.kv.v2.read_secret_version(path=self.secrets_path)
            return read_response["data"]["data"]

        except Exception as e:
            logger.error(f"Fatal: Failed to fetch secrets from Vault: {e}")
            raise RuntimeError(f"Vault secret fetch failed: {e}") from e


def get_vault_secrets() -> dict[str, Any]:
    """Helper to fetch secrets."""
    return VaultSecretManager().get_secrets()
