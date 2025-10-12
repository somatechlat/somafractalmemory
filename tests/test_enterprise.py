from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


def test_init(tmp_path):
    config = {"qdrant": {"path": str(tmp_path / "qdrant.db")}, "redis": {"testing": True}}
    instance = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "soma_enterprise", config=config)
    assert isinstance(instance, SomaFractalMemoryEnterprise)
