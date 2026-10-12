#!/usr/bin/env python3
"""SomaFractalMemory standalone Vault seeder — VIBE Rule 164 / Rule 91.

**NO SECRETS EVER TOUCH THE FILESYSTEM** (except the RAM tmpfs first-boot handoff).

Every credential is generated in process memory (``secrets.token_urlsafe``) and
written directly into Vault. There is no ``SECRETS_DIR``, no plaintext file,
and no local copy after this process exits. Vault is the only system of record.

    somafractalmemory/database   DB credentials (password generated here)
    somafractalmemory/redis      Redis credentials (password generated here)
    somafractalmemory/credentials  API token (generated here)

First-boot handoff: the postgres password is also written to a **RAM tmpfs**
(T0_DIR, typically /run/t0) because the postgres image requires a password file
at container start. The handoff is RAM-only and the system of record remains
Vault.

Properties:

* **Never prints a secret value.** Not on success, not on failure, not in a
  request body, not in an exception. Errors name keys and HTTP status only.
* **Never writes a secret to disk.** The only write outside Vault is the RAM
  tmpfs handoff (R-SEC-01 permits tmpfs as the last-resort first-boot channel).
* **Fails closed.** Missing Vault / sealed Vault / HTTP error is a hard error.
  An empty string is never written.
* **Idempotent.** Without ``--force``, a key already in Vault is left alone
  (hand-rotation survives). With ``--force``, regenerate + overwrite.

Usage::

    python3 init_vault.py            # generate + seed missing keys
    python3 init_vault.py --force    # regenerate + overwrite every key
    python3 init_vault.py --check    # report presence, write nothing

Environment (bootstrap topology — REQUIRED, never defaulted; Rule 91)::

    VAULT_ADDR       Vault API address
    T0_DIR           RAM tmpfs custodian dir for the postgres handoff
    SOMA_DB_USER     database username (topology)
    SOMA_DB_NAME     database name (topology)
    SOMA_DB_HOST     database host (topology)
    SOMA_DB_PORT     database port (topology)
    SOMA_REDIS_HOST  redis host (topology)
    SOMA_REDIS_PORT  redis port (topology)

The Vault root token is read from the T0_DIR custodian or OS keychain
(written by vault_unseal.py). Never from a repo file. Never from ENV of a
long-running container.
"""

from __future__ import annotations

import json
import os
import secrets as py_secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VAULT_ADDR = (os.environ.get("VAULT_ADDR") or "").rstrip("/")
T0_DIR = Path(os.environ["T0_DIR"]) if os.environ.get("T0_DIR") else None
KEYCHAIN_SERVICE = os.environ.get("KEYCHAIN_SERVICE", "sfm-vault-t0")

FORCE = "--force" in sys.argv
CHECK = "--check" in sys.argv


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _load_vault_token() -> str:
    """Bootstrap token for THIS one-shot process (R-SEC-03).

    Order: RAM tmpfs custodian (T0_DIR) → OS keychain. Never a repo file.
    Never logged. Never an ENV value of a long-running container.
    """
    if T0_DIR is not None:
        path = T0_DIR / "vault_root_token"
        if path.is_file():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value
    try:
        proc = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                "vault_root_token",
                "-w",
            ],
            capture_output=True,
        )
        if proc.returncode == 0:
            value = proc.stdout.decode("utf-8", errors="replace").strip()
            if value:
                return value
    except FileNotFoundError:
        pass
    raise SystemExit(
        "ERROR: no Vault root token available for the seeder.\n"
        "   R-SEC-03: ensure vault_unseal.py left it in the T0_DIR tmpfs\n"
        "   custodian or the OS keychain. It is never read from a file in\n"
        "   the repo and never from a long-running container's ENV."
    )


VAULT_TOKEN = _load_vault_token()


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"ERROR: required environment variable {name} is not set.\n"
            f"   Bootstrap topology is required and never defaulted "
            f"   (RAPID Rule 1 / VIBE Rule 91)."
        )
    return value


def vault_req(method: str, path: str, body: dict | None = None):
    url = f"{VAULT_ADDR}/v1/{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-Vault-Token", VAULT_TOKEN)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {}
        return e.code, payload
    except Exception as e:
        raise SystemExit(f"ERROR: Vault request {method} {path} failed: {type(e).__name__}") from e


def generate_value() -> str:
    """Generate a 256-bit url-safe credential in memory. Never printed."""
    return py_secrets.token_urlsafe(32)


def kv2_write(mount: str, path: str, data: dict) -> None:
    status, payload = vault_req("POST", f"{mount}/data/{path}", {"data": data})
    if status not in (200, 204):
        raise SystemExit(
            f"ERROR: write {mount}/data/{path} -> HTTP {status}. " f"Value was not logged."
        )


def kv2_read(mount: str, path: str) -> dict | None:
    status, payload = vault_req("GET", f"{mount}/data/{path}")
    if status == 404:
        return None
    if status != 200:
        raise SystemExit(f"ERROR: read {mount}/data/{path} -> HTTP {status}.")
    return (payload.get("data") or {}).get("data") or {}


