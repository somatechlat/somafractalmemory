# isort: skip_file
"""
Synthetic benchmark against a live SomaFractalMemory API (no mocks).

This script generates a simple, precise synthetic dataset, loads it via the
real HTTP API (/store_bulk), and runs recall queries (/recall_with_scores)
to measure correctness (Recall@K, MRR) and latency quantiles. It never
starts containers itself: the stack must be up and healthy before running.

Usage (examples):
  python scripts/synthetic_real_stack_benchmark.py
  python scripts/synthetic_real_stack_benchmark.py --N 5000 --Q 500 --top-k 5
  SOMA_API_TOKEN=secret \
    python scripts/synthetic_real_stack_benchmark.py --base-url http://127.0.0.1:9595

Contract:
  Inputs
    - Live API base URL (detected: 9595, 8888, 9999; or via --base-url)
    - Optional bearer token via env SOMA_API_TOKEN or --token
    - N items to insert, Q queries to issue, top_k, batch_size
  Outputs
    - Prints metrics: insert throughput, query latency p50/p90/p95/p99 (ms),
      Recall@K, MRR. Writes a JSON report when --out is provided.

Edge cases handled
  - Base URL auto-detection across common ports
  - Health check via /healthz (fallback /health)
  - Authorization optional (only enforced if API is configured with a token)

Notes
  - Dataset uses payload {"fact": f"item-{i}"} so the exact-query "item-i"
    has a well-defined ground truth. This mirrors internal benchmarks.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import string
import sys
import time
from dataclasses import dataclass
from typing import Any

import requests


DEFAULT_PORTS = (9595, 8888, 9999)


def _percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile for small samples.

    p in [0,1]. For empty list returns NaN.
    """
    if not values:
        return float("nan")
    if p <= 0:
        return min(values)
    if p >= 1:
        return max(values)
    s = sorted(values)
    k = max(1, min(len(s), int(math.ceil(p * len(s)))))
    return s[k - 1]


def _detect_base_url(user_url: str | None) -> str:
    if user_url:
        return user_url.rstrip("/")
    candidates = [f"http://127.0.0.1:{port}" for port in DEFAULT_PORTS]
    candidates += [f"http://localhost:{port}" for port in DEFAULT_PORTS]
    for base in candidates:
        try:
            r = requests.get(f"{base}/healthz", timeout=1.5)
            if r.ok:
                return base
        except Exception:
            pass
        try:
            r = requests.get(f"{base}/health", timeout=1.5)
            if r.ok:
                return base
        except Exception:
            pass
    raise SystemExit(
        "No live API detected on 127.0.0.1:{9595,8888,9999} or localhost. "
        "Provide --base-url or start the stack."
    )


def _headers(token: str | None) -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _post_with_retry(
    url: str,
    headers: dict[str, str],
    *,
    json_payload: dict | None = None,
    params: dict | None = None,
    timeout: float = 30.0,
) -> requests.Response:
    """POST with basic 429-aware retry/backoff to respect API rate limits."""
    delay = 0.5
    for _ in range(6):
        r = requests.post(url, headers=headers, json=json_payload, params=params, timeout=timeout)
        if r.status_code != 429:
            return r
        # rate limited; honor Retry-After header if present
        retry_after = r.headers.get("Retry-After")
        try:
            wait = float(retry_after) if retry_after else delay
        except Exception:
            wait = delay
        time.sleep(wait)
        delay = min(delay * 2.0, 8.0)
    # Final attempt without swallowing errors
    r = requests.post(url, headers=headers, json=json_payload, params=params, timeout=timeout)
    return r


def _rand_coord(i: int) -> str:
    # Simple 2D coordinate; use deterministic mapping but non-trivial floats
    return f"{float(i):.6f},{float(i + 1):.6f}"


def _noise(n: int = 6) -> str:
    return "".join(random.choice(string.ascii_lowercase) for _ in range(n))


@dataclass
class InsertMetrics:
    inserted: int
    seconds: float

    @property
    def throughput(self) -> float:
        return self.inserted / self.seconds if self.seconds > 0 else float("nan")


@dataclass
class QueryMetrics:
    queries: int
    seconds: float
    latencies_ms: list[float]
    hits: int
    rr: list[float]

    @property
    def qps(self) -> float:
        return self.queries / self.seconds if self.seconds > 0 else float("nan")

    @property
    def recall_at_k(self) -> float:
        return self.hits / self.queries if self.queries else float("nan")

    @property
    def mrr(self) -> float:
        return sum(self.rr) / len(self.rr) if self.rr else float("nan")


def store_bulk(base: str, token: str | None, items: list[dict[str, Any]]) -> None:
    url = f"{base}/store_bulk"
    payload = {"items": items}
    r = _post_with_retry(url, headers=_headers(token), json_payload=payload, timeout=30)
    r.raise_for_status()


