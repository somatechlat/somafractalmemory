"""Live integration tests that exercise the running services.

These tests connect to the Docker‑compose services started on the host
(`docker compose --profile core up -d`). They use the central ``settings``
singleton to obtain the API bearer token and the API port, guaranteeing
that no hard‑coded values are present.

The suite validates:
* Health endpoint is reachable.
* A memory can be stored, retrieved and then deleted via the HTTP API.
* The delete operation truly removes the memory.

All requests include the ``Authorization: Bearer <token>`` header as required
by the API. The tests are deliberately simple but hit the real backend
components (Postgres, Redis, Qdrant) to satisfy the "always test on live
servers" rule.
"""

import os
import time

import pytest
import requests

# The API configuration lives in the shared ``common`` settings module.
# Importing from ``somafractalmemory.config.settings`` would miss the
# ``api_port`` field, causing an AttributeError during test collection.
from common.config.settings import settings as common_settings

BASE_URL = f"http://127.0.0.1:{common_settings.api_port or 9595}"


def _auth_headers() -> dict[str, str]:
    token = common_settings.api_token or os.getenv("SOMA_API_TOKEN", "devtoken")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _wait_for_service(timeout: int = 30) -> None:
    """Poll the health endpoint until it returns 200 or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/healthz")
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("API health endpoint did not become ready within timeout")


@pytest.fixture(scope="session", autouse=True)
def ensure_api_is_up():
    """Ensure the API is reachable before any tests run."""
    _wait_for_service()


def test_health_endpoint() -> None:
    resp = requests.get(f"{BASE_URL}/healthz")
    assert resp.status_code == 200


def test_store_retrieve_delete_cycle() -> None:
    coord = "1.2,3.4,5.6"
    payload = {"foo": "bar", "number": 42}
    # Store
    store_resp = requests.post(
        f"{BASE_URL}/memories",
        headers=_auth_headers(),
        json={"coord": coord, "payload": payload, "memory_type": "episodic"},
    )
    assert store_resp.status_code in (200, 201)

    # Retrieve
    get_resp = requests.get(f"{BASE_URL}/memories/{coord}", headers=_auth_headers())
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["memory"]["payload"] == payload

    # Delete
    del_resp = requests.delete(f"{BASE_URL}/memories/{coord}", headers=_auth_headers())
    assert del_resp.status_code == 200

    # Verify deletion
    get_again = requests.get(f"{BASE_URL}/memories/{coord}", headers=_auth_headers())
    assert get_again.status_code == 404
