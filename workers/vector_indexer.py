import hashlib
import json
import logging
import os

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

logger = logging.getLogger(__name__)

# Configuration (environment variables, with defaults matching docker-compose.dev.yml)
_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
# Default collection name; we also index into namespace-specific collections when present
_QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "memory_vectors")
_QDRANT_EXTRA_COLLECTION = os.getenv("QDRANT_EXTRA_COLLECTION")
_VECTOR_DIM = int(os.getenv("MEMORY_VECTOR_DIM", "768"))

# Lazy singleton client
_qclient = None


def _get_client():
    global _qclient
    if _qclient is None:
        _qclient = QdrantClient(url=_QDRANT_URL)
        # Ensure default collection exists eagerly
        _ensure_collection(_qclient, _QDRANT_COLLECTION)
    return _qclient


def _ensure_collection(client: QdrantClient, collection_name: str):
    """Create the given collection if it does not exist, using modern Qdrant API."""
    try:
        if not client.collection_exists(collection_name=collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=_VECTOR_DIM, distance=Distance.COSINE),
            )
    except Exception as e:
        # Log the error but allow the client to continue; the calling code will
        # handle any further failures.
        logger.error(f"Failed to ensure Qdrant collection {collection_name}: {e}")


def _embed(payload: dict) -> list[float]:
    """Deterministic hash-based embedding aligned with core fallback.

    - blake2b over JSON
    - map bytes to float32
    - tile/truncate to vector_dim
    - L2-normalize
    """
    text = json.dumps(payload, sort_keys=True)
    h = hashlib.blake2b(text.encode("utf-8")).digest()
    arr = np.frombuffer(h, dtype=np.uint8).astype("float32")
    if arr.size < _VECTOR_DIM:
        reps = int(np.ceil(_VECTOR_DIM / arr.size))
        arr = np.tile(arr, reps)
    vec = arr[:_VECTOR_DIM]
    try:
        norm = float(np.linalg.norm(vec)) or 1.0
        vec = vec / norm
    except Exception:
        pass
    return vec.tolist()


def index_event(record: dict) -> bool:
    """Upsert a memory event into Qdrant.

    The function validates required fields, generates a deterministic vector from
    the ``payload`` and performs an ``upsert`` using the ``id`` as the point ID.
    """
    required = ("id", "event_id", "payload")
    if not all(k in record for k in required):
        logger.warning("Record missing required fields for vector indexing: %s", record)
        return False
    if not record.get("payload"):
        logger.warning("No payload to index for record %s", record.get("event_id"))
        return False
    client = _get_client()
    try:
        point = PointStruct(
            id=record["id"],
            vector=_embed(record["payload"]),
            payload=record["payload"],
        )
        # Index into default collection
        _ensure_collection(client, _QDRANT_COLLECTION)
        client.upsert(collection_name=_QDRANT_COLLECTION, points=[point])

        # Also index into namespace-named collection for per-namespace queries
        namespace = str(record.get("namespace", "")).strip()
        if namespace:
            try:
                _ensure_collection(client, namespace)
                client.upsert(collection_name=namespace, points=[point])
            except Exception as ns_exc:  # pragma: no cover
                logger.warning(
                    "Failed to index into namespace collection %s: %s", namespace, ns_exc
                )

        # Optional extra collection (useful for tests to keep scroll windows small)
        if _QDRANT_EXTRA_COLLECTION:
            try:
                _ensure_collection(client, _QDRANT_EXTRA_COLLECTION)
                client.upsert(collection_name=_QDRANT_EXTRA_COLLECTION, points=[point])
            except Exception as ex_exc:  # pragma: no cover
                logger.warning(
                    "Failed to index into extra collection %s: %s", _QDRANT_EXTRA_COLLECTION, ex_exc
                )

        logger.info("Indexed event %s into Qdrant", record["event_id"])
        return True
    except Exception as exc:  # pragma: no cover – runtime error handling
        logger.exception("Failed to upsert vector for record %s: %s", record.get("event_id"), exc)
        return False
