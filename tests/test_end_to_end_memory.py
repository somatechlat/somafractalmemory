"""End‑to‑end integration test for the SomaFractalMemory API.

VIBE RULES: Test against REAL infrastructure only. NO MOCKS.

The test validates the **full stack** (Django, Redis, Milvus, PostgreSQL) by:

1. Storing a memory via the API.
2. Fetching the same memory to confirm the payload is returned correctly.
3. Querying health endpoint to verify all stores are connected.

Requires: SFM cluster running on port 10101 (via Tilt/Minikube)
"""

import os

import pytest
import requests

# VIBE: Read from environment, no hardcoded secrets
BASE_URL = os.environ.get("SFM_API_URL", "http://localhost:10101")
API_TOKEN = os.environ.get("SOMA_API_TOKEN")


@pytest.fixture(scope="module")
def api_token() -> str:
    """Return the API token from environment."""
    if not API_TOKEN:
        pytest.skip("SOMA_API_TOKEN not set; set it to match the running SFM API")
    return API_TOKEN


def test_end_to_end_memory_save(api_token: str) -> None:
    # 1) Store a semantic memory (Milvus-backed vector insert when Milvus is configured)
    """Execute test end to end memory save.

    Args:
        api_token: The api_token.
    """

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
    # Keep tests quiet; assertions above are the signal.
