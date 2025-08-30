import json


def test_cli_export_import_shared_mem(tmp_path, capsys):
    from somafractalmemory import cli
    from somafractalmemory.factory import create_memory_system, MemoryMode
    # Use one shared memory instance behind CLI to avoid local qdrant lock issues
    shared_mem = create_memory_system(MemoryMode.LOCAL_AGENT, "cli_ei", config={"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "ei.db")}})
    cli.create_memory_system = lambda *a, **k: shared_mem

    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "ei.cfg.db")}}))

    # Store one
    cli.sys = __import__('sys')
    cli.sys.argv = [
        "soma", "--mode", "local_agent", "--namespace", "cli_ei", "--config-json", str(cfg_path),
        "store", "--coord", "1,2,3", "--payload", "{\"d\":1}", "--type", "episodic"
    ]
    cli.main()
    _ = capsys.readouterr()

    # Export
    out_path = tmp_path / "mem.jsonl"
    cli.sys.argv = [
        "soma", "--mode", "local_agent", "--namespace", "cli_ei", "--config-json", str(cfg_path),
        "export-memories", "--path", str(out_path)
    ]
    cli.main()
    out = capsys.readouterr().out.strip().splitlines()
    data = json.loads(out[-1]) if out else {}
    assert data.get("exported", 0) >= 1

    # Import (replace)
    cli.sys.argv = [
        "soma", "--mode", "local_agent", "--namespace", "cli_ei", "--config-json", str(cfg_path),
        "import-memories", "--path", str(out_path), "--replace"
    ]
    cli.main()
    out = capsys.readouterr().out.strip().splitlines()
    data = json.loads(out[-1]) if out else {}
    assert data.get("imported", 0) >= 1

