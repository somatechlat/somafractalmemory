import os
import shutil
import socket
import subprocess
import time

import pytest

from somafractalmemory.config import settings

# Ensure FastAPI surface can import with mandatory auth in test runs.
os.environ.setdefault("SOMA_API_TOKEN", "test-token")


def _tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def _start_compose_services(services: list[str]) -> None:
    # Try to start required services via docker compose in the repo root
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

    Note: Qdrant support was removed per architecture decision - Milvus is the only vector backend.
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
    pg_url = settings.postgres_url or "postgresql://postgres:postgres@localhost:5433/somamemory"
    # Redis: prefer env, else try common host ports (6379 from other stacks, 6381 from this compose)
    redis_host = settings.redis_host
    redis_port_env = str(settings.redis_port) if settings.redis_port else None
    if redis_port_env is not None:
        redis_port = int(redis_port_env)
    else:
        # Probe for a reachable Redis on localhost
        detected = _first_reachable("localhost", [6379, 6381])
        redis_port = detected if detected is not None else 6379
    # Milvus (Qdrant removed - standardized on Milvus)
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
