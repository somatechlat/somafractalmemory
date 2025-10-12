import json


def test_cli_path(tmp_path, capsys):
    # Three steps: store two, link, then path. Use distinct qdrant paths to avoid local lock contention
    from somafractalmemory import cli
    from somafractalmemory.factory import MemoryMode, create_memory_system

    # Create a shared memory instance and monkeypatch the CLI factory to reuse it
    shared_mem = create_memory_system(
        MemoryMode.EVENTED_ENTERPRISE,
        "cli_path",
        config={"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "qp_shared.db")}},
    )
    cli.create_memory_system = lambda *a, **k: shared_mem
    cfg_path = tmp_path / "cfg.json"

    # Store nodes via CLI using the shared mem
    for idx, coord in enumerate(("1,1,1", "2,2,2"), start=1):
        cfg_path.write_text(
            json.dumps(
                {"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / f"qp_{idx}.db")}}
            )
        )
        cli.sys = __import__("sys")
        cli.sys.argv = [
            "soma",
            "--mode",
            "evented_enterprise",
            "--namespace",
            "cli_path",
            "--config-json",
            str(cfg_path),
            "store",
            "--coord",
            coord,
            "--payload",
            '{"d":1}',
            "--type",
            "episodic",
        ]
        cli.main()
        _ = capsys.readouterr()  # drain

    # Link
    cfg_path.write_text(
        json.dumps({"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "qp_link.db")}})
    )
    cli.sys.argv = [
        "soma",
        "--mode",
        "evented_enterprise",
        "--namespace",
        "cli_path",
        "--config-json",
        str(cfg_path),
        "link",
        "--from",
        "1,1,1",
        "--to",
        "2,2,2",
        "--type",
        "related",
    ]
    cli.main()
    _ = capsys.readouterr()

    # Path
    cfg_path.write_text(
        json.dumps({"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "qp_path.db")}})
    )
    cli.sys.argv = [
        "soma",
        "--mode",
        "evented_enterprise",
        "--namespace",
        "cli_path",
        "--config-json",
        str(cfg_path),
        "path",
        "--from",
        "1,1,1",
        "--to",
        "2,2,2",
    ]
    cli.main()
    out = capsys.readouterr().out.strip().splitlines()
    data = json.loads(out[-1]) if out else []
    assert data == [[1.0, 1.0, 1.0], [2.0, 2.0, 2.0]]
