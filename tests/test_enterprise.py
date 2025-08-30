import pytest
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import SomaFractalMemoryEnterprise

def test_init(tmp_path):
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True}
    }
    instance = create_memory_system(MemoryMode.LOCAL_AGENT, "soma_enterprise", config=config)
    assert isinstance(instance, SomaFractalMemoryEnterprise)
