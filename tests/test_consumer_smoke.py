import os
import time
import uuid

import psycopg2
import pytest
import requests
from qdrant_client import QdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)


@pytest.mark.integration
def test_consumer_end_to_end_smoke():
    use_live = os.getenv("USE_LIVE_INFRA") in ("1", "true", "yes")
    use_real = os.getenv("USE_REAL_INFRA") in ("1", "true", "yes")
    if not (use_live or use_real):
        pytest.skip(
            "Requires live infra (USE_LIVE_INFRA=1 or USE_REAL_INFRA=1) and running docker-compose stack"
        )

    # Helper: wait for API readiness
    @retry(
        reraise=True,
        stop=stop_after_attempt(10),
        wait=wait_random_exponential(multiplier=0.2, max=2.5),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
    )
    def _wait_health():
        r = requests.get("http://127.0.0.1:9595/healthz", timeout=5)
        r.raise_for_status()
        j = r.json()
        assert j.get("kv_store") and j.get("vector_store") and j.get("graph_store")
        return True

    _wait_health()

    # 1) Store a marker via API to publish an event
    marker = f"consumer-e2e-{uuid.uuid4()}"

    @retry(
        reraise=True,
        stop=stop_after_attempt(8),
        wait=wait_random_exponential(multiplier=0.25, max=3.0),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
    )
    def _post_store():
        with requests.Session() as s:
            # Avoid keep-alive to reduce risk of mid-flight connection resets
            headers = {"Content-Type": "application/json", "Connection": "close"}
            api_token = os.getenv("SOMA_API_TOKEN")
            if api_token:
                headers["Authorization"] = f"Bearer {api_token}"
            return s.post(
                "http://127.0.0.1:9595/store",
                json={
                    "coord": "11,22,33",
                    "payload": {"task": marker, "importance": 9},
                    "type": "episodic",
                },
                headers=headers,
                timeout=10,
            )

    resp = _post_store()
    assert resp.status_code == 200, resp.text

    # 2) Poll Postgres memory_events for the marker
    pg_url = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5433/somamemory")
    conn = psycopg2.connect(pg_url)
    conn.autocommit = True
    found_db = False
    deadline = time.time() + 20
    while time.time() < deadline and not found_db:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM memory_events WHERE payload->>'task' = %s", (marker,))
            cnt = cur.fetchone()[0]
            found_db = cnt and cnt > 0
        if not found_db:
            time.sleep(1.0)
    assert found_db, "Consumer did not upsert record into Postgres in time"

    # 3) Poll Qdrant vector presence (collection defaults to memory_vectors in worker)
    qc = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"), port=int(os.getenv("QDRANT_PORT", "6333"))
    )
    found_vec = False
    deadline = time.time() + 30
    env_collection = os.getenv("QDRANT_COLLECTION", "memory_vectors")
    candidates = [env_collection, "memory_vectors", "default", "api_ns"]
    payload_filter = Filter(must=[FieldCondition(key="task", match=MatchValue(value=marker))])
    while time.time() < deadline and not found_vec:
        for collection in candidates:
            try:
                # 1) Use count with filter (works across client versions)
                cnt = qc.count(collection_name=collection, count_filter=payload_filter, exact=True)
                count_val = getattr(cnt, "count", cnt)
                found_vec = bool(count_val and int(count_val) > 0)
                if found_vec:
                    break
            except Exception:
                pass
            try:
                # 2) Try scroll with 'filter' kw
                items, _ = qc.scroll(
                    collection_name=collection,
                    limit=1,
                    with_payload=True,
                    filter=payload_filter,  # type: ignore[arg-type]
                )
                found_vec = len(items) > 0
                if found_vec:
                    break
            except Exception:
                try:
                    # 3) Try scroll with 'scroll_filter' kw
                    items, _ = qc.scroll(
                        collection_name=collection,
                        limit=1,
                        with_payload=True,
                        scroll_filter=payload_filter,  # type: ignore[arg-type]
                    )
                    found_vec = len(items) > 0
                    if found_vec:
                        break
                except Exception:
                    # 4) Last resort small unfiltered scroll
                    try:
                        items, _ = qc.scroll(
                            collection_name=collection,
                            limit=200,
                            with_payload=True,
                        )
                        found_vec = any(
                            getattr(p, "payload", {}).get("task") == marker
                            for p in items
                            if getattr(p, "payload", None)
                        )
                        if found_vec:
                            break
                    except Exception:
                        pass
        if not found_vec:
            time.sleep(1.0)
    assert found_vec, "Consumer did not index vector into Qdrant in time"