def recall_with_scores(
    base: str, token: str | None, query: str, top_k: int, type_: str | None
) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {"query": query, "top_k": top_k}
    if type_:
        payload["type"] = type_
    url = f"{base}/recall_with_scores"
    r = _post_with_retry(
        url,
        headers=_headers(token),
        json_payload=payload,
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    return body.get("results", [])


def do_inserts(
    base: str, token: str | None, N: int, batch_size: int, type_: str | None
) -> InsertMetrics:
    t0 = time.time()
    i = 0
    while i < N:
        batch: list[dict[str, Any]] = []
        for j in range(i, min(i + batch_size, N)):
            batch.append(
                {
                    "coord": _rand_coord(j),
                    "payload": {
                        "fact": f"item-{j}",
                        # Provide some structure and variation
                        "importance": (j % 97) / 96.0,
                        "noise": _noise(8),
                    },
                    "type": type_ or "episodic",
                }
            )
        store_bulk(base, token, batch)
        i += len(batch)
    seconds = time.time() - t0
    return InsertMetrics(inserted=N, seconds=seconds)


def do_queries(
    base: str, token: str | None, N: int, Q: int, top_k: int, type_: str | None
) -> QueryMetrics:
    latencies: list[float] = []
    rr: list[float] = []
    hits = 0

    # Deterministic but covering the space reasonably
    random.seed(0)
    indices = [random.randint(0, N - 1) for _ in range(Q)]

    t0 = time.time()
    for idx in indices:
        query = f"item-{idx}"
        s = time.perf_counter()
        results = recall_with_scores(base, token, query, top_k, type_)
        latencies.append((time.perf_counter() - s) * 1000.0)

        # Evaluate Recall@K and Reciprocal Rank
        found_rank = None
        for r_i, r in enumerate(results, start=1):
            payload = r.get("payload", {})
            if payload.get("fact") == query:
                found_rank = r_i
                break
        if found_rank is not None and found_rank <= top_k:
            hits += 1
            rr.append(1.0 / found_rank)
        else:
            rr.append(0.0)

    seconds = time.time() - t0
    return QueryMetrics(queries=Q, seconds=seconds, latencies_ms=latencies, hits=hits, rr=rr)


def run(
    base_url: str | None,
    token: str | None,
    N: int,
    Q: int,
    top_k: int,
    batch_size: int,
    type_: str | None,
    out: str | None,
) -> int:
    base = _detect_base_url(base_url)
    token = token or os.getenv("SOMA_API_TOKEN")
    # Deterministic noise and query sampling for reproducibility
    random.seed(0)

    # Sanity health check
    try:
        r = requests.get(f"{base}/healthz", timeout=3)
    except Exception:
        r = requests.get(f"{base}/health", timeout=3)
    r.raise_for_status()
    health = r.json()
    print(
        f"[health] kv_store={health.get('kv_store')} vector_store={health.get('vector_store')} graph_store={health.get('graph_store')} prediction_provider={health.get('prediction_provider')}"
    )

    ins = do_inserts(base, token, N=N, batch_size=batch_size, type_=type_)
    qry = do_queries(base, token, N=N, Q=Q, top_k=top_k, type_=type_)

    p50 = _percentile(qry.latencies_ms, 0.50)
    p90 = _percentile(qry.latencies_ms, 0.90)
    p95 = _percentile(qry.latencies_ms, 0.95)
    p99 = _percentile(qry.latencies_ms, 0.99)

    print("\nResults (real stack):")
    print(
        f"- Inserts: {ins.inserted} in {ins.seconds:.2f}s  | throughput = {ins.throughput:.1f} items/s"
    )
    print(
        f"- Queries: {qry.queries} in {qry.seconds:.2f}s | qps = {qry.qps:.1f} | latency ms p50={p50:.2f} p90={p90:.2f} p95={p95:.2f} p99={p99:.2f}"
    )
    print(f"- Recall@{top_k}: {qry.recall_at_k:.3f}")
    print(f"- MRR: {qry.mrr:.3f}")

    report = {
        "base_url": base,
        "N": N,
        "Q": Q,
        "top_k": top_k,
        "batch_size": batch_size,
        "insert": {"seconds": ins.seconds, "throughput": ins.throughput},
        "query": {
            "seconds": qry.seconds,
            "qps": qry.qps,
            "latency_ms": {
                "p50": p50,
                "p90": p90,
                "p95": p95,
                "p99": p99,
            },
            "recall_at_k": qry.recall_at_k,
            "mrr": qry.mrr,
        },
    }

    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nSaved report to {out}")

    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Synthetic benchmark against a live SomaFractalMemory API"
    )
    p.add_argument(
        "--base-url",
        dest="base_url",
        help="API base URL (default: auto-detect common localhost ports)",
    )
    p.add_argument("--token", help="Bearer token (default: uses SOMA_API_TOKEN env if set)")
    p.add_argument("--N", type=int, default=2000, help="Number of items to insert")
    p.add_argument("--Q", type=int, default=400, help="Number of queries to run")
    p.add_argument("--top-k", type=int, default=5, help="Top-K for recall evaluation")
    p.add_argument("--batch-size", type=int, default=200, help="Store batch size for /store_bulk")
    p.add_argument(
        "--type",
        dest="type_",
        choices=["episodic", "semantic"],
        default=None,
        help="Memory type to store/query",
    )
    p.add_argument("--out", help="Optional path to write a JSON report")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        return run(
            base_url=args.base_url,
            token=args.token or os.getenv("SOMA_API_TOKEN"),
            N=args.N,
            Q=args.Q,
            top_k=args.top_k,
            batch_size=args.batch_size,
            type_=args.type_,
            out=args.out,
        )
    except requests.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        if e.response is not None:
            try:
                print(e.response.json(), file=sys.stderr)
            except Exception:
                print(e.response.text, file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
