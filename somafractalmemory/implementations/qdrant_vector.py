"""
Qdrant Vector Store implementation for SomaFractalMemory.

This module provides a Qdrant-backed implementation of the IVectorStore
interface, primarily used for local testing with on-disk storage.
Production deployments should use MilvusVectorStore.
"""

from collections.abc import Iterator
from typing import Any

from somafractalmemory.core import VectorStoreError
from somafractalmemory.interfaces.storage import IVectorStore

# Module-level cache for Qdrant clients
_qdrant_clients: dict[tuple, Any] = {}

# Check if qdrant-client is available
try:
    import qdrant_client
    from qdrant_client.models import Distance, PointIdsList, PointStruct, VectorParams

    _QDRANT_AVAILABLE = True
except ImportError:
    _QDRANT_AVAILABLE = False
    qdrant_client = None  # type: ignore


class QdrantVectorStore(IVectorStore):
    """Qdrant implementation of the vector store interface.

    Used primarily for local testing with on-disk storage. Production
    deployments should use MilvusVectorStore.
    """

    def __init__(self, collection_name: str, **kwargs):
        if not _QDRANT_AVAILABLE:
            raise VectorStoreError(
                "qdrant-client is required for QdrantVectorStore. "
                "Install with: pip install qdrant-client"
            )
        self._init_kwargs = kwargs
        # Attempt to reuse a shared Qdrant client when the same connection
        # parameters are used multiple times.
        try:
            key = tuple(sorted((k, str(v)) for k, v in self._init_kwargs.items()))
        except Exception:
            key = tuple(sorted(list(self._init_kwargs.items())))
        cached = _qdrant_clients.get(key)
        if cached is not None:
            self.client = cached
        else:
            client = qdrant_client.QdrantClient(**self._init_kwargs)
            _qdrant_clients[key] = client
            self.client = client
        self.collection_name = collection_name

    @property
    def is_on_disk(self) -> bool:
        """Checks if the Qdrant client is using on-disk storage."""
        if "url" in self._init_kwargs or "host" in self._init_kwargs:
            return False
        path = self._init_kwargs.get("path")
        location = self._init_kwargs.get("location")
        return path is not None and path != ":memory:" and location != ":memory:"

    def setup(self, vector_dim: int, namespace: str):
        """Set up the collection with the required schema."""
        self.collection_name = namespace
        try:
            exists = False
            if hasattr(self.client, "collection_exists"):
                exists = bool(self.client.collection_exists(self.collection_name))
            else:
                try:
                    self.client.get_collection(collection_name=self.collection_name)
                    exists = True
                except Exception:
                    exists = False

            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
                )
        except Exception:
            pass

    def upsert(self, points: list[dict[str, Any]]):
        """Insert or update vectors in the collection."""
        point_structs = [
            PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points
        ]
        self.client.upsert(collection_name=self.collection_name, wait=True, points=point_structs)

    def search(self, vector: list[float], top_k: int) -> list[Any]:
        """Search for similar vectors."""
        try:
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=vector,
                    limit=top_k,
                    with_payload=True,
                )
                points = getattr(response, "points", response)
                return points
        except Exception:
            pass
        return self.client.search(
            collection_name=self.collection_name, query_vector=vector, limit=top_k
        )

    def delete(self, ids: list[str]):
        """Delete vectors by their IDs."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=[i for i in ids if i]),
            wait=True,
        )

    def scroll(self) -> Iterator[Any]:
        """Iterate over all vectors in the collection."""
        _lim = 100
        records, next_page_offset = self.client.scroll(
            collection_name=self.collection_name,
            limit=_lim,
            with_payload=True,
            with_vectors=True,
        )
        while records:
            yield from records
            if next_page_offset is None:
                break
            records, next_page_offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=_lim,
                with_payload=True,
                offset=next_page_offset,
            )

    def health_check(self) -> bool:
        """Check if the Qdrant connection is healthy."""
        try:
            self.client.get_collection(collection_name=self.collection_name)
            return True
        except Exception:
            return False
