"""
Simple benchmark for store and recall operations.

Usage:
  python examples/benchmark.py --n 1000 --dim 256
"""

import argparse
import random
import string
import time
from statistics import mean

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def rand_text(k: int = 16) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits + " ", k=k))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000, help="Number of items to store")
    ap.add_argument("--dim", type=int, default=256, help="Vector dimension (fallback)")
    ap.add_argument("--namespace", default="bench_ns")
    args = ap.parse_args()

    mem = create_memory_system(
        MemoryMode.DEVELOPMENT,
        args.namespace,
        config={
            "redis": {"testing": True},
            "qdrant": {"path": "./qdrant.db"},
            "memory_enterprise": {"vector_dim": args.dim},
        },
    )

    # Store benchmark
    start = time.perf_counter()
    for i in range(args.n):
        coord = (float(i % 100), float((i // 100) % 100), float(i % 7))
        payload = {"task": rand_text(24), "importance": i % 5}
        mem.store_memory(coord, payload, memory_type=MemoryType.EPISODIC)
    store_time = time.perf_counter() - start

    # Recall benchmark (random queries)
    queries = [rand_text(8) for _ in range(min(100, args.n))]
    latencies = []
    for q in queries:
        t0 = time.perf_counter()
        _ = mem.recall(q, top_k=5)
        latencies.append(time.perf_counter() - t0)

    print(
        {
            "stored": args.n,
            "store_seconds": round(store_time, 4),
            "store_per_sec": round(args.n / store_time if store_time else float("inf"), 2),
            "recall_count": len(queries),
            "recall_avg_ms": round(mean(latencies) * 1000, 2) if latencies else 0.0,
            "vector_dim": args.dim,
        }
    )


if __name__ == "__main__":
    main()
