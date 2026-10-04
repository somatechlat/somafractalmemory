"""
SomaFractalMemory - Milvus Vector Store Implementation
Copyright (C) 2025 SomaTech LAT.

Provides vector similarity search using Milvus 2.3+ via MilvusClient
(the supported API — ORM-style Collection/connections is deprecated).
Core component of the FNOM memory retrieval pipeline.

Topology (host/port), connect timeout, distance metric and IVF index shape
come from the settings model. No call site names a URL or a magic number.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from somafractalmemory.settings.model import milvus_uri, resolve_setting

logger = logging.getLogger(__name__)

# Milvus metric_type spelling is uppercase; the settings model names the
# metric in lowercase (cosine|ip|l2) because that is how operators write it.
_METRIC_ALIASES = {"cosine": "COSINE", "ip": "IP", "l2": "L2"}


class MilvusVectorStore:
    """Milvus-backed vector store for semantic search.

    Stores and retrieves vectors using Milvus for fast ANN search.
    """

    def __init__(self, collection_name: str, dim: int):
        """Initialize Milvus connection.

        Args:
            collection_name: Name of the Milvus collection
            dim: Vector dimension (must match SOMA_VECTOR_DIM / MEM_EMBED_DIM)
        """
        self.collection_name = collection_name
        self.dim = int(dim)
        self._client: Any | None = None

    def _metric_type(self) -> str:
        """Resolve the Milvus distance metric from settings (fail-closed)."""
        raw = str(resolve_setting("SOMA_SIMILARITY_METRIC")).strip().lower()
        metric = _METRIC_ALIASES.get(raw)
        if metric is None:
            raise ValueError(
                f"SOMA_SIMILARITY_METRIC={raw!r} is not a Milvus metric "
                "(cosine|ip|l2). VIBE Rule 91: an unknown metric is not "
                "permission to invent one."
            )
        return metric

    def _ensure_connection(self) -> None:
        """Ensure MilvusClient connection is established."""
        if self._client is not None:
            return

        try:
            from pymilvus import MilvusClient

            uri = milvus_uri()
            self._client = MilvusClient(
                uri=uri,
                timeout=float(resolve_setting("SOMA_MILVUS_TIMEOUT_S")),
            )
            if self._client.has_collection(self.collection_name):
                self._assert_dimension()
            else:
                self._create_collection()
            logger.info(f"Connected to Milvus at {uri}")
        except ImportError:
            logger.error("pymilvus not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            self._client = None
            raise

    def _describe_fields(self) -> list[dict[str, Any]]:
        """Return schema field dicts for this store's collection."""
        try:
            desc = self._client.describe_collection(self.collection_name)
            return list(desc.get("fields") or [])
        except Exception:
            return []

    def _assert_dimension(self) -> None:
        """Fail loudly when an existing collection's vector dim is not ``self.dim``.

        Milvus collections are fixed-dim at creation. Accepting a collection
        built for another dimension is not a soft mismatch: every insert and
        search then dies inside Milvus with a ``field_meta.get_sizeof()``
        assertion, and the service silently falls back to ORM text search —
        so recall returns exact-text-only hits scored 0.0 and looks merely
        "weak" instead of broken. Refusing here surfaces the real problem.
        """
        stored = None
        for field in self._describe_fields():
            if field.get("name") == "vector":
                params = field.get("params") or {}
                stored = params.get("dim")
                break
        if stored is not None and int(stored) != int(self.dim):
            raise ValueError(
                f"Milvus collection {self.collection_name!r} has vector dim {stored}, "
                f"but this writer expects {self.dim} (SOMA_VECTOR_DIM / MEM_EMBED_DIM). "
                f"Migrate the collection to dim {self.dim} — do not write into a "
                f"mismatched one."
            )

    def _create_collection(self) -> None:
        """Create the Milvus collection if it doesn't exist."""
        from pymilvus import DataType, MilvusClient

        schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field("coordinate_key", DataType.VARCHAR, max_length=512)
        schema.add_field("namespace", DataType.VARCHAR, max_length=255)
        schema.add_field("tenant", DataType.VARCHAR, max_length=255)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=self.dim)

        index_params = MilvusClient.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="IVF_FLAT",
            metric_type=self._metric_type(),
            params={"nlist": int(resolve_setting("SOMA_MILVUS_NLIST"))},
        )

        self._client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        logger.info(f"Created Milvus collection: {self.collection_name}")

    def insert(
        self,
        coordinate_key: str,
        vector: list[float] | np.ndarray,
        namespace: str = "default",
        tenant: str = "default",
    ) -> Any:
        """Insert a vector into Milvus.

        Args:
            coordinate_key: Unique key for the vector
            vector: The embedding vector
            namespace: Memory namespace
            tenant: Tenant ID

        Returns:
            The Milvus insert result (primary keys).
        """
        self._ensure_connection()

        if isinstance(vector, np.ndarray):
            vector = vector.tolist()

        # Strict dimension check - NO silent padding or truncation (Flaw 5 Fix)
        if len(vector) != self.dim:
            raise ValueError(
                f"Vector dimension mismatch. Expected {self.dim}, got {len(vector)}. "
                "Padding/truncation is prohibited for semantic integrity."
            )

        row = {
            "coordinate_key": coordinate_key,
            "namespace": namespace,
            "tenant": tenant,
            "vector": vector,
        }
        result = self._client.insert(
            collection_name=self.collection_name,
            data=[row],
        )
        # Flush is deferred — collection.flush() after every insert serializes
        # writes and adds multi-100ms latency on the hot path. Milvus flushes
        # on interval / growing-segment pressure.
        return result

    def search(
        self,
        query_vector: list[float] | np.ndarray,
        top_k: int = 10,
        namespace: str | None = None,
        tenant: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors.

        Args:
            query_vector: Query embedding
            top_k: Number of results to return
            namespace: Filter by namespace
            tenant: Filter by tenant

        Returns:
            List of results with id, coordinate_key, score
        """
        self._ensure_connection()

        if isinstance(query_vector, np.ndarray):
            query_vector = query_vector.tolist()

        # Strict dimension check (Flaw 5 Fix)
        if len(query_vector) != self.dim:
            raise ValueError(
                f"Query vector dimension mismatch. Expected {self.dim}, got {len(query_vector)}"
            )

        expr_parts = []
        if namespace:
            expr_parts.append(f'namespace == "{namespace}"')
        if tenant:
            expr_parts.append(f'tenant == "{tenant}"')
        expr = " && ".join(expr_parts) if expr_parts else ""

        results = self._client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            anns_field="vector",
            search_params={
                "metric_type": self._metric_type(),
                "params": {"nprobe": int(resolve_setting("SOMA_MILVUS_NPROBE"))},
            },
            limit=max(1, int(top_k)),
            filter=expr or None,
            output_fields=["coordinate_key", "namespace", "tenant"],
        )

        output: list[dict[str, Any]] = []
        for hits in results or []:
            for hit in hits:
                entity = hit.get("entity") or {}
                output.append(
                    {
                        "id": hit.get("id"),
                        "coordinate_key": entity.get("coordinate_key"),
                        "namespace": entity.get("namespace"),
                        "tenant": entity.get("tenant"),
                        "score": hit.get("distance", hit.get("score")),
                    }
                )
        return output

    def delete(
        self, coordinate_key: str, namespace: str = "default", tenant: str = "default"
    ) -> bool:
        """Delete a vector by coordinate key with strict tenant/namespace filtering.

        Args:
            coordinate_key: The coordinate key to delete
            namespace: Memory namespace
            tenant: Tenant ID

        Returns:
            True if deleted, False otherwise
        """
        self._ensure_connection()

        expr = f'coordinate_key == "{coordinate_key}" && namespace == "{namespace}" && tenant == "{tenant}"'
        self._client.delete(collection_name=self.collection_name, filter=expr)
        return True

    def health_check(self) -> bool:
        """Check if Milvus is healthy."""
        try:
            self._ensure_connection()
            return self._client is not None
        except Exception:
            return False
