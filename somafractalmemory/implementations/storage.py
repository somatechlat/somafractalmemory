"""
Storage implementations for SomaFractalMemory.

This module serves as a re-export layer for backward compatibility.
All implementations have been decomposed into separate modules:

- postgres_kv.py: PostgresKeyValueStore
- redis_kv.py: RedisKeyValueStore, PostgresRedisHybridStore
- milvus_vector.py: MilvusVectorStore (Qdrant removed per architecture decision)
- batched_store.py: BatchedStore

Import from this module for backward compatibility, or import directly
from the specific modules for cleaner dependencies.
"""

# Re-export all storage implementations for backward compatibility
from somafractalmemory.implementations.batched_store import BatchedStore
from somafractalmemory.implementations.milvus_vector import MilvusVectorStore
from somafractalmemory.implementations.postgres_kv import PostgresKeyValueStore
from somafractalmemory.implementations.redis_kv import (
    PostgresRedisHybridStore,
    RedisKeyValueStore,
)

__all__ = [
    "RedisKeyValueStore",
    "PostgresRedisHybridStore",
    "MilvusVectorStore",
    "BatchedStore",
    "PostgresKeyValueStore",
]
