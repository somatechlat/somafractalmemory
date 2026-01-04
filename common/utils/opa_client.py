"""Minimal OPA client used by the HTTP API.

This implementation is intentionally resilient for development:
- If OPA is unreachable or returns an unexpected payload, it defaults to allow (True).
- In production, point OPA_URL to a reachable OPA server and author a policy
  whose decision document resolves to a boolean (or an object with an `allow` bool).
"""

from __future__ import annotations

from typing import Any

import requests


class OPAClient:
    """Opaclient class implementation."""

    def __init__(self, *, opa_url: str, policy_path: str) -> None:
        # Normalise URL and policy path to an evaluation endpoint like:
        #   http://opa:8181/v1/data/soma/authz/allow
        """Initialize the instance."""

        base = opa_url.rstrip("/")
        policy = policy_path.strip("/")
        self._url = f"{base}/v1/data/{policy}"

    def check(self, input_data: dict[str, Any]) -> bool:
        """Evaluate the policy with the given input.

        Returns True when allowed. For development safety, any network or parsing
        error defaults to True to avoid blocking local workflows when OPA is absent.
        """
        try:
            resp = requests.post(self._url, json={"input": input_data}, timeout=1.0)
            if resp.status_code != 200:
                return True  # default allow on non-200 in dev
            data = resp.json()
            result = data.get("result")
            if isinstance(result, bool):
                return result
            if isinstance(result, dict):
                allow = result.get("allow")
                if isinstance(allow, bool):
                    return allow
            # Unexpected shape: default allow in dev
            return True
        except Exception:
            # Network error, JSON error, etc. Default allow for dev.
            return True
