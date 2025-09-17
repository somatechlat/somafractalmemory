import json
import sys
from pathlib import Path


def run_cli(tmp_path: Path, args, qdrant_subdir: str = "qdrant.db"):
    # Build a minimal config JSON for the CLI
    cfg = {
        "redis": {"testing": True},
        "qdrant": {"path": str(tmp_path / qdrant_subdir)},
    }
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg))

    sys.argv = [
        "soma",
        "--mode",
        "local_agent",
        "--namespace",
        "cli_ns",
        "--config-json",
        str(cfg_path),
    ] + args
    from somafractalmemory import cli

    # Execute CLI main; capture prints via capsys in the tests
    cli.main()
    # Ensure Qdrant local client releases file locks between invocations
    import gc

    gc.collect()


def test_cli_store_and_recall(tmp_path, capsys):
    # Store
    run_cli(
        tmp_path,
        ["store", "--coord", "1,2,3", "--payload", '{"d":1}', "--type", "episodic"],
        qdrant_subdir="q1.db",
    )
    out = capsys.readouterr().out
    assert "OK" in out

    # Recall
    run_cli(tmp_path, ["recall", "--query", "1", "--top-k", "1"], qdrant_subdir="q2.db")
    out = capsys.readouterr().out
    # Output is JSON list; ensure it is well-formed
    data = json.loads(out)
    assert isinstance(data, list)

    # Stats
    run_cli(tmp_path, ["stats"], qdrant_subdir="q3.db")
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, dict)
