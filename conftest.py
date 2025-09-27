import os
import shutil
import socket
import subprocess
import time

import pytest


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
            "docker not found; cannot auto-start services. Please start Redis/Postgres/Qdrant manually."
        )
        return
    # Use `docker compose` (v2) to start services
    cmd = ["docker", "compose", "up", "-d"] + services
    try:
        subprocess.check_call(cmd, cwd=os.path.dirname(__file__) or ".")
    except subprocess.CalledProcessError as exc:
        print(f"docker compose up failed: {exc}. Please start services manually.")


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """If USE_REAL_INFRA=1 is set, wire tests to use localhost services (Redis/Postgres/Qdrant).

    Behavior:
    - Export sensible defaults for REDIS_URL, POSTGRES_URL, QDRANT_HOST, QDRANT_PORT if not already set.
    - If services are not reachable, attempt `docker compose up -d redis postgres qdrant`.
    - Wait up to 60s for services to become responsive; otherwise skip tests.
    """
    use_real = os.getenv("USE_REAL_INFRA", "0").lower() in ("1", "true", "yes")
    if not use_real:
        return

    print("[conftest] USE_REAL_INFRA enabled: attempting to bind tests to local infra...")

    # Default to compose mapping (host port 6380 -> container 6379) to avoid conflicts
    os.environ.setdefault("REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6380/0"))
    # Default to compose mapping (host port 5433 -> container 5432)
    os.environ.setdefault(
        "POSTGRES_URL",
        os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5433/somamemory"),
    )
    os.environ.setdefault("QDRANT_HOST", os.getenv("QDRANT_HOST", "localhost"))
    os.environ.setdefault("QDRANT_PORT", os.getenv("QDRANT_PORT", "6333"))

    # Quick connectivity checks
    redis_host = os.environ["REDIS_URL"].split("//")[-1].split(":")[0]
    redis_port = int(os.environ["REDIS_URL"].split(":")[-1].split("/")[0])
    pg_host = os.environ["POSTGRES_URL"].split("@")[1].split(":")[0]
    pg_port = int(os.environ["POSTGRES_URL"].split(":")[-1].split("/")[0])
    q_host = os.environ["QDRANT_HOST"]
    q_port = int(os.environ["QDRANT_PORT"])

    ok_redis = _tcp_open(redis_host, redis_port)
    ok_pg = _tcp_open(pg_host, pg_port)
    ok_q = _tcp_open(q_host, q_port)

    if ok_redis and ok_pg and ok_q:
        print("[conftest] Redis, Postgres and Qdrant are reachable on localhost.")
        return

    # On Docker Desktop (macOS) containers may be reachable at host.docker.internal
    # if localhost checks fail, try that as a fallback before attempting to start compose.
    try_alternate = os.uname().sysname.lower().startswith("darwin")
    if try_alternate:
        alt_host = "host.docker.internal"
        print(f"[conftest] Localhost unreachable; trying alternate host {alt_host}...")
        alt_ok_redis = _tcp_open(alt_host, redis_port)
        alt_ok_pg = _tcp_open(alt_host, pg_port)
        alt_ok_q = _tcp_open(alt_host, q_port)
        if alt_ok_redis and alt_ok_pg and alt_ok_q:
            print(f"[conftest] Services reachable via {alt_host}; updating env vars.")
            os.environ["REDIS_URL"] = os.environ["REDIS_URL"].replace(redis_host, alt_host)
            os.environ["POSTGRES_URL"] = os.environ["POSTGRES_URL"].replace(pg_host, alt_host)
            os.environ["QDRANT_HOST"] = alt_host
            return

    print(
        "[conftest] One or more infra services are unreachable. Attempting to start missing services via docker compose..."
    )
    # Only start services that are not reachable to avoid port conflicts with existing containers
    missing = []
    if not ok_redis:
        missing.append("redis")
    if not ok_pg:
        missing.append("postgres")
    if not ok_q:
        missing.append("qdrant")

    if missing:
        try:
            _start_compose_services(missing)
        except Exception as exc:
            print(f"[conftest] docker compose up reported an error: {exc}")
    else:
        print("[conftest] No missing services to start (ports already in use).")

    # Wait for services (give Docker Desktop a bit longer on macOS)
    deadline = time.time() + 90
    while time.time() < deadline:
        ok_redis = _tcp_open(redis_host, redis_port)
        ok_pg = _tcp_open(pg_host, pg_port)
        ok_q = _tcp_open(q_host, q_port)
        if ok_redis and ok_pg and ok_q:
            print("[conftest] Services are now reachable.")
            return
        time.sleep(2)

    # If we reach here, attempt one last graceful check: maybe compose failed due to port bind but services are present
    ok_redis = _tcp_open(redis_host, redis_port)
    ok_pg = _tcp_open(pg_host, pg_port)
    ok_q = _tcp_open(q_host, q_port)
    if ok_redis and ok_pg and ok_q:
        print("[conftest] Services are reachable after final check.")
        return

    pytest.exit(
        "Required infra (Redis/Postgres/Qdrant) not reachable after timeout. Start them and re-run tests."
    )
