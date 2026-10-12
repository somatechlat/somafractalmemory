"""Module conftest."""

import os
import shutil
import socket
import subprocess
import time

import django
import pytest
from django.conf import settings

# ---------------------------------------------------------------------------
# Test-only Vault stub. TEST DATA, not a deployment default.
#
# ``somafractalmemory.settings.django_core`` resolves every secret from Vault
# only (Rule 164 / Settings Law 2026-10-09: never ENV, never a code default).
# These fixtures are served through the real vault_client module with its
# lookup functions patched, so the production resolution path is exercised
# and no secret is placed in the process environment.
# ---------------------------------------------------------------------------
_TEST_SECRETS = {
    (
        "somafractalmemory/credentials",
        "soma_secret_key",
    ): "test-only-insecure-secret-key-not-for-production",
    ("somafractalmemory/database", "username"): "test_user",
    ("somafractalmemory/database", "password"): "test_password_not_a_real_credential",
    ("secret/agent/credentials", "soma_api_token"): "test-token",
}


def _real_vault_available() -> bool:
    """True when real Vault topology is present (VAULT_ADDR + VAULT_TOKEN_FILE)."""
    addr = os.environ.get("VAULT_ADDR", "")
    token_file = os.environ.get("VAULT_TOKEN_FILE", "")
    return bool(addr) and bool(token_file) and os.path.isfile(token_file)


def _install_test_vault_stub() -> None:
    # Real-infra mode: when live Vault topology is present, do NOT stub.
    # The production vault_client resolves credentials from Vault, so tests
    # exercise the real path and the real database password matches.
    if _real_vault_available():
        return

    from somafractalmemory.admin.core.security import vault_client as _vc

    def _test_vault_topology_present() -> bool:
        return True

    def _test_get_secret(path: str, key: str | None = None):
        if key is None:
            return {k: v for (p, k), v in _TEST_SECRETS.items() if p == path}
        value = _TEST_SECRETS.get((path, key))
        if value is None:
            raise _vc.SecretNotFound(f"Key {key!r} not found at path {path!r}")
        return value

    _vc.vault_topology_present = _test_vault_topology_present
    _vc.get_secret = _test_get_secret


_install_test_vault_stub()

# ---------------------------------------------------------------------------
# Test-only topology. TOPOLOGY, not a secret. Must be set BEFORE
# ``django.setup()``, which is what imports settings.
# Real-infra env (VAULT_ADDR / SOMA_DB_HOST / ...) always wins — never override.
# ---------------------------------------------------------------------------
_TEST_ENV = {
    "SOMA_ALLOWED_HOSTS": "testserver,localhost,127.0.0.1",
    "SOMA_DB_NAME": "somafractalmemory",
    "SOMA_DB_HOST": "localhost",
    "SOMA_DB_PORT": "5432",
    # Dual-store contract: Milvus topology must be present before django.setup()
    # so settings/infra.py reads it at import time (resolve_optional returns None
    # otherwise and MemoryService._build_vector_store refuses — which is correct
    # production behaviour but needs test fixture values here).
    "SOMA_MILVUS_HOST": "localhost",
    "SOMA_MILVUS_PORT": "19530",
}
for _key, _value in _TEST_ENV.items():
    os.environ.setdefault(_key, _value)

# Force Setup
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somafractalmemory.settings")
django.setup()


