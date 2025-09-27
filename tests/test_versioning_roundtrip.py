import time

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.implementations.graph import NetworkXGraphStore
from somafractalmemory.implementations.storage import InMemoryVectorStore, RedisKeyValueStore


def make_mem(ns: str = "ver_ns") -> SomaFractalMemoryEnterprise:
    return SomaFractalMemoryEnterprise(
        namespace=ns,
        kv_store=RedisKeyValueStore(testing=True),
        vector_store=InMemoryVectorStore(),
        graph_store=NetworkXGraphStore(),
        decay_enabled=False,
        reconcile_enabled=False,
    )


def test_versioning_roundtrip():
    mem = make_mem()
    c = (1.0, 2.0, 3.0)
    mem.store_memory(c, {"task": "a", "importance": 1}, memory_type=MemoryType.EPISODIC)
    mem.save_version(c)
    # mutate and save another version
    mem.store_memory(c, {"task": "b", "importance": 2}, memory_type=MemoryType.EPISODIC)
    time.sleep(0.01)
    mem.save_version(c)
    versions = mem.get_versions(c)
    assert isinstance(versions, list) and len(versions) >= 2
    # Latest stored payload should reflect last store
    cur = mem.retrieve(c)
    assert cur is not None and cur.get("task") == "b"
