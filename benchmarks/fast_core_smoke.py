"""Fast core smoke benchmark.
Run manually: python -m somafractalmemory.benchmarks.fast_core_smoke
"""

from __future__ import annotations

import os
import random
import statistics as stats
import time

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.implementations.storage import (
    InMemoryKeyValueStore,
    InMemoryVectorStore,
)
from somafractalmemory.interfaces.graph import IGraphStore


class _NullGraph(IGraphStore):
    def add_memory(self, coordinate, value):
        return None

    def add_link(self, from_coord, to_coord, link_data):
        return None

    def find_shortest_path(self, from_coord, to_coord, link_type=None):
        return []

    def get_neighbors(self, coord, link_type=None):
        return []

    def remove_memory(self, coordinate):
        return None

    def health_check(self):
        return True


def build_system(fast: bool):
    if fast:
        os.environ["SFM_FAST_CORE"] = "1"
    else:
        os.environ.pop("SFM_FAST_CORE", None)
    return SomaFractalMemoryEnterprise(
        namespace="bench",
        kv_store=InMemoryKeyValueStore(),
        vector_store=InMemoryVectorStore(),
        graph_store=_NullGraph(),
        vector_dim=64,
        decay_enabled=False,
        reconcile_enabled=False,
    )


def main():
    N = 5000
    Q = 200
    random.seed(0)
    print(f"Benchmark N={N} Q={Q}")

    for fast in (False, True):
        sys = build_system(fast)
        t0 = time.time()
        for i in range(N):
            sys.store_memory(
                (float(i), float(i + 1)),
                {
                    "fact": f"item-{i}",
                    "importance": random.random() * (1 + (i % 97)),
                    "memory_type": MemoryType.EPISODIC.value,
                },
            )
        t_insert = time.time() - t0
        latencies = []
        for _ in range(Q):
            q = f"item-{random.randint(0, N-1)}"
            s = time.perf_counter()
            _ = sys.find_hybrid_by_type(q, top_k=5)
            latencies.append((time.perf_counter() - s) * 1000.0)
        print(
            f"Mode={'FAST' if fast else 'LEGACY'} | insert {t_insert:.2f}s | query ms p50={stats.median(latencies):.3f} p95={sorted(latencies)[int(0.95*len(latencies))-1]:.3f} p99={sorted(latencies)[int(0.99*len(latencies))-1]:.3f}"  # noqa: E501
        )


if __name__ == "__main__":
    main()
