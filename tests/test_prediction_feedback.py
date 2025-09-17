from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


class StubPredictor:
    def __init__(self, value="foo", conf=0.9):
        self.value = value
        self.conf = conf

    def predict(self, memory_data):
        return self.value, self.conf

    def health_check(self):
        return True


def test_prediction_enrichment_and_feedback(tmp_path):
    cfg = {
        "qdrant": {"path": str(tmp_path / "q.db")},
        "redis": {"testing": True},
        "memory_enterprise": {"predictions": {"enabled": True, "error_policy": "exact"}},
    }
    mem = create_memory_system(MemoryMode.LOCAL_AGENT, "pred_ns", config=cfg)
    # Swap in a stub predictor for determinism
    mem.prediction_provider = StubPredictor(value="foo", conf=0.9)

    coord = (1, 2, 3)
    mem.store_memory(coord, {"task": "bar"}, memory_type=MemoryType.EPISODIC)
    stored = mem.retrieve(coord)
    assert stored is not None
    assert stored.get("predicted_outcome") == "foo"
    assert isinstance(stored.get("predicted_confidence"), float)

    # Report an outcome that differs to trigger correction
    result = mem.report_outcome(coord, outcome="bar")
    assert result.get("error") is True
    # Importance lowered (may be absent if not set initially, so just ensure no error)
    # A corrective semantic memory should have been created
    semantics = mem.retrieve_memories(MemoryType.SEMANTIC)
    assert any("corrective_for" in s for s in semantics)
