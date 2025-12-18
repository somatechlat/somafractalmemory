import os
import uuid

import pytest

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


def _get_test_config():
    """Get test configuration from environment variables."""
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", "40022"))
    milvus_host = os.environ.get("SOMA_MILVUS_HOST", "localhost")
    milvus_port = int(os.environ.get("SOMA_MILVUS_PORT", "35003"))
    postgres_url = os.environ.get(
        "POSTGRES_URL", "postgresql://soma:soma@localhost:40021/somamemory"
    )
    return {
        "redis": {"host": redis_host, "port": redis_port},
        "milvus": {"host": milvus_host, "port": milvus_port},
        "postgres": {"url": postgres_url},
    }


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    # Use unique namespace per test run to avoid leftover data
    namespace = f"stats_test_{uuid.uuid4().hex[:8]}"
    config = _get_test_config()
    return create_memory_system(MemoryMode.EVENTED_ENTERPRISE, namespace, config=config)


def test_memory_stats_counts(mem: SomaFractalMemoryEnterprise):
    """Test basic memory statistics counting."""
    # Initially empty
    assert mem.memory_stats()["total_memories"] == 0

    # Store different types of memories
    c1, c2, c3 = (1, 1, 1), (2, 2, 2), (3, 3, 3)
    mem.store_memory(c1, {"content": "episodic memory 1"}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(c2, {"content": "episodic memory 2"}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(c3, {"content": "semantic memory"}, memory_type=MemoryType.SEMANTIC)

    # Verify counts
    stats = mem.memory_stats()
    assert stats["total_memories"] >= 3
    assert stats["episodic"] >= 2
    assert stats["semantic"] >= 1
