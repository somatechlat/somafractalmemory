"""Module diagnose_sfm."""

import os
import sys
import traceback

import django

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somafractalmemory.settings")
django.setup()


from somafractalmemory.api.core import get_mem  # noqa: E402


def diagnose():
    """Execute diagnose."""

    print("--- DIAGNOSING SOMAFRACTALMEMORY ---")
    try:
        service = get_mem()
        print("Service initialized.")

        print("Attempting to store memory...")
        coord = (1.0, 2.0, 3.0)
        payload = {"text": "Diagnosis Payload"}
        tenant = "default"

        service.store(coordinate=coord, payload=payload, memory_type="episodic", tenant=tenant)
        print("✅ Store successful!")

        print("Attempting to retrieve memory...")
        result = service.retrieve(coord, tenant=tenant)
        print(f"✅ Retrieve successful: {result}")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    diagnose()
