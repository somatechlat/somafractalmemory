"""Test coordinate validation - Django Ninja.

Tests for malformed coordinate handling.
100% Django patterns - NO FastAPI.
"""

import os

import pytest

# Set environment variables for localhost infrastructure BEFORE importing API
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somafractalmemory.settings")
os.environ.setdefault("SOMA_API_TOKEN", "test-token")
# Required Django settings for import-time validation
os.environ.setdefault("SOMA_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SOMA_ALLOWED_HOSTS", "*")

try:
    from ninja.testing import TestClient

    from somafractalmemory.api import api

    client = TestClient(api)
    SKIP_REASON = None
except ImportError as e:
    client = None
    SKIP_REASON = f"Missing dependency: {e}"
except RuntimeError as e:
    # Infrastructure not available (Redis/Postgres/Milvus not running)
    client = None
    SKIP_REASON = f"Infrastructure not available: {e}"

pytestmark = pytest.mark.skipif(
    SKIP_REASON is not None,
    reason=SKIP_REASON or "Missing dependencies",
)


def test_malformed_coord_returns_400():
    """Test that malformed coordinates return 400 Bad Request."""
    token = os.environ.get("SOMA_API_TOKEN", "test-token")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "coord": "target-learnbench-3c6c5e16-282e3f50",
        "memory_type": "episodic",
        "payload": {"foo": "bar"},
    }
    r = client.post("/memories", headers=headers, json=payload)
    assert r.status_code == 400
    data = r.json()
    assert (
        "Invalid coord" in data.get("detail", "") or "coordinate" in data.get("detail", "").lower()
    )
