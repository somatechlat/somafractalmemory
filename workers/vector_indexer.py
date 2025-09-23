import json
import logging
import os
from typing import Dict

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

logger = logging.getLogger(__name__)

# Configuration (environment variables, with defaults matching docker-compose.dev.yml)
_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
_QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "memory_vectors")
_VECTOR_DIM = int(os.getenv("MEMORY_VECTOR_DIM", "768"))

# Lazy singleton client
_qclient = None


def _get_client():
    global _qclient
    if _qclient is None:
        _qclient = QdrantClient(url=_QDRANT_URL)
        _ensure_collection(_qclient)
    return _qclient


def _ensure_collection(client: QdrantClient):
    """Create the collection if it does not exist, using the modern Qdrant API.

    The previous implementation used ``client.recreate_collection`` which is
    deprecated. We now check ``collection_exists`` and only create the collection
    when it is missing.
    """
    try:
        if not client.collection_exists(collection_name=_QDRANT_COLLECTION):
            client.create_collection(
                collection_name=_QDRANT_COLLECTION,
                vectors_config=VectorParams(size=_VECTOR_DIM, distance=Distance.COSINE),
            )
    except Exception as e:
        # Log the error but allow the client to continue; the calling code will
        # handle any further failures.
        logger.error(f"Failed to ensure Qdrant collection {_QDRANT_COLLECTION}: {e}")


def _embed(payload: Dict) -> list[float]:
    """Create a deterministic pseudo‑embedding from the payload.

    For now we hash the JSON representation and expand it to the required
    dimension using a simple PRNG (XORShift). This provides a stable vector for
    tests without needing an external model.
    """
    # Serialize payload deterministically
    data = json.dumps(payload, sort_keys=True).encode()
    # Simple 64‑bit hash
    h = int.from_bytes(data[:8], "big", signed=False) if len(data) >= 8 else len(data)
    # Generate vector using a tiny PRNG seeded with the hash
    vec = []
    seed = h
    for _ in range(_VECTOR_DIM):
        # XORShift algorithm (fast, deterministic)
        seed ^= (seed << 13) & 0xFFFFFFFFFFFFFFFF
        seed ^= seed >> 7
        seed ^= (seed << 17) & 0xFFFFFFFFFFFFFFFF
        # Map to float in [-1, 1]
        vec.append(((seed % 2000) - 1000) / 1000.0)
    return vec


def index_event(record: Dict) -> bool:
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
        client.upsert(collection_name=_QDRANT_COLLECTION, points=[point])
        logger.info("Indexed event %s into Qdrant", record["event_id"])
        return True
    except Exception as exc:  # pragma: no cover – runtime error handling
        logger.exception("Failed to upsert vector for record %s: %s", record.get("event_id"), exc)
        return False
