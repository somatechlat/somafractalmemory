import pytest

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def test_encryption_roundtrip_if_available(tmp_path):
    crypt = pytest.importorskip("cryptography.fernet")
    key = crypt.Fernet.generate_key()
    mem = create_memory_system(
        MemoryMode.LOCAL_AGENT,
        "enc_ns",
        config={
            "redis": {"testing": True},
            "qdrant": {"path": str(tmp_path / "q.db")},
            "memory_enterprise": {"vector_dim": 64},
        },
    )
    # Inject cipher into instance (simulate enterprise config with key)
    mem.cipher = crypt.Fernet(key)
    coord = (9, 9, 9)
    mem.store_memory(
        coord, {"task": "secret-task", "code": "print(1)"}, memory_type=MemoryType.EPISODIC
    )
    out = mem.retrieve(coord)
    assert out is not None
    # Retrieved values should be decrypted
    assert out.get("task") == "secret-task"
    assert out.get("code") == "print(1)"
