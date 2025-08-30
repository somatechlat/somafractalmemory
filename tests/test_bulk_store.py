import json
import pytest
from somafractalmemory.core import MemoryType
from somafractalmemory.factory import create_memory_system, MemoryMode


def test_store_memories_bulk_core(tmp_path):
    mem = create_memory_system(MemoryMode.LOCAL_AGENT, "bulk_core", config={"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "q.db")}})
    items = [
        ((1,1,1), {"d": 1}, MemoryType.EPISODIC),
        ((2,2,2), {"f": 2}, MemoryType.SEMANTIC),
    ]
    mem.store_memories_bulk(items)
    all_mems = mem.get_all_memories()
    assert len(all_mems) >= 2


def test_cli_store_bulk(tmp_path, capsys):
    from somafractalmemory import cli
    from somafractalmemory.factory import create_memory_system, MemoryMode
    shared_mem = create_memory_system(MemoryMode.LOCAL_AGENT, "cli_bulk", config={"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "bulk_shared.db")}})
    cli.create_memory_system = lambda *a, **k: shared_mem

    data = [
        {"coord": "1,1,1", "payload": {"d": 1}, "type": "episodic"},
        {"coord": "2,2,2", "payload": {"f": 2}, "type": "semantic"},
    ]
    fpath = tmp_path / "items.json"
    fpath.write_text(json.dumps(data))

    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "bulk_cli.db")}}))

    cli.sys = __import__('sys')
    cli.sys.argv = [
        "soma", "--mode", "local_agent", "--namespace", "cli_bulk", "--config-json", str(cfg_path),
        "store-bulk", "--file", str(fpath)
    ]
    cli.main()
    out = capsys.readouterr().out.strip().splitlines()
    import json as _json
    resp = _json.loads(out[-1]) if out else {}
    assert resp.get("stored") == 2

