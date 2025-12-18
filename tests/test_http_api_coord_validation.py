import os

import pytest

# Set environment variables for localhost infrastructure BEFORE importing http_api
# This is required because http_api.py creates the memory system at import time
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "40022")
os.environ.setdefault("POSTGRES_URL", "postgresql://soma:soma@localhost:40021/somamemory")
os.environ.setdefault("SOMA_MILVUS_HOST", "localhost")
os.environ.setdefault("SOMA_MILVUS_PORT", "35003")
os.environ.setdefault("SOMA_API_TOKEN", "test-token")

try:
    from fastapi.testclient import TestClient

    from somafractalmemory.http_api import app

    client = TestClient(app)
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
    # Use the token from environment (set by conftest.py) or fallback to test-token
    import os

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
    assert "Invalid coord" in data.get("detail", "")
