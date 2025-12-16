import pytest

try:
    from fastapi.testclient import TestClient

    from somafractalmemory.http_api import app

    client = TestClient(app)
    SKIP_REASON = None
except ImportError as e:
    client = None
    SKIP_REASON = f"Missing dependency: {e}"

pytestmark = pytest.mark.skipif(
    SKIP_REASON is not None,
    reason=SKIP_REASON or "Missing dependencies",
)


def test_malformed_coord_returns_400():
    # Use the pinned dev token by default to match local compose configuration
    from somafractalmemory.config.settings import settings

    token = settings.api_token or "devtoken"
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
