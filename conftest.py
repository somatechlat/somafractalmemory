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
    - Respect environment overrides for REDIS_HOST/PORT, POSTGRES_URL, QDRANT_HOST/PORT,
      KAFKA_BOOTSTRAP_SERVERS. Provide sensible localhost defaults that match docker-compose
      published ports when not set.
    - Attempt to auto-detect common host ports (e.g., Redis 6379 or 6381) and export the
      resolved values back into the environment so tests share a consistent config.
    - Try to start compose services if nothing is reachable, then wait briefly and re-check.
    - Never abort the entire test session; if infra remains unreachable, mark it via env so
      integration tests can skip gracefully.
    """
    # Accept either USE_LIVE_INFRA (preferred) or USE_REAL_INFRA (back-compat)
    use_live = os.getenv("USE_LIVE_INFRA", "").lower() in ("1", "true", "yes")
    use_real = os.getenv("USE_REAL_INFRA", "").lower() in ("1", "true", "yes")
    if not (use_live or use_real):
        return

    print("[conftest] Live infra mode enabled: attempting to bind tests to local infra...")

    # Derive desired endpoints from env or localhost defaults.
    # Postgres
    pg_url = os.getenv(
        "POSTGRES_URL",
        "postgresql://postgres:postgres@localhost:5433/somamemory",
    )
    # Redis: prefer env, else try common host ports (6379 from other stacks, 6381 from this compose)
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port_env = os.getenv("REDIS_PORT")
    if redis_port_env is not None:
        redis_port = int(redis_port_env)
    else:
        # Probe for a reachable Redis on localhost
        detected = _first_reachable("localhost", [6379, 6381])
        redis_port = detected if detected is not None else 6379
    # Qdrant
    q_host = os.getenv("QDRANT_HOST", "localhost")
    q_port = int(os.getenv("QDRANT_PORT", "6333"))
    # Kafka (first bootstrap server)
    kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
    first_broker = kafka_bootstrap.split(",")[0]
    try:
        k_host, k_port_raw = first_broker.split(":", 1)
        # Strip any trailing path suffix (unlikely here)
        k_port = int(k_port_raw.split("/")[0])
    except Exception:
        k_host, k_port = "localhost", 19092

    # Export back resolved env for tests and library code.
    os.environ["POSTGRES_URL"] = pg_url
    os.environ["REDIS_HOST"] = redis_host
    os.environ["REDIS_PORT"] = str(redis_port)
    os.environ["QDRANT_HOST"] = q_host
    os.environ["QDRANT_PORT"] = str(q_port)
    # Align Qdrant collection with the active namespace to keep test scrolls small and recent.
    # Default API namespace is "api_ns"; respect override if provided. If the preferred
    # namespace collection does not exist but another known namespace does, fall back to it.
    preferred_ns = os.getenv("SOMA_MEMORY_NAMESPACE", "api_ns")
    chosen_collection = preferred_ns
    try:
        from qdrant_client import QdrantClient

        qc = QdrantClient(host=q_host, port=q_port)
        cols = {c.name for c in qc.get_collections().collections}
        # Prefer the preferred namespace if present, else a common default used by the API settings,
        # else fall back to the legacy memory_vectors for compatibility.
        if preferred_ns in cols:
            chosen_collection = preferred_ns
        elif "somabrain_ns:public" in cols:
            chosen_collection = "somabrain_ns:public"
        elif "api_ns" in cols:
            chosen_collection = "api_ns"
        elif "memory_vectors" in cols:
            chosen_collection = "memory_vectors"
    except Exception:
        # If Qdrant probe fails, keep the preferred default; tests will still run.
        chosen_collection = preferred_ns
    os.environ["QDRANT_COLLECTION"] = chosen_collection
    os.environ["KAFKA_BOOTSTRAP_SERVERS"] = f"{k_host}:{k_port}"

    # Connectivity check with small retry if needed.
    deadline = time.time() + 10
    ok_pg = ok_redis = ok_q = ok_kafka = False
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
        ok_q = _tcp_open(q_host, q_port)
        ok_kafka = _tcp_open(k_host, k_port)
        if ok_pg and ok_redis and ok_q and ok_kafka:
            break
        time.sleep(0.5)

    if not (ok_pg and ok_redis and ok_q and ok_kafka):
        # Best-effort to start compose services if nothing reachable on localhost
        _start_compose_services(["redis", "postgres", "qdrant", "kafka"])
        # Wait up to another 20s
        deadline = time.time() + 20
        while time.time() < deadline and not (ok_pg and ok_redis and ok_q and ok_kafka):
            ok_pg = _tcp_open(pg_host, pg_port)
            ok_redis = _tcp_open(redis_host, redis_port)
            ok_q = _tcp_open(q_host, q_port)
            ok_kafka = _tcp_open(k_host, k_port)
            if ok_pg and ok_redis and ok_q and ok_kafka:
                break
            time.sleep(1.0)

    if ok_pg and ok_redis and ok_q and ok_kafka:
        print("[conftest] All required infra reachable.")
        os.environ["SOMA_INFRA_AVAILABLE"] = "1"
    else:
        missing = []
        if not ok_redis:
            missing.append("Redis")
        if not ok_pg:
            missing.append("Postgres")
        if not ok_q:
            missing.append("Qdrant")
        if not ok_kafka:
            missing.append("Kafka")
        print(
            f"[conftest] Required infra not reachable: {', '.join(missing)}. "
            "Integration tests may skip."
        )
        # Signal tests to skip integration paths gracefully
        os.environ["SOMA_INFRA_AVAILABLE"] = "0"
        # Do not exit the entire session.
    return