def kv2_ensure_mount(mount: str) -> None:
    """Mount KV v2 if not already present. Idempotent."""
    status, _ = vault_req("POST", "sys/mounts/" + mount, {"type": "kv-v2"})
    # 204 = created, 400 = already mounted. Both are fine.
    if status not in (204, 400):
        raise SystemExit(f"ERROR: mount {mount} -> HTTP {status}.")


def seed_credential(
    mount: str, path: str, key: str, extra: dict | None = None, handoff_filename: str | None = None
) -> str:
    """Generate (or reuse) one credential, write to Vault, optionally hand off.

    Returns "seeded", "skip", or "check".
    """
    if CHECK:
        existing = kv2_read(mount, path)
        present = bool(existing and existing.get(key))
        log(f"   {'present' if present else 'MISSING'}  {mount}/{path}[{key}]")
        return "check"

    existing = kv2_read(mount, path) or {}
    if not FORCE and existing.get(key):
        log(f"   – skipped (already in Vault): {mount}/{path}[{key}]")
        # Still ensure the handoff exists on re-boot (postgres needs it every
        # first-boot of a fresh data volume; the value is the same one Vault
        # already holds).
        if handoff_filename and T0_DIR is not None:
            _write_handoff(handoff_filename, str(existing[key]))
        return "skip"

    value = generate_value()
    if not value:
        raise SystemExit(f"ERROR: generated empty value for {key}. Refusing.")

    data = dict(existing)
    data[key] = value
    if extra:
        data.update(extra)
    kv2_write(mount, path, data)

    # Read-back assert — compare in memory only.
    stored = kv2_read(mount, path) or {}
    if stored.get(key) != value:
        raise SystemExit(
            f"ERROR: read-back mismatch at {mount}/{path}[{key}]. "
            f"Value was not logged. Refusing to treat the seed as successful."
        )
    log(f"   ✔ generated + seeded {mount}/{path}[{key}]  (in-memory only)")

    if handoff_filename and T0_DIR is not None:
        _write_handoff(handoff_filename, value)

    del value, stored
    return "seeded"


def _write_handoff(filename: str, value: str) -> None:
    """RAM tmpfs first-boot handoff. Not the repo, not a disk volume."""
    if T0_DIR is None:
        return
    T0_DIR.mkdir(parents=True, exist_ok=True)
    handoff = T0_DIR / filename
    fd = os.open(str(handoff), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, value.encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(str(handoff), 0o600)
    log(f"   ✔ handoff {filename} → RAM tmpfs {T0_DIR} (first boot only)")


def main() -> int:
    require_env("VAULT_ADDR")
    for name in (
        "SOMA_DB_USER",
        "SOMA_DB_NAME",
        "SOMA_DB_HOST",
        "SOMA_DB_PORT",
        "SOMA_REDIS_HOST",
        "SOMA_REDIS_PORT",
    ):
        require_env(name)

    # Wait for Vault API.
    for _ in range(30):
        try:
            status, _ = vault_req("GET", "sys/health")
            break
        except SystemExit:
            time.sleep(1)
    else:
        raise SystemExit(f"ERROR: Vault at {VAULT_ADDR} is unreachable.")

    # Ensure the KV v2 mounts exist.
    kv2_ensure_mount("somafractalmemory")

    db_topology = {
        "username": os.environ["SOMA_DB_USER"],
        "host": os.environ["SOMA_DB_HOST"],
        "port": os.environ["SOMA_DB_PORT"],
        "dbname": os.environ["SOMA_DB_NAME"],
    }
    redis_topology = {
        "host": os.environ["SOMA_REDIS_HOST"],
        "port": os.environ["SOMA_REDIS_PORT"],
    }

    log("📝 Credentials → somafractalmemory/*  (generated in memory)")
    # Database password: generated → Vault + RAM tmpfs handoff for postgres.
    seed_credential(
        "somafractalmemory",
        "database",
        "password",
        extra=db_topology,
        handoff_filename="postgres_password",
    )
    # Redis password: generated → Vault only (Redis has no auth in this stack
    # yet; the credential is ready for when it does).
    seed_credential(
        "somafractalmemory",
        "redis",
        "password",
        extra=redis_topology,
    )
    # API bearer token: generated → Vault only.
    seed_credential(
        "somafractalmemory",
        "credentials",
        "soma_api_token",
    )
    # MinIO root credentials: generated in memory → Vault + RAM tmpfs handoff
    # for MINIO_ROOT_*_FILE. Never a host file, never a compose env value.
    seed_credential(
        "somafractalmemory",
        "credentials",
        "minio_access_key",
        handoff_filename="minio_access_key",
    )
    seed_credential(
        "somafractalmemory",
        "credentials",
        "minio_secret_key",
        handoff_filename="minio_secret_key",
    )

    if CHECK:
        log("✅ check complete — nothing written.")
    else:
        log("✅ Vault seeded — values exist ONLY in Vault (plus RAM tmpfs handoff).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
