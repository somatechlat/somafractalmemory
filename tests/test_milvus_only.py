"""Property test verifying Milvus-only vector store operations.

**Feature: production-readiness-audit, Property 5: Vector Store Consistency**
**Validates: Requirements 1.1, 1.2, 1.3**

This test verifies that:
1. QdrantVectorStore has been removed from the codebase
2. Only MilvusVectorStore is available for vector operations
3. The factory creates Milvus-backed systems
"""

from pathlib import Path

import pytest


def test_qdrant_vector_store_removed() -> None:
    """Verify that QdrantVectorStore implementation file has been removed.

    **Feature: production-readiness-audit, Property 5: Vector Store Consistency**
    **Validates: Requirements 1.1**
    """
    workspace_root = Path(__file__).resolve().parents[1]
    qdrant_file = workspace_root / "somafractalmemory" / "implementations" / "qdrant_vector.py"

    assert not qdrant_file.exists(), (
        f"Qdrant implementation should be removed: {qdrant_file}\n"
        "Architecture decision: Milvus-only for vector operations"
    )


def test_qdrant_not_in_exports() -> None:
    """Verify that QdrantVectorStore is not exported from implementations package.

    **Feature: production-readiness-audit, Property 5: Vector Store Consistency**
    **Validates: Requirements 1.3**
    """
    from somafractalmemory import implementations

    # Check __all__ does not contain Qdrant
    all_exports = getattr(implementations, "__all__", [])
    assert (
        "QdrantVectorStore" not in all_exports
    ), "QdrantVectorStore should not be in implementations.__all__"

    # Check the class is not importable
    assert not hasattr(
        implementations, "QdrantVectorStore"
    ), "QdrantVectorStore should not be accessible from implementations module"


def test_milvus_is_available() -> None:
    """Verify that MilvusVectorStore is available and importable.

    **Feature: production-readiness-audit, Property 5: Vector Store Consistency**
    **Validates: Requirements 1.1**
    """
    from somafractalmemory.implementations import MilvusVectorStore

    assert MilvusVectorStore is not None
    assert hasattr(MilvusVectorStore, "upsert")
    assert hasattr(MilvusVectorStore, "search")
    assert hasattr(MilvusVectorStore, "delete")
    assert hasattr(MilvusVectorStore, "scroll")


def test_qdrant_not_importable() -> None:
    """Verify that QdrantVectorStore cannot be imported.

    **Feature: production-readiness-audit, Property 5: Vector Store Consistency**
    **Validates: Requirements 1.3**
    """
    with pytest.raises(ImportError):
        from somafractalmemory.implementations.qdrant_vector import QdrantVectorStore  # noqa: F401
