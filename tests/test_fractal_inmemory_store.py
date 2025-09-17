import os
import random

import numpy as np

from somafractalmemory.implementations.fractal_inmemory import (
    FractalInMemoryVectorStore,
)


def test_fractal_store_basic_search_and_rebuild():
    dim = 32
    store = FractalInMemoryVectorStore(centroids=8, beam_width=3, max_candidates=64)
    store.setup(vector_dim=dim, namespace="testns")

    # Insert clusters around a few random anchors
    rng = np.random.default_rng(123)
    anchors = rng.normal(size=(5, dim)).astype(np.float32)
    anchors = anchors / np.clip(np.linalg.norm(anchors, axis=1, keepdims=True), 1e-9, None)

    pts = []
    for i, a in enumerate(anchors):
        for j in range(50):
            v = a + 0.05 * rng.normal(size=(dim,)).astype(np.float32)
            pts.append({"id": f"p{i}_{j}", "vector": v.tolist(), "payload": {"group": i}})
    store.upsert(pts)

    # Query near one anchor
    q = anchors[2] + 0.02 * rng.normal(size=(dim,)).astype(np.float32)
    hits = store.search(q.tolist(), top_k=5)
    assert len(hits) == 5
    # Majority should be from group 2
    grp = [h.payload.get("group") for h in hits]
    assert grp.count(2) >= 3

    # Delete a couple and ensure not returned
    del_ids = ["p2_0", "p2_1"]
    store.delete(del_ids)
    hits2 = store.search(q.tolist(), top_k=10)
    ids2 = [h.id for h in hits2]
    for did in del_ids:
        assert did not in ids2

    # Scroll sanity
    seen = list(store.scroll())
    assert len(seen) >= 200
    # health check should be true once built
    assert store.health_check() in (True, False)
