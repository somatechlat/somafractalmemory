"""Production-grade OPA client.

Features:
- LRU Caching for high-throughput (millions of transactions).
- Fail-Closed default for security.
- Configurable timeout and resilience settings.
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any

import requests

logger = logging.getLogger(__name__)


class OPAClient:
    """High-performance OPA client with caching and strict security defaults."""

    def __init__(
        self,
        *,
        opa_url: str,
        policy_path: str,
        timeout: float = 1.0,
        fail_open: bool | None = None,
        cache_size: int = 10000,
    ) -> None:
        """Initialize the OPA client.

        Args:
            opa_url: Base URL of OPA server.
            policy_path: Path to policy (e.g. "soma/authz/allow").
            timeout: Network timeout in seconds.
            fail_open: If True, allow access on network error. Default: False (Fail Closed).
            cache_size: Number of unique inputs to cache.
        """
        base = opa_url.rstrip("/")
        policy = policy_path.strip("/")
        self._url = f"{base}/v1/data/{policy}"
        self._timeout = timeout

        # Configuration: Prefer explicit arg, fall back to env, default False (Fail Closed)
        if fail_open is not None:
            self._fail_open = fail_open
        else:
            self._fail_open = os.environ.get("SOMA_OPA_FAIL_OPEN", "false").lower() == "true"

        # Initialize cached checker
        # We use a separate method for caching to keep 'check' signature clean
        self._check_cached = lru_cache(maxsize=cache_size)(self._internal_check)

    def check(self, input_data: dict[str, Any]) -> bool:
        """Evaluate policy.

        Args:
            input_data: Dict of input parameters for the policy.

        Returns:
            bool: True if allowed, False if denied.
        """
        try:
            # Serialize for hashing (LRU cache requirement)
            # sort_keys=True ensures canonical representation
            input_json = json.dumps(input_data, sort_keys=True)
            return self._check_cached(input_json)
        except Exception as e:
            logger.error(f"OPA check validation failed: {e}")
            return self._fail_open

    def _internal_check(self, input_json: str) -> bool:
        """Internal method performing the actual request (cached)."""
        try:
            # Deserialize just for the log context if needed, but we send as JSON payload
            # Actually OPA expects {"input": ...}
            # We can re-use the string if we construct the body carefully, but simple dict is safer for requests
            payload = {"input": json.loads(input_json)}

            resp = requests.post(self._url, json=payload, timeout=self._timeout)

            if resp.status_code != 200:
                logger.warning(f"OPA returned status {resp.status_code}")
                return self._fail_open

            data = resp.json()
            result = data.get("result")

            # Handle boolean result
            if isinstance(result, bool):
                return result

            # Handle object result {"allow": bool}
            if isinstance(result, dict):
                allow = result.get("allow")
                if isinstance(allow, bool):
                    return allow

            logger.warning(f"OPA returned unexpected shape: {result}")
            return self._fail_open

        except Exception as e:
            logger.error(f"OPA connection failed: {e}")
            return self._fail_open
