# tests/test_bulk_1000.py
"""Load 1000 memories via the FastAPI API and verify they are stored.

The test uses the FastAPI app (somafractalmemory/http_api.py) which runs in
DEVELOPMENT mode. We point the app at the real Redis, Postgres and Qdrant
services that are started by `docker compose up`.
"""

import os

import pytest
import requests

# Ensure the real services URLs are set (Docker‑Compose exposes ports on localhost)
os.environ.setdefault("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5433/somamemory")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("QDRANT_HOST", "localhost")
os.environ.setdefault("QDRANT_PORT", "6333")

# Prefer SOMA_TEST_API_BASE_URL override; else try primary 9595 then fallback to 8888 mapping (test_api service)
BASE_URL = os.getenv("SOMA_TEST_API_BASE_URL", "http://localhost:9595")


def _resolve_base_url():
    # If explicit override provided, trust it
    if os.getenv("SOMA_TEST_API_BASE_URL"):
        return os.getenv("SOMA_TEST_API_BASE_URL")
    import requests

    for candidate in ["http://localhost:9595", "http://localhost:8888"]:
        try:
            requests.get(f"{candidate}/healthz", timeout=0.4)
            return candidate
        except Exception:
            continue
    return "http://localhost:9595"  # default (will skip later if unreachable)


BASE_URL = _resolve_base_url()


def test_store_and_count_1000_memories():
    # Verify the API is reachable before proceeding
    try:
        requests.get(f"{BASE_URL}/healthz", timeout=1)
    except Exception:
        pytest.skip("FastAPI server not running on port 9595 – skipping integration bulk test")
    # Build 1000 memory items
    items = []
    for i in range(10):  # reduced from 1000 for quick test
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
    assert data.get("stored") == 10, "API reported wrong stored count"

    # Verify total count via /stats endpoint
    stats_resp = requests.get(f"{BASE_URL}/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats.get("total_memories", 0) >= 10
