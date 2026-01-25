import json
import os
import sys
import time

import requests

# Configuration
BASE_URL = "http://localhost:10101"
# Use the token we know works (from previous steps)
TOKEN = os.environ.get("SOMA_API_TOKEN", "dev-token-somastack2024")

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def log(msg, color="\033[0m"):
    print(f"{color}{msg}\033[0m")


def print_json(data):
    print(json.dumps(data, indent=2))


def main():
    log("=== SOMA FRACTAL MEMORY LIVE API VERIFICATION ===", "\033[1;36m")
    log(f"Target: {BASE_URL}")
    log(f"Token: {TOKEN[:5]}***")

    # 1. Health Check
    log("\n[1] Checking Health...", "\033[1;33m")
    try:
        resp = requests.get(f"{BASE_URL}/healthz")
        if resp.status_code == 200:
            log("✅ Health Check Passed", "\033[1;32m")
            print_json(resp.json())
        else:
            log(f"❌ Health Check Failed: {resp.status_code}", "\033[1;31m")
            print(resp.text)
            sys.exit(1)
    except Exception as e:
        log(f"❌ Connection Failed: {e}", "\033[1;31m")
        sys.exit(1)

    # 2. Store Memory
    coord = "0.99,0.99,0.99"
    payload = {"content": "E2E Verification Test", "timestamp": time.time(), "verified": True}

    log(f"\n[2] Storing Memory at {coord}...", "\033[1;33m")
    resp = requests.post(
        f"{BASE_URL}/memories",
        headers=HEADERS,
        json={"coord": coord, "payload": payload, "memory_type": "episodic"},
    )

    if resp.status_code in (200, 201):
        log("✅ Store Successful", "\033[1;32m")
        print_json(resp.json())
    else:
        log(f"❌ Store Failed: {resp.status_code}", "\033[1;31m")
        print(resp.text)
        sys.exit(1)

    # 3. Retrieve Memory
    log(f"\n[3] Retrieving Memory from {coord}...", "\033[1;33m")
    resp = requests.get(f"{BASE_URL}/memories/{coord}", headers=HEADERS)

    if resp.status_code == 200:
        data = resp.json()
        stored_payload = data.get("memory", {}).get("payload")
        if stored_payload.get("content") == payload["content"]:
            log("✅ Retrieval Successful & Content Verified", "\033[1;32m")
            print_json(data)
        else:
            log("❌ Retrieval Content Mismatch", "\033[1;31m")
            print_json(data)
    else:
        log(f"❌ Retrieval Failed: {resp.status_code}", "\033[1;31m")
        print(resp.text)

    # 4. Cleanup (Delete)
    log(f"\n[4] Deleting Memory at {coord}...", "\033[1;33m")
    resp = requests.delete(f"{BASE_URL}/memories/{coord}", headers=HEADERS)

    if resp.status_code == 200:
        log("✅ Delete Successful", "\033[1;32m")
        print_json(resp.json())
    else:
        log(f"❌ Delete Failed: {resp.status_code}", "\033[1;31m")
        print(resp.text)

    # 5. Verify Deletion
    log("\n[5] Verifying Deletion...", "\033[1;33m")
    resp = requests.get(f"{BASE_URL}/memories/{coord}", headers=HEADERS)
    if resp.status_code == 404:
        log("✅ Verification Successful (404 Not Found)", "\033[1;32m")
    else:
        log(f"❌ Verification Failed: Expected 404, got {resp.status_code}", "\033[1;31m")

    log("\n=== E2E VERIFICATION COMPLETE ===", "\033[1;36m")


if __name__ == "__main__":
    main()
