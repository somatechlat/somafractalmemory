import json
from pathlib import Path

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def test_export_import_jsonl(tmp_path: Path):
    cfg1 = {"qdrant": {"path": str(tmp_path / "q1.db")}, "redis": {"testing": True}}
    cfg2 = {"qdrant": {"path": str(tmp_path / "q2.db")}, "redis": {"testing": True}}

    m1 = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "ns_export", config=cfg1)
    c = (1.0, 2.0, 3.0)
    m1.store_memory(c, {"task": "export me", "importance": 3}, memory_type=MemoryType.EPISODIC)
    out = tmp_path / "mem.jsonl"
    n = m1.export_memories(str(out))
    assert n >= 1 and out.exists()

    # Read file sanity
    line = out.read_text().strip().splitlines()[0]
    rec = json.loads(line)
    assert rec.get("task") == "export me"

    # Import into separate instance
    m2 = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "ns_import", config=cfg2)
    imported = m2.import_memories(str(out), replace=True)
    assert imported >= 1
    got = m2.retrieve(c)
    assert got is not None
    assert got.get("task") == "export me"
