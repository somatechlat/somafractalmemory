# tests/test_bulk_1000.py
"""Load 1000 memories via the FastAPI API and verify they are stored.

The test uses the example FastAPI app (examples/api.py) which runs in
DEVELOPMENT mode. We point the app at the real Redis, Postgres and Qdrant
services that are started by `docker compose up`.
"""

import os

import requests

# Ensure the real services URLs are set (Docker‑Compose exposes ports on localhost)
os.environ.setdefault("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5433/somamemory")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("QDRANT_HOST", "localhost")
os.environ.setdefault("QDRANT_PORT", "6333")

BASE_URL = "http://localhost:9595"


def test_store_and_count_1000_memories():
    # Build 1000 memory items
    items = []
    for i in range(1000):
        items.append(
            {
                "coord": f"{i},{i},{i}",
                "payload": {"val": i},
                "type": "episodic",
            }
        )

    # Bulk‑store via the real API
    resp = requests.post(f"{BASE_URL}/store_bulk", json={"items": items})
    assert resp.status_code == 200, f"Unexpected status {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("stored") == 1000, "API reported wrong stored count"

    # Verify total count via /stats endpoint
    stats_resp = requests.get(f"{BASE_URL}/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats.get("total_memories", 0) >= 1000
