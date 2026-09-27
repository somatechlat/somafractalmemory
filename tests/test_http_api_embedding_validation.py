"""Test precomputed-embedding validation on the HTTP API - Django Ninja.

Validation-path tests only (no database access): wrong-dimension and
non-finite embeddings must fail with 400 before any store/search happens.

100% Django patterns - NO FastAPI.

Auth uses the real deployment token from the environment / ``.env`` —
never a synthesised placeholder (VIBE rules).
"""

import os

import pytest

try:
    from dotenv import load_dotenv

    load_dotenv(".env", override=False)
except ImportError:  # pragma: no cover
    pass

# Set environment variables for localhost infrastructure BEFORE importing API
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somafractalmemory.settings")
# Required Django settings for import-time validation
os.environ.setdefault("SOMA_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SOMA_ALLOWED_HOSTS", "*")

API_TOKEN = os.environ.get("SOMA_API_TOKEN", "")

try:
    from django.conf import settings as django_settings
    from ninja.testing import TestClient

    from somafractalmemory.api import api

    client = TestClient(api)
    VECTOR_DIM = int(getattr(django_settings, "SOMA_VECTOR_DIM", 0) or 0)
    SKIP_REASON = None
except ImportError as e:
    client = None
    VECTOR_DIM = 0
    SKIP_REASON = f"Missing dependency: {e}"
except RuntimeError as e:
    # Infrastructure not available (Redis/Postgres/Milvus not running)
    client = None
    VECTOR_DIM = 0
    SKIP_REASON = f"Infrastructure not available: {e}"

if SKIP_REASON is None and not API_TOKEN:
    SKIP_REASON = "SOMA_API_TOKEN must be set from the deployment environment"
if SKIP_REASON is None and VECTOR_DIM <= 0:
    SKIP_REASON = "SOMA_VECTOR_DIM is not configured"

pytestmark = pytest.mark.skipif(
    SKIP_REASON is not None,
    reason=SKIP_REASON or "Missing dependencies",
)

HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


def test_store_rejects_wrong_embedding_dimension():
    """A precomputed embedding with the wrong dimension returns 400."""
    payload = {
        "coord": "0.1,0.2,0.3",
        "payload": {"text": "hello"},
        "embedding": [0.0] * (VECTOR_DIM + 1),
    }
    r = client.post("/memories", headers=HEADERS, json=payload)
    assert r.status_code == 400
    detail = r.json().get("detail", "")
    assert "dimension" in detail.lower()
    assert str(VECTOR_DIM) in detail


def test_store_rejects_empty_embedding():
    payload = {
        "coord": "0.1,0.2,0.3",
        "payload": {"text": "hello"},
        "embedding": [],
    }
    r = client.post("/memories", headers=HEADERS, json=payload)
    assert r.status_code == 400


def test_store_rejects_non_finite_embedding():
    # JSON has no NaN literal; a huge number that overflows to inf on parse is
    # not reliable either — use an explicit invalid value via python client json.
    payload = {
        "coord": "0.1,0.2,0.3",
        "payload": {"text": "hello"},
        "embedding": [1e400] + [0.0] * (VECTOR_DIM - 1),  # parses to inf
    }
    r = client.post("/memories", headers=HEADERS, json=payload)
    assert r.status_code == 400


def test_search_rejects_wrong_embedding_dimension():
    payload = {"query": "", "embedding": [0.0] * 3}
    r = client.post("/memories/search", headers=HEADERS, json=payload)
    assert r.status_code == 400
    detail = r.json().get("detail", "")
    assert "dimension" in detail.lower()


def test_malformed_coord_still_rejected():
    """Backward compatibility: float-tuple coord contract is unchanged."""
    payload = {
        "coord": "target-learnbench-3c6c5e16-282e3f50",
        "memory_type": "episodic",
        "payload": {"foo": "bar"},
    }
    r = client.post("/memories", headers=HEADERS, json=payload)
    assert r.status_code == 400


def test_old_request_shape_accepted_by_schema_layer():
    """Old callers that omit embedding/tenant_id still validate."""
    payload = {
        "coord": "0.9,0.8,0.7",
        "payload": {"test": "value"},
        "memory_type": "semantic",
    }
    # Validation of coord/embedding happens before any DB write; a well-formed
    # request must get past schema + coord + dim checks (status 500 here would
    # mean it reached the service layer, which needs Postgres in this test env).
    r = client.post("/memories", headers=HEADERS, json=payload)
    assert r.status_code != 400
    assert r.status_code != 422
