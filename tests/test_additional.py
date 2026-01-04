"""Module test_additional."""

import pytest

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    # Use real Redis service - configuration comes from environment variables
    # (REDIS_HOST, REDIS_PORT, POSTGRES_URL, SOMA_MILVUS_HOST, SOMA_MILVUS_PORT)
    # No hardcoded Docker hostnames - let factory.py read from env vars
    """Execute mem.

    Args:
        tmp_path: The tmp_path.
    """

    import os

    config = {}
    # Only pass redis config if explicitly set in env (otherwise factory uses env vars)
    redis_host = os.environ.get("REDIS_HOST")
    redis_port = os.environ.get("REDIS_PORT")
    if redis_host:
        config["redis"] = {"host": redis_host, "port": int(redis_port or 6379)}
    return create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "additional_ns", config=config)


def test_delete_removes_memory(mem: SomaFractalMemoryEnterprise):
    """Test that delete operation properly removes stored memory."""
    coord = (9, 9, 9)
    mem.store_memory(coord, {"data": "test_value"})
    assert mem.retrieve(coord) is not None
    mem.delete(coord)
    assert mem.retrieve(coord) is None


def test_basic_memory_persistence(mem: SomaFractalMemoryEnterprise):
    """Test basic memory storage and retrieval persistence."""
    coord = (7, 7, 7)
    payload = {"content": "test data", "importance": 0.5}
    mem.store_memory(coord, payload)
    retrieved = mem.retrieve(coord)
    assert retrieved is not None
    assert retrieved["content"] == "test data"
    assert retrieved["importance"] == 0.5
