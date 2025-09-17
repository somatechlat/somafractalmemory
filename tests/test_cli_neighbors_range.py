import json


def test_cli_neighbors_and_range(tmp_path, capsys):
    from somafractalmemory import cli
    from somafractalmemory.factory import MemoryMode, create_memory_system

    # Use one shared memory instance for all CLI calls to avoid qdrant local locks
    shared_mem = create_memory_system(MemoryMode.LOCAL_AGENT, "cli_nr", config={
        "redis": {"testing": True},
        "qdrant": {"path": str(tmp_path / "nr.db")},
    })
    cli.create_memory_system = lambda *a, **k: shared_mem

    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "nr.cfg.db")}}))

    # Store three nodes
    cli.sys = __import__('sys')
    for coord in ("0,0,0", "1,1,1", "2,2,2"):
        cli.sys.argv = [
            "soma", "--mode", "local_agent", "--namespace", "cli_nr", "--config-json", str(cfg_path),
            "store", "--coord", coord, "--payload", "{\"d\":1}", "--type", "episodic"
        ]
        cli.main()
        _ = capsys.readouterr()

    # Link 0->1 as related; 1->2 as unrelated
    cli.sys.argv = [
        "soma", "--mode", "local_agent", "--namespace", "cli_nr", "--config-json", str(cfg_path),
        "link", "--from", "0,0,0", "--to", "1,1,1", "--type", "related"
    ]
    cli.main(); _ = capsys.readouterr()
    cli.sys.argv = [
        "soma", "--mode", "local_agent", "--namespace", "cli_nr", "--config-json", str(cfg_path),
        "link", "--from", "1,1,1", "--to", "2,2,2", "--type", "unrelated"
    ]
    cli.main(); _ = capsys.readouterr()

    # neighbors for 0,0,0 should include 1,1,1
    cli.sys.argv = [
        "soma", "--mode", "local_agent", "--namespace", "cli_nr", "--config-json", str(cfg_path),
        "neighbors", "--coord", "0,0,0"
    ]
    cli.main()
    out = capsys.readouterr().out.strip().splitlines()
    nbrs = json.loads(out[-1]) if out else []
    assert [1.0,1.0,1.0] in nbrs

    # range search for [1,1,1]..[2,2,2]
    cli.sys.argv = [
        "soma", "--mode", "local_agent", "--namespace", "cli_nr", "--config-json", str(cfg_path),
        "range", "--min", "1,1,1", "--max", "2,2,2"
    ]
    cli.main()
    out = capsys.readouterr().out.strip().splitlines()
    coords = json.loads(out[-1]) if out else []
    assert [1.0,1.0,1.0] in coords and [2.0,2.0,2.0] in coords

