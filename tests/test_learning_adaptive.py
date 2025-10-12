import os
import time

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def _make_system(env: dict | None = None):
    # Allow caller to inject env overrides (e.g. SOMA_MAX_MEMORY_SIZE) but restore after creation
    original = {}
    if env:
        for k, v in env.items():
            original[k] = os.environ.get(k)
            os.environ[k] = str(v)
    config = {"redis": {"testing": True}, "vector": {"backend": "memory"}}
    system = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "learn_ns", config=config)
    # Restore original env to avoid leaking settings into other tests
    if env:
        for k, old in original.items():
            if old is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old
    return system


def test_adaptive_importance_minmax_stage():
    """<64 samples -> method should stay 'minmax' and normalization in [0,1]."""
    mem = _make_system()
    methods = set()
    norms = []
    for imp in range(1, 10):
        mem.store_memory(
            (float(imp), 0.0, 0.0),
            {"task": f"early-{imp}", "importance": imp},
            memory_type=MemoryType.EPISODIC,
        )
        methods.add(mem._imp_method)  # type: ignore[attr-defined]
        norms.append(mem.retrieve((float(imp), 0.0, 0.0))["importance_norm"])  # type: ignore[index]
    # All norms bounded
    assert all(0.0 <= n <= 1.0 for n in norms)
    # Only minmax expected in early stage
    assert methods == {"minmax"}


def test_adaptive_importance_logistic_transition():
    """Inject heavy tail after reservoir >64 to force logistic path selection."""
    mem = _make_system()
    # Stage 1: build a narrow core distribution (importance mostly 1-3)
    for _ in range(80):
        mem.store_memory(
            (time.time(), _, 0.0),
            {"task": "core-low", "importance": 1},
            memory_type=MemoryType.EPISODIC,
        )
    for _ in range(15):
        mem.store_memory(
            (time.time(), _, 1.0),
            {"task": "core-mid", "importance": 2},
            memory_type=MemoryType.EPISODIC,
        )
    for _ in range(5):
        mem.store_memory(
            (time.time(), _, 2.0),
            {"task": "core-hi", "importance": 3},
            memory_type=MemoryType.EPISODIC,
        )
    # Stage 2: add extreme outliers to inflate tail ratios R_tail_max / R_tail_ext
    for extreme in (500.0, 1000.0, 2000.0):
        mem.store_memory(
            (extreme, 9.9, 9.9),
            {"task": f"outlier-{extreme}", "importance": extreme},
            memory_type=MemoryType.EPISODIC,
        )
    # Expect logistic now (heuristic thresholds in _adaptive_importance_norm)
    assert mem._imp_method in {
        "winsor",
        "logistic",
    }  # allow intermediate winsor in borderline cases
    # If logistic selected, confirm a mid value maps near sigmoid center ~0.5
    if mem._imp_method == "logistic":  # type: ignore[attr-defined]
        # Retrieve one mid-importance memory and check normalized value is not collapsed to 0/1
        mid = mem.retrieve_memories()[90]  # should be from earlier core distribution
        assert 0.15 < mid["importance_norm"] < 0.85


def test_importance_norm_monotonicity_snapshot():
    """Within a close batch (no method change), higher raw importance should yield >= norm."""
    mem = _make_system()
    raw_vals = [1, 5, 10, 25, 50]
    observed = []
    for r in raw_vals:
        mem.store_memory(
            (float(r), 1.0, 1.0),
            {"task": f"mono-{r}", "importance": r},
            memory_type=MemoryType.EPISODIC,
        )
        observed.append(mem.retrieve((float(r), 1.0, 1.0))["importance_norm"])  # type: ignore[index]
    # Non-decreasing (allow tiny floating epsilon)
    for i in range(len(observed) - 1):
        a, b = observed[i], observed[i + 1]
        assert b + 1e-9 >= a


def test_memory_limit_pruning():
    """Setting SOMA_MAX_MEMORY_SIZE forces pruning of oldest lowest-importance entries."""
    mem = _make_system({"SOMA_MAX_MEMORY_SIZE": 5})
    # Insert 8 with ascending importance so earlier low-importance candidates are pruned
    for i in range(8):
        mem.store_memory(
            (i * 1.0, 2.0, 3.0),
            {"task": f"prune-{i}", "importance": i},
            memory_type=MemoryType.EPISODIC,
        )
    all_mems = mem.get_all_memories()
    assert len(all_mems) <= 5
    # Ensure at least one highest importance item retained
    max_raw = max(m["importance"] for m in all_mems)
    assert max_raw >= 7 or any(m["importance"] == 7 for m in all_mems)
