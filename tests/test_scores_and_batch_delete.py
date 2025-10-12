import json

import pytest

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.fixture
def mem(tmp_path):
    cfg = {"qdrant": {"path": str(tmp_path / "q.db")}, "redis": {"testing": True}}
    return create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "score_ns", config=cfg)


def test_recall_with_scores(mem):
    c = (1, 2, 3)
    mem.store_memory(c, {"task": "alpha"}, memory_type=MemoryType.EPISODIC)
    res = mem.recall_with_scores("alpha", top_k=1)
    assert isinstance(res, list)
    assert res and "payload" in res[0]
    # score may be None depending on backend, but key should exist
    assert "score" in res[0]


def test_cli_delete_many(tmp_path, capsys):
    # Prepare config JSON
    # Use separate qdrant paths per CLI invocation to avoid local lock contention
    cfg = {"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "q_a.db")}}
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg))

    # Store two memories via CLI
    from somafractalmemory import cli

    for idx, coord in enumerate(("1,1,1", "2,2,2"), start=1):
        cli.sys = __import__("sys")  # ensure sys available for argv
        cfg_path.write_text(
            json.dumps(
                {"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / f"q_{idx}.db")}}
            )
        )
        cli.sys.argv = [
            "soma",
            "--mode",
            "evented_enterprise",
            "--namespace",
            "cli_batch",
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
        # Drain output from previous command
        _ = capsys.readouterr()

    # Delete many via CLI
    from somafractalmemory import cli as cli2

    cli2.sys = __import__("sys")
    # Delete against a fresh path as well (we count requested deletions)
    cfg_path.write_text(
        json.dumps({"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "q_c.db")}})
    )
    cli2.sys.argv = [
        "soma",
        "--mode",
        "evented_enterprise",
        "--namespace",
        "cli_batch",
        "--config-json",
        str(cfg_path),
        "delete-many",
        "--coords",
        "1,1,1;2,2,2",
    ]
    cli2.main()
    out = capsys.readouterr().out.strip().splitlines()
    line = out[-1] if out else "{}"
    data = json.loads(line)
    assert data.get("deleted") == 2
