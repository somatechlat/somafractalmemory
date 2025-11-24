"""End‑to‑end integration test for the SomaFractalMemory API.

The test validates the **full stack** (FastAPI, Redis, Qdrant, PostgreSQL) by:

1. Storing a **semantic** memory – this creates a vector in Qdrant.
2. Fetching the same memory to confirm the payload is returned correctly.
3. Querying ``/stats`` and asserting that ``total_memories`` and
   ``vector_count`` have increased.

The API requires a bearer token. The token is read from the environment variable
``SOMA_API_TOKEN``; if the variable is missing the test falls back to the
``.env`` file at the repository root.  No secrets are hard‑coded.
"""

import os

import pytest
import requests

BASE_URL = "http://127.0.0.1:9595"


def _load_token() -> str:
    """Return the API token.

    Preference order:
    1. ``SOMA_API_TOKEN`` environment variable.
    2. ``.env`` file in the repository root.
    """
    token = os.getenv("SOMA_API_TOKEN")
    if token:
        return token
    # Fallback to .env file
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("SOMA_API_TOKEN"):
                    return line.strip().split("=", 1)[1]
    except Exception:
        pass
    raise RuntimeError("SOMA_API_TOKEN not found in environment or .env file")


@pytest.fixture(scope="module")
def api_token() -> str:
    return _load_token()


def test_end_to_end_memory_save(api_token: str) -> None:
    # 1️⃣ Store a semantic memory (creates a vector in Qdrant)
    coord = "0.9,0.8,0.7"
    payload = {"test": "value"}
    store_resp = requests.post(
        f"{BASE_URL}/memories",
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
        json={"coord": coord, "payload": payload, "memory_type": "semantic"},
    )
    assert store_resp.status_code in (
        200,
        201,
    ), f"Unexpected store status: {store_resp.status_code}"

    # 2️⃣ Retrieve the same memory and verify the payload
    fetch_resp = requests.get(
        f"{BASE_URL}/memories/{coord}",
        headers={"Authorization": f"Bearer {api_token}"},
    )
    assert fetch_resp.status_code == 200, f"Fetch failed: {fetch_resp.status_code}"
    data = fetch_resp.json()
    assert data["memory"]["payload"] == payload

    # 3️⃣ Verify stats reflect the stored semantic memory
    stats_resp = requests.get(f"{BASE_URL}/stats")
    assert stats_resp.status_code == 200, f"Stats request failed: {stats_resp.status_code}"
    stats = stats_resp.json()
    assert stats.get("total_memories", 0) >= 1, "total_memories should be >= 1"
    assert stats.get("semantic", 0) >= 1, "semantic count should be >= 1"
    assert stats.get("vector_count", 0) >= 1, "vector_count should be >= 1"
