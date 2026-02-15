import os

from somafractalmemory.admin.core.security.vault_client import _get_vault_client, get_secret

print("--- Vault Debug ---")
print(f"VAULT_ADDR: {os.environ.get('VAULT_ADDR')}")
print(f"VAULT_TOKEN set: {bool(os.environ.get('VAULT_TOKEN'))}")

try:
    print("Attempting to get client...")
    client = _get_vault_client()
    print(f"Client authenticated: {client.is_authenticated()}")

    print("Attempting to read path: somafractalmemory/database")
    secret = get_secret("somafractalmemory/database")
    print(f"Secret found: {secret is not None}")
    if secret:
        print(f"Username in secret: {secret.get('username')}")
    else:
        print("SECRET IS NONE")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()

print("--- End Debug ---")
