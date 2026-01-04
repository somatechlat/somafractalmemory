"""Module test_delete_idempotent."""

import pytest

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    # Use the real Redis service (hosted by Docker compose) instead of the fakeredis testing shim.
    """Execute mem.

    Args:
        tmp_path: The tmp_path.
    """

    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"host": "localhost", "port": 40022},
    }
    return create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "idempotent_ns", config=config)


def test_delete_idempotent(mem: SomaFractalMemoryEnterprise):
    """Execute test delete idempotent.

    Args:
        mem: The mem.
    """

    coord = (10, 10, 10)
    mem.store_memory(coord, {"d": 1})
    assert mem.retrieve(coord) is not None
    # First delete
    mem.delete(coord)
    assert mem.retrieve(coord) is None
    # Second delete should not raise
    mem.delete(coord)
    assert mem.retrieve(coord) is None
