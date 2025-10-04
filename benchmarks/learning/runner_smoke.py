from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Any

import requests

from .generators import generate_dataset
from .metrics import mrr, ndcg_at_k, percentiles, recall_at_k


@dataclass
class RunConfig:
    base_url: str = os.environ.get("SFM_API_BASE", "http://127.0.0.1:9595")
    token: str | None = os.environ.get("SOMA_API_TOKEN")
    n_topics: int = int(os.environ.get("SFM_BENCH_TOPICS", "3"))
    items_per_topic: int = int(os.environ.get("SFM_BENCH_ITEMS", "5"))
    top_k: int = 5
    seed: int = 42
    hybrid: bool = True
    exact: bool = False
    timeout_s: float = float(os.environ.get("SFM_HTTP_TIMEOUT", "60"))
    retries: int = int(os.environ.get("SFM_HTTP_RETRIES", "3"))


def _headers(cfg: RunConfig) -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if cfg.token:
        h["Authorization"] = f"Bearer {cfg.token}"
    return h


def store_bulk(cfg: RunConfig, items):
    url = f"{cfg.base_url}/store_bulk"
    payload = {
        "items": [
            {"coord": ",".join(str(x) for x in it.coord), "payload": it.payload, "type": it.mtype}
            for it in items
        ]
    }
    last_exc = None
    for attempt in range(1, cfg.retries + 1):
        try:
            r = requests.post(url, headers=_headers(cfg), json=payload, timeout=cfg.timeout_s)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_exc = e
            time.sleep(min(2 ** (attempt - 1), 5))
    raise last_exc  # type: ignore[misc]


def recall_with_scores(cfg: RunConfig, query: str) -> tuple[list[dict[str, Any]], float]:
    url = f"{cfg.base_url}/recall_with_scores"
    params = {
        "query": query,
        "top_k": cfg.top_k,
        "hybrid": str(cfg.hybrid).lower(),
        "exact": str(cfg.exact).lower(),
    }
    t0 = time.perf_counter()
    r = requests.post(url, headers=_headers(cfg), params=params, timeout=cfg.timeout_s)
    dt = (time.perf_counter() - t0) * 1000.0
    r.raise_for_status()
    data = r.json()
    results = data.get("results", [])
    return results, dt


def run_smoke(cfg: RunConfig) -> dict[str, Any]:
    items, queries = generate_dataset(
        n_topics=cfg.n_topics, items_per_topic=cfg.items_per_topic, seed=cfg.seed
    )
    store_bulk(cfg, items)

    ranks = []
    lats = []
    for q in queries:
        results, ms = recall_with_scores(cfg, q.query)
        lats.append(ms)
        # Relevance heuristic:
        # - For keyword queries: exact payload string contains the token
        # - For semantic: payload["topic"] matches q.topic
        target_rank = 0
        for i, res in enumerate(results, start=1):
            payload = res.get("payload", {})
            if q.kind in ("keyword", "hybrid") and q.token:
                found = any(isinstance(v, str) and q.token in v for v in payload.values())
                if found:
                    target_rank = i
                    break
            if q.kind == "semantic" and q.topic and payload.get("topic") == q.topic:
                target_rank = i
                break
        ranks.append(target_rank if target_rank > 0 else 0)

    out = {
        "config": asdict(cfg),
        "counts": {"items": len(items), "queries": len(queries)},
        "metrics": {
            "recall@1": recall_at_k(ranks, 1),
            "recall@5": recall_at_k(ranks, 5),
            "mrr": mrr(ranks),
            "ndcg@5": ndcg_at_k(ranks, 5),
            "latency_ms": percentiles(lats),
        },
    }
    return out


if __name__ == "__main__":
    cfg = RunConfig()
    report = run_smoke(cfg)
    print(json.dumps(report, indent=2))
