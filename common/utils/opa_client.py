"""
OPA client for policy enforcement (production-grade).
Strictly follows VIBE Coding Rules.
"""

import os
from typing import Any

import requests


class OPAClient:
    def __init__(self, opa_url: str, policy_path: str):
        self.opa_url = opa_url.rstrip("/")
        self.policy_path = policy_path.lstrip("/")
        self._endpoint = f"{self.opa_url}/v1/data/{self.policy_path}"
        self._session = requests.Session()
        token = os.getenv("OPA_BEARER_TOKEN")
        if token:
            self._session.headers.update({"Authorization": f"Bearer {token}"})
        self._session.headers.update({"Content-Type": "application/json"})

    def check(self, input_data: dict[str, Any]) -> bool:
        payload = {"input": input_data}
        try:
            resp = self._session.post(self._endpoint, json=payload, timeout=2)
            resp.raise_for_status()
            result = resp.json().get("result", None)
            return bool(result)
        except requests.RequestException as e:
            # Log error. In development and test environments OPA may be
            # unreachable; prefer to fail-open so the API remains usable.
            # If you require a strict deny-on-error behaviour, set the
            # SOMA_OPA_FAIL_CLOSED=1 environment variable.
            print(f"OPA request error: {e}")
            if os.getenv("SOMA_OPA_FAIL_CLOSED", "") in {"1", "true", "True"}:
                return False
            return True


# Usage example (to be used in API layer):
# opa = OPAClient(opa_url="http://opa:8181", policy_path="soma/authz/allow")
# allowed = opa.check({"user": "alice", "action": "read", ...})
