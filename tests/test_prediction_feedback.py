from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def test_report_outcome_without_prediction(tmp_path):
    cfg = {
        "qdrant": {"path": str(tmp_path / "q.db")},
        "redis": {"testing": True},
    }
    mem = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "pred_ns", config=cfg)
    coord = (1, 2, 3)
    mem.store_memory(coord, {"task": "bar"}, memory_type=MemoryType.EPISODIC)
    stored = mem.retrieve(coord)
    assert stored is not None
    assert "predicted_outcome" not in stored

    result = mem.report_outcome(coord, outcome="bar")
    assert result.get("error") is False
    semantics = mem.retrieve_memories(MemoryType.SEMANTIC)
    assert all("corrective_for" not in s for s in semantics)
