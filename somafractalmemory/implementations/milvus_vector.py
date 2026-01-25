"""
SomaFractalMemory - Milvus Vector Store Implementation
Copyright (C) 2025 SomaTech LAT.

Provides vector similarity search using Milvus 2.3+.
Core component of the FNOM memory retrieval pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class MilvusVectorStore:
    """Milvus-backed vector store for semantic search.

    Stores and retrieves vectors using Milvus for fast ANN search.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: str | int = "19530",
        collection_name: str = "soma_memory",
        dim: int = 768,
    ):
        """Initialize Milvus connection.

        Args:
            host: Milvus server host
            port: Milvus server port
            collection_name: Name of the Milvus collection
            dim: Vector dimension
        """
        self.host = host
        self.port = int(port)
        self.collection_name = collection_name
        self.dim = dim
        self._client: Any | None = None
        self._collection: Any | None = None

    def _ensure_connection(self) -> None:
        """Ensure Milvus connection is established."""
        if self._client is not None:
            return

        try:
            from pymilvus import Collection, connections, utility

            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
            )

            if utility.has_collection(self.collection_name):
                self._collection = Collection(self.collection_name)
                self._collection.load()
            else:
                self._create_collection()

            self._client = connections
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")

        except ImportError:
            logger.error("pymilvus not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise

    def _create_collection(self) -> None:
        """Create the Milvus collection if it doesn't exist."""
        from pymilvus import (
            Collection,
            CollectionSchema,
            DataType,
            FieldSchema,
        )

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="coordinate_key", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="namespace", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="tenant", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
        ]

        schema = CollectionSchema(fields=fields, description="SomaFractalMemory vectors")
        self._collection = Collection(name=self.collection_name, schema=schema)

        # Create IVF_FLAT index for vector field
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        }
        self._collection.create_index(field_name="vector", index_params=index_params)
        self._collection.load()

        logger.info(f"Created Milvus collection: {self.collection_name}")

    def insert(
        self,
        coordinate_key: str,
        vector: list[float] | np.ndarray,
        namespace: str = "default",
        tenant: str = "default",
    ) -> int:
        """Insert a vector into Milvus.

        Args:
            coordinate_key: Unique key for the vector
            vector: The embedding vector
            namespace: Memory namespace
            tenant: Tenant ID

        Returns:
            The Milvus ID of the inserted vector
        """
        self._ensure_connection()

        if isinstance(vector, np.ndarray):
            vector = vector.tolist()

        # Pad or truncate to correct dimension
        if len(vector) < self.dim:
            vector = vector + [0.0] * (self.dim - len(vector))
        elif len(vector) > self.dim:
            vector = vector[: self.dim]

        data = [
            [coordinate_key],  # coordinate_key
            [namespace],  # namespace
            [tenant],  # tenant
            [vector],  # vector
        ]

        result = self._collection.insert(data)
        self._collection.flush()

        return result.primary_keys[0]

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

        # Pad or truncate
        if len(query_vector) < self.dim:
            query_vector = query_vector + [0.0] * (self.dim - len(query_vector))
        elif len(query_vector) > self.dim:
            query_vector = query_vector[: self.dim]

        search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}

        # Build filter expression
        expr_parts = []
        if namespace:
            expr_parts.append(f'namespace == "{namespace}"')
        if tenant:
            expr_parts.append(f'tenant == "{tenant}"')
        expr = " && ".join(expr_parts) if expr_parts else None

        results = self._collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["coordinate_key", "namespace", "tenant"],
        )

        output = []
        for hits in results:
            for hit in hits:
                output.append(
                    {
                        "id": hit.id,
                        "coordinate_key": hit.entity.get("coordinate_key"),
                        "namespace": hit.entity.get("namespace"),
                        "tenant": hit.entity.get("tenant"),
                        "score": hit.score,
                    }
                )

        return output

    def delete(self, coordinate_key: str) -> bool:
        """Delete a vector by coordinate key.

        Args:
            coordinate_key: The coordinate key to delete

        Returns:
            True if deleted, False otherwise
        """
        self._ensure_connection()

        expr = f'coordinate_key == "{coordinate_key}"'
        self._collection.delete(expr)
        return True

    def health_check(self) -> bool:
        """Check if Milvus is healthy."""
        try:
            self._ensure_connection()
            return self._collection is not None
        except Exception:
            return False
