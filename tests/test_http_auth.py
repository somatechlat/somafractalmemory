import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def http_api_app(monkeypatch):
    """Reload FastAPI app with test memory mode and a known token."""

    monkeypatch.setenv("SOMA_API_TOKEN", "unit-test-token")
    monkeypatch.setenv("MEMORY_MODE", "evented_enterprise")
    # Ensure a clean import so startup code re-runs with the patched env.
    sys.modules.pop("somafractalmemory.http_api", None)
    module = importlib.import_module("somafractalmemory.http_api")
    yield module.app
    # Clean up module cache after test to avoid side effects.
    sys.modules.pop("somafractalmemory.http_api", None)


def test_store_requires_valid_bearer(http_api_app):
    client = TestClient(http_api_app)
    payload = {
        "coord": "0,0,0",
        "payload": {"task": "auth-check"},
        "type": "episodic",
    }

    # Missing header → 401
    resp = client.post("/store", json=payload)
    assert resp.status_code == 401

    # Wrong token → 403
    resp = client.post("/store", json=payload, headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 403

    # Correct token succeeds
    resp = client.post("/store", json=payload, headers={"Authorization": "Bearer unit-test-token"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
