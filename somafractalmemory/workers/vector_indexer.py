# fmt: off
# isort: skip_file
"""Utility for ensuring a Qdrant collection exists.

Provides a helper that checks whether the configured Qdrant collection exists
and creates it if necessary, using the modern Qdrant client API.
"""

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from .config import QDRANT_COLLECTION, _VECTOR_DIM

logger = structlog.get_logger()

# Initialise a client pointing at the local Qdrant instance used in tests.
client: QdrantClient = QdrantClient(host="localhost", port=6333)


def create_collection_if_not_exists() -> None:
    """Create the Qdrant collection if it does not already exist."""
    try:
        if not client.collection_exists(collection_name=QDRANT_COLLECTION):
            client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=_VECTOR_DIM,
                    distance=Distance.COSINE,
                ),
            )
    except Exception as e:  # pragma: no cover
        logger.error(
            "Failed to create Qdrant collection %s: %s",
            QDRANT_COLLECTION,
            e,
        )

# End of file
