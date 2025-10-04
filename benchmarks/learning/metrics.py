from __future__ import annotations

import math
from collections.abc import Sequence


def recall_at_k(ranks: Sequence[int], k: int) -> float:
    if not ranks:
        return 0.0
    hits = sum(1 for r in ranks if 1 <= r <= k)
    return hits / len(ranks)


def mrr(ranks: Sequence[int]) -> float:
    if not ranks:
        return 0.0
    return sum(1.0 / r for r in ranks if r > 0) / len(ranks)


def ndcg_at_k(ranks: Sequence[int], k: int) -> float:
    # Single relevant item per query variant: DCG = 1/log2(rank+1) if rank<=k else 0
    if not ranks:
        return 0.0

    def gain(rank: int) -> float:
        if rank <= 0 or rank > k:
            return 0.0
        return 1.0 / math.log2(rank + 1)

    dcg = sum(gain(r) for r in ranks)
    # Ideal DCG for single relevant item per query is 1 (rank=1 ⇒ 1/log2(2)=1)
    idcg = len(ranks) * 1.0
    return (dcg / idcg) if idcg > 0 else 0.0


def percentiles(latencies_ms: list[float]) -> dict[str, float]:
    if not latencies_ms:
        return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
    xs = sorted(latencies_ms)

    def pct(p: float) -> float:
        i = int(max(0, min(len(xs) - 1, round(p * (len(xs) - 1)))))
        return xs[i]

    return {
        "p50": pct(0.50),
        "p90": pct(0.90),
        "p95": pct(0.95),
        "p99": pct(0.99),
    }
