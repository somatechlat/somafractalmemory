import os
import shutil
import socket
import subprocess

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

    # Set default connection URLs using internal Docker service names.
    os.environ.setdefault("REDIS_URL", "redis://redis:6379/0")
    os.environ.setdefault(
        "POSTGRES_URL",
        "postgresql://postgres:postgres@postgres:5432/somamemory",
    )
    os.environ.setdefault("QDRANT_HOST", "qdrant")
    os.environ.setdefault("QDRANT_PORT", "6333")
    os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

    # Quick connectivity checks – abort if any required service is unreachable.
    redis_host = "redis"
    redis_port = 6379
    pg_host = "postgres"
    pg_port = 5432
    q_host = "qdrant"
    q_port = 6333
    kafka_host = "kafka"
    kafka_port = 9092

    ok_redis = _tcp_open(redis_host, redis_port)
    ok_pg = _tcp_open(pg_host, pg_port)
    ok_q = _tcp_open(q_host, q_port)
    ok_kafka = _tcp_open(kafka_host, kafka_port)

    if not (ok_redis and ok_pg and ok_q and ok_kafka):
        missing = []
        if not ok_redis:
            missing.append("Redis")
        if not ok_pg:
            missing.append("Postgres")
        if not ok_q:
            missing.append("Qdrant")
        if not ok_kafka:
            missing.append("Kafka")
        pytest.exit(
            f"[conftest] Required infra not reachable: {', '.join(missing)}. "
            "Ensure `docker compose up -d` is running and ports are correct."
        )
    # All services reachable – continue with tests.
    print("[conftest] All required infra reachable.")
    return
