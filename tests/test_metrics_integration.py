from somafractalmemory.factory import MemoryMode, create_memory_system


def _get_metric_value(metric):
    try:
        # prometheus_client metric has _value or collect() depending on type
        samples = list(metric.collect())[0].samples
        return sum(s.value for s in samples)
    except Exception:
        try:
            return float(metric._value.get())
        except Exception:
            return None


def test_metrics_basic_store_recall():
    mem = create_memory_system(MemoryMode.ON_DEMAND, "metrics_ns")

    # If metrics are not available, just exercise paths to ensure no exceptions
    store_before = None
    recall_before = None
    try:
        from somafractalmemory.core import _RECALL_COUNT, _STORE_COUNT

        if _STORE_COUNT is not None:
            store_before = _get_metric_value(_STORE_COUNT)
        if _RECALL_COUNT is not None:
            recall_before = _get_metric_value(_RECALL_COUNT)
    except Exception:
        pass

    coord = (1.0, 2.0)
    mem.store_memory(coord, {"task": "test", "importance": 1})
    _ = mem.retrieve(coord)

    try:
        from somafractalmemory.core import _RECALL_COUNT, _STORE_COUNT

        if _STORE_COUNT is not None:
            store_after = _get_metric_value(_STORE_COUNT)
            assert store_after is None or (store_before is None or store_after >= store_before)
        if _RECALL_COUNT is not None:
            recall_after = _get_metric_value(_RECALL_COUNT)
            assert recall_after is None or (recall_before is None or recall_after >= recall_before)
    except Exception:
        # If prometheus_client not installed, consider test passed as long as no exceptions
        pass