def _tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Execute tcp open.

    Args:
        host: The host.
        port: The port.
        timeout: The timeout.
    """

    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def _start_compose_services(services: list[str]) -> None:
    # Try to start required services via docker compose in the repo root
    """Execute start compose services.

    Args:
        services: The services.
    """

    dc = shutil.which("docker")
    if not dc:
        print(
            "docker not found; cannot auto-start services. Please start Redis/Postgres/Milvus manually."
        )
        return
    # Use `docker compose` (v2) to start services
    cmd = ["docker", "compose", "up", "-d"] + services
    try:
        subprocess.check_call(cmd, cwd=os.path.dirname(__file__) or ".")
    except subprocess.CalledProcessError as exc:
        print(f"docker compose up failed: {exc}. Please start services manually.")


def _first_reachable(host: str, ports: list[int], timeout: float = 1.0) -> int | None:
    """Return the first port that is reachable on host from the provided list, else None."""
    for p in ports:
        if _tcp_open(host, p, timeout=timeout):
            return p
    return None


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """If USE_REAL_INFRA=1 is set, wire tests to use reachable services.

    Behavior:
    - Respect environment overrides for REDIS_HOST/PORT, POSTGRES_URL, SOMA_MILVUS_HOST/PORT,
      KAFKA_BOOTSTRAP_SERVERS. Provide sensible localhost defaults that match docker-compose
      published ports when not set.
    - Attempt to auto-detect common host ports (e.g., Redis 6379 or 6381) and export the
      resolved values back into the environment so tests share a consistent config.
    - Try to start compose services if nothing is reachable, then wait briefly and re-check.
    - Never abort the entire test session; if infra remains unreachable, mark it via env so
      integration tests can skip gracefully.

    Note: Milvus is the only vector backend.
    """
    # Accept either USE_LIVE_INFRA (preferred) or USE_REAL_INFRA (back-compat)
    use_live = settings.use_live_infura if hasattr(settings, "use_live_infura") else False
    # NOTE: The original flags are not part of the central Settings; kept for backward compatibility.
    use_real = settings.use_real_infra if hasattr(settings, "use_real_infra") else False
    if not (use_live or use_real):
        return

    print("[conftest] Live infra mode enabled: attempting to bind tests to local infra...")

    # Derive desired endpoints from env or localhost defaults.
    # Postgres URL – already provided by the central settings. If for any reason it is
    # missing (unlikely in normal operation), fall back to a sensible default that
    # matches the docker‑compose configuration.
    if settings.postgres_url:
        pg_url = settings.postgres_url
    else:
        # Avoid committing credential-like defaults. If a password is needed, it must come
        # from the environment (e.g. standalone compose or CI secret injection).
        pg_user = os.environ.get("POSTGRES_USER", "postgres")
        pg_pass = os.environ.get("SOMA_DB_PASSWORD") or os.environ.get("POSTGRES_PASSWORD")
        if pg_pass:
            pg_url = "postgresql://" + pg_user + ":" + pg_pass + "@localhost:5433/somamemory"
        else:
            pg_url = "postgresql://" + pg_user + "@localhost:5433/somamemory"
    # Redis: prefer env, else try common host ports (6379 from other stacks, 6381 from this compose)
    redis_host = settings.redis_host
    redis_port_env = str(settings.redis_port) if settings.redis_port else None
    if redis_port_env is not None:
        redis_port = int(redis_port_env)
    else:
        # Probe for a reachable Redis on localhost
        detected = _first_reachable("localhost", [6379, 6381])
        redis_port = detected if detected is not None else 6379
    # Milvus (standardized on Milvus)
    milvus_host = getattr(settings, "milvus_host", "milvus")
    milvus_port = getattr(settings, "milvus_port", 19530)

    # Export back resolved env for tests and library code.
    # Convert Pydantic types to strings for environment variables
    os.environ["POSTGRES_URL"] = str(pg_url) if pg_url else ""
    os.environ["REDIS_HOST"] = str(redis_host) if redis_host else "localhost"
    os.environ["REDIS_PORT"] = str(redis_port)
    os.environ["SOMA_MILVUS_HOST"] = str(milvus_host) if milvus_host else "localhost"
    os.environ["SOMA_MILVUS_PORT"] = str(milvus_port)

    # Connectivity check with small retry if needed.
    deadline = time.time() + 10
    ok_pg = ok_redis = ok_milvus = False
    pg_host, pg_port = "localhost", 5432
    while time.time() < deadline:
        # Parse pg host/port from URL for reachability
        try:
            import re

            m = re.search(r"@([^:/]+):(\d+)", pg_url)
            pg_host = m.group(1) if m else "localhost"
            pg_port = int(m.group(2)) if m else 5432
        except Exception:
            pg_host, pg_port = "localhost", 5432

        ok_pg = _tcp_open(pg_host, pg_port)
        ok_redis = _tcp_open(redis_host, redis_port)
        ok_milvus = _tcp_open(milvus_host, milvus_port)
        if ok_pg and ok_redis and ok_milvus:
            break
        time.sleep(0.5)

    if not (ok_pg and ok_redis and ok_milvus):
        # Best-effort to start compose services if nothing reachable on localhost
        _start_compose_services(["redis", "postgres", "milvus"])
        # Wait up to another 20s
        deadline = time.time() + 20
        while time.time() < deadline and not (ok_pg and ok_redis and ok_milvus):
            ok_pg = _tcp_open(pg_host, pg_port)
            ok_redis = _tcp_open(redis_host, redis_port)
            ok_milvus = _tcp_open(milvus_host, milvus_port)
            if ok_pg and ok_redis and ok_milvus:
                break
            time.sleep(1.0)

    if ok_pg and ok_redis and ok_milvus:
        print("[conftest] All required infra reachable.")
        os.environ["SOMA_INFRA_AVAILABLE"] = "1"
    else:
        missing = []
        if not ok_redis:
            missing.append("Redis")
        if not ok_pg:
            missing.append("Postgres")
        if not ok_milvus:
            missing.append("Milvus")
        print(
            f"[conftest] Required infra not reachable: {', '.join(missing)}. "
            "Integration tests may skip."
        )
        # Signal tests to skip integration paths gracefully
        os.environ["SOMA_INFRA_AVAILABLE"] = "0"
        # Do not exit the entire session.
    return
