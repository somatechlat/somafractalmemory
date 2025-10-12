import pytest

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True},
    }
    return create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "idempotent_ns", config=config)


def test_delete_idempotent(mem: SomaFractalMemoryEnterprise):
    coord = (10, 10, 10)
    mem.store_memory(coord, {"d": 1})
    assert mem.retrieve(coord) is not None
    # First delete
    mem.delete(coord)
    assert mem.retrieve(coord) is None
    # Second delete should not raise
    mem.delete(coord)
    assert mem.retrieve(coord) is None
