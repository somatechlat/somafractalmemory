import os

import pytest

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system

# Skip if infrastructure is not available
pytestmark = pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure (Milvus, Redis, Postgres)",
)


def test_store_memories_bulk_core(tmp_path):
    """Test bulk storage of multiple memories.

    Uses real Redis and Milvus services (Qdrant removed per architecture decision).
    """
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    milvus_host = os.environ.get("SOMA_MILVUS_HOST", "localhost")
    milvus_port = int(os.environ.get("SOMA_MILVUS_PORT", 19530))

    mem = create_memory_system(
        MemoryMode.EVENTED_ENTERPRISE,
        "bulk_core",
        config={
            "redis": {"host": "localhost", "port": redis_port},
            "milvus": {"host": milvus_host, "port": milvus_port},
        },
    )
    items = [
        ((1, 1, 1), {"content": "first memory"}, MemoryType.EPISODIC),
        ((2, 2, 2), {"content": "second memory"}, MemoryType.SEMANTIC),
    ]
    mem.store_memories_bulk(items)

    # Verify stored memories
    first = mem.retrieve((1, 1, 1))
    second = mem.retrieve((2, 2, 2))
    assert first is not None
    assert second is not None
    assert first["content"] == "first memory"
    assert second["content"] == "second memory"
