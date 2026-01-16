import sys
import time

import requests

# SFM E2E Memory Test Configuration
SFM_HOST = "localhost"
SFM_PORT = 10101
ENDPOINT = f"http://{SFM_HOST}:{SFM_PORT}/api/memories/"
TOKEN = "dev-token-somastack2024"

# Test Data (Resilient Fractal Coordinate)
TEST_COORD = [1.2, 3.4, 5.6]
TEST_PAYLOAD = {"origin": "e2e_resilience_test", "timestamp": time.time(), "vibe": "resilient"}
TEST_NAMESPACE = "resilience_audit"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "X-Soma-Tenant": "default",
}


def verify_sfm():
    print(f"--- SFM E2E VERIFICATION START | {time.ctime()} ---")

    # 1. Store Operation
    store_data = {
        "namespace": TEST_NAMESPACE,
        "coordinate": TEST_COORD,
        "payload": TEST_PAYLOAD,
        "memory_type": "episodic",
    }

    print(f"Stating memory at {TEST_COORD}...")
    try:
        r = requests.post(ENDPOINT, headers=headers, json=store_data, timeout=10)
        r.raise_for_status()
        print(f"STORE SUCCESS: {r.status_code}")
    except Exception as e:
        print(f"STORE FAILED: {e}")
        sys.exit(1)

    # 2. Retrieve Operation
    coord_str = ",".join(map(str, TEST_COORD))
    retrieve_url = f"{ENDPOINT}{TEST_NAMESPACE}/{coord_str}"

    print(f"Retrieving memory from {coord_str}...")
    try:
        r = requests.get(retrieve_url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()

        # Verify Integrity
        if data["payload"]["origin"] == "e2e_resilience_test":
            print(f"RETRIEVE SUCCESS: Match Confirmed via {TEST_NAMESPACE}")
            print("--- SFM E2E VERIFICATION COMPLETE | STATUS: SOVEREIGN ---")
            return True
        else:
            print("INTEGRITY ERROR: Data Mismatch")
            sys.exit(1)
    except Exception as e:
        print(f"RETRIEVE FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    verify_sfm()
