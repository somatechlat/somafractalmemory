import os

from fastapi.testclient import TestClient

from somafractalmemory.http_api import app

client = TestClient(app)


def test_malformed_coord_returns_400():
    token = os.getenv("SOMA_API_TOKEN", "dev-89661821bba49bb033a26c0b")
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
