"""
Milvus Vector Store implementation for SomaFractalMemory.

This module provides the production vector backend using Milvus.
All network-related errors are wrapped in VectorStoreError for consistent
error handling across backends.
"""

import logging
from collections.abc import Iterator
from typing import Any

from somafractalmemory.core import VectorStoreError
from somafractalmemory.interfaces.storage import IVectorStore

logger = logging.getLogger(__name__)


class MilvusVectorStore(IVectorStore):
    """Milvus implementation of the vector-store interface.

    The constructor expects a collection name and connection kwargs. The
    `setup` method creates the collection with the required schema if it does
    not already exist.
    """

    def __init__(self, collection_name: str, **kwargs):
        # Import pymilvus - required for Milvus (exclusive vector backend)
        try:
            from pymilvus import Collection, connections, utility
        except ImportError as exc:
            raise VectorStoreError("pymilvus is required for Milvus backend") from exc

        self.collection_name = collection_name
        self._init_kwargs = kwargs
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 19530)
        # Establish a default connection (named "default").
        connections.connect(alias="default", host=host, port=port)
        self._connections = connections
        self._Collection = Collection
        self._utility = utility

    def setup(self, vector_dim: int, namespace: str):
        """Set up the collection with the required schema, index, and load it.

        Milvus requires:
        1. Collection with schema (id, embedding, payload)
        2. Index on the embedding field for similarity search
        3. Collection loaded into memory for queries

        Without all three steps, search operations will fail.
        """
        # Use namespace as collection name if not already set.
        self.collection_name = namespace

        # Check if collection exists; create if missing.
        if not self._utility.has_collection(self.collection_name):
            from pymilvus import CollectionSchema, DataType, FieldSchema

            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=255),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
                FieldSchema(name="payload", dtype=DataType.JSON),
            ]
            schema = CollectionSchema(fields, description="SomaFractalMemory vectors")
            self._Collection(name=self.collection_name, schema=schema)
        else:
            # Verify dimension matches expected size.
            coll = self._Collection(self.collection_name)
            vec_field = next(f for f in coll.schema.fields if f.name == "embedding")
            if vec_field.params.get("dim") != vector_dim:
                raise VectorStoreError(
                    f"Milvus collection dimension {vec_field.params.get('dim')} "
                    f"does not match required {vector_dim}"
                )

        # Ensure index exists on embedding field (required for search)
        coll = self._Collection(self.collection_name)
        if not coll.indexes:
            index_params = {
                "metric_type": "IP",  # Inner Product for cosine similarity on normalized vectors
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128},
            }
            coll.create_index(field_name="embedding", index_params=index_params)

        # Load collection into memory (required for queries)
        try:
            coll.load()
        except Exception as exc:
            # Collection may already be loaded; log at debug level
            logger.debug(
                "Collection load skipped (may already be loaded)",
                extra={"collection": self.collection_name, "error": str(exc)},
            )

    def upsert(self, points: list[dict[str, Any]]):
        """Insert or update vectors in the collection."""
        ids = [p["id"] for p in points]
        vectors = [p["vector"] for p in points]
        payloads = [p["payload"] for p in points]
        coll = self._Collection(self.collection_name)
        try:
            coll.insert([ids, vectors, payloads])
            # Flush to ensure data is persisted and visible to queries
            coll.flush()
        except Exception as exc:
            raise VectorStoreError("Milvus upsert failed") from exc

    def search(self, vector: list[float], top_k: int) -> list[Any]:
        """Search for similar vectors."""
        from pymilvus import SearchParam

        coll = self._Collection(self.collection_name)
        try:
            results = coll.search(
                data=[vector],
                anns_field="embedding",
                param=SearchParam(metric_type="IP", params={"nprobe": 10}),
                limit=top_k,
                expr=None,
                output_fields=["payload"],
            )
            # `results` is a list of lists; flatten.
            return [hit for sublist in results for hit in sublist]
        except Exception as exc:
            raise VectorStoreError("Milvus search failed") from exc

    def delete(self, ids: list[str]):
        """Delete vectors by their primary IDs.

        Modern Milvus SDK versions provide ``delete(ids=...)``. For backward
        compatibility we fall back to the expression-based syntax if the newer
        signature is unavailable.
        """
        if not ids:
            return
        coll = self._Collection(self.collection_name)
        try:
            # Prefer the native ``ids`` argument supported by modern Milvus SDKs.
            # type: ignore[arg-type] - Milvus SDK type stubs don't match runtime behavior
            coll.delete(ids=ids)  # type: ignore[arg-type]
        except Exception:
            # Fallback to expression syntax for legacy clients.
            try:
                ids_quoted = ",".join([f'"{i}"' for i in ids])
                expr = f"id in [{ids_quoted}]"
                coll.delete(expr=expr)
            except Exception as exc:
                raise VectorStoreError("Milvus delete failed") from exc

    def scroll(self) -> Iterator[Any]:
        """Iterate over all vectors in the collection.

        Milvus does not provide a native scroll; emulate with offset pagination.
        """
        coll = self._Collection(self.collection_name)
        batch = 1000
        offset = 0
        while True:
            records = coll.query(
                expr="", output_fields=["id", "embedding", "payload"], limit=batch, offset=offset
            )
            if not records:
                break
            yield from records
            offset += batch

    def count(self) -> int:
        """Return the number of entities in the namespace's collection.

        This method returns the count of vectors stored in the current
        namespace's Milvus collection only, ensuring namespace isolation.

        Note: Milvus requires flush() for num_entities to reflect recent inserts.
        """
        try:
            coll = self._Collection(self.collection_name)
            # Flush to ensure num_entities reflects recent inserts
            try:
                coll.flush()
            except Exception as exc:
                logger.debug(
                    "Flush before count failed",
                    extra={"collection": self.collection_name, "error": str(exc)},
                )
            # Ensure collection is loaded before querying
            try:
                coll.load()
            except Exception as exc:
                # Collection may already be loaded
                logger.debug(
                    "Load before count skipped (may already be loaded)",
                    extra={"collection": self.collection_name, "error": str(exc)},
                )
            return coll.num_entities
        except Exception as exc:
            # Collection may not exist or be accessible
            logger.debug(
                "Count failed, returning 0",
                extra={"collection": self.collection_name, "error": str(exc)},
            )
            return 0

    def health_check(self) -> bool:
        """Check if the Milvus connection is healthy."""
        try:
            return self._utility.has_collection(self.collection_name)
        except Exception as exc:
            logger.debug(
                "Health check failed", extra={"collection": self.collection_name, "error": str(exc)}
            )
            return False
