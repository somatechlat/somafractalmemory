#!/usr/bin/env python3
"""
Performance Benchmark for SomaFractalMemory
Tests key operations: store, retrieve, search, decay, annealing.
Measures latency, throughput, memory, CPU, and compares to baselines.
Supports large-scale testing (up to 1M items).
"""

import argparse
import csv
import gc
import importlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import numpy as np

# Optional dependency: psutil (used for metrics). Fallback to limited metrics if unavailable.
try:
    _psutil = importlib.import_module("psutil")
except Exception:
    _psutil = None

from somafractalmemory.core import MemoryType

# Import the memory system
from somafractalmemory.factory import MemoryMode, create_memory_system


class PerformanceMonitor:
    """Monitor system performance metrics."""
    def __init__(self):
        self.process = _psutil.Process(os.getpid()) if _psutil else None
        self.start_cpu = _psutil.cpu_percent(interval=None) if _psutil else 0.0
        self.start_mem = self.process.memory_info().rss if self.process else 0
        self.start_disk = _psutil.disk_io_counters() if _psutil else None
        self.start_time = time.time()

    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics."""
        end_time = time.time()
        end_cpu = _psutil.cpu_percent(interval=None) if _psutil else 0.0
        end_mem = self.process.memory_info().rss if self.process else 0
        end_disk = _psutil.disk_io_counters() if _psutil else None

        return {
            "cpu_percent": end_cpu,
            "memory_mb": end_mem / 1024 / 1024,
            "memory_delta_mb": (end_mem - self.start_mem) / 1024 / 1024,
            "disk_read_mb": (end_disk.read_bytes - self.start_disk.read_bytes) / 1024 / 1024 if end_disk and self.start_disk else 0,
            "disk_write_mb": (end_disk.write_bytes - self.start_disk.write_bytes) / 1024 / 1024 if end_disk and self.start_disk else 0,
            "time_elapsed": end_time - self.start_time
        }

def benchmark_redis_baseline(num_items: int = 10000) -> Dict[str, Any]:
    """Benchmark Redis as KV baseline."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.flushdb()

        monitor = PerformanceMonitor()

        # Store
        for i in range(num_items):
            r.set(f"key_{i}", f"value_{i}")

        store_metrics = monitor.get_metrics()

        # Retrieve
        monitor = PerformanceMonitor()
        for i in range(num_items):
            r.get(f"key_{i}")

        retrieve_metrics = monitor.get_metrics()

        r.flushdb()
        return {
            "store_throughput": num_items / store_metrics["time_elapsed"],
            "retrieve_throughput": num_items / retrieve_metrics["time_elapsed"],
            "memory_mb": store_metrics["memory_mb"]
        }
    except Exception as e:
        print(f"Redis baseline failed: {e}")
        return {"error": str(e)}

def benchmark_faiss_baseline(num_items: int = 10000, dim: int = 768) -> Dict[str, Any]:
    """Benchmark FAISS as vector search baseline."""
    try:
        import faiss
        monitor = PerformanceMonitor()

        # Generate data
        vectors = np.random.random((num_items, dim)).astype('float32')
        query = np.random.random((1, dim)).astype('float32')

        # Build index
        index = faiss.IndexFlatL2(dim)
        index.add(vectors)  # type: ignore[attr-defined]

        build_metrics = monitor.get_metrics()

        # Search
        monitor = PerformanceMonitor()
        D, I = index.search(query, 10)  # type: ignore[attr-defined]

        search_metrics = monitor.get_metrics()

        return {
            "build_time": build_metrics["time_elapsed"],
            "search_time": search_metrics["time_elapsed"],
            "memory_mb": build_metrics["memory_mb"]
        }
    except Exception as e:
        print(f"FAISS baseline failed: {e}")
        return {"error": str(e)}

def benchmark_store(mem, num_items: int = 1000, batch_size: int = 100) -> Dict[str, Any]:
    """Benchmark store operations with batching for large scale."""
    print(f"Benchmarking store: {num_items} items (batch size: {batch_size})...")
    monitor = PerformanceMonitor()

    def store_batch(start_idx: int):
        for i in range(start_idx, min(start_idx + batch_size, num_items)):
            coord = (i % 100, i // 100, i % 1000)
            payload = {
                "data": f"item_{i}",
                "value": i,
                "text": f"This is test memory item number {i} with some content for benchmarking."
            }
            mem.store_memory(coord, payload, MemoryType.EPISODIC)

    # Parallel batch processing
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(store_batch, i) for i in range(0, num_items, batch_size)]
        for future in futures:
            future.result()

    metrics = monitor.get_metrics()
    throughput = num_items / metrics["time_elapsed"]
    latency = metrics["time_elapsed"] / num_items

    return {
        "total_time": metrics["time_elapsed"],
        "latency_per_item": latency,
        "throughput_items_per_sec": throughput,
        "cpu_percent": metrics["cpu_percent"],
        "memory_mb": metrics["memory_mb"],
        "memory_delta_mb": metrics["memory_delta_mb"],
        "disk_read_mb": metrics["disk_read_mb"],
        "disk_write_mb": metrics["disk_write_mb"]
    }

def benchmark_retrieve(mem, num_items: int = 1000) -> Dict[str, Any]:
    """Benchmark retrieve operations."""
    print(f"Benchmarking retrieve: {num_items} items...")
    coords = [(i % 100, i // 100, i % 1000) for i in range(num_items)]
    monitor = PerformanceMonitor()

    for coord in coords:
        result = mem.retrieve(coord)

    metrics = monitor.get_metrics()
    throughput = num_items / metrics["time_elapsed"]
    latency = metrics["time_elapsed"] / num_items

    return {
        "total_time": metrics["time_elapsed"],
        "latency_per_item": latency,
        "throughput_items_per_sec": throughput,
        "cpu_percent": metrics["cpu_percent"],
        "memory_mb": metrics["memory_mb"],
        "memory_delta_mb": metrics["memory_delta_mb"],
        "disk_read_mb": metrics["disk_read_mb"],
        "disk_write_mb": metrics["disk_write_mb"]
    }

def benchmark_search(mem, num_queries: int = 100) -> Dict[str, Any]:
    """Benchmark search operations."""
    print(f"Benchmarking search: {num_queries} queries...")
    queries = [f"test memory item number {i}" for i in range(num_queries)]
    monitor = PerformanceMonitor()

    for query in queries:
        results = mem.find_hybrid_by_type(query, top_k=5)

    metrics = monitor.get_metrics()
    throughput = num_queries / metrics["time_elapsed"]
    latency = metrics["time_elapsed"] / num_queries

    return {
        "total_time": metrics["time_elapsed"],
        "latency_per_query": latency,
        "throughput_queries_per_sec": throughput,
        "cpu_percent": metrics["cpu_percent"],
        "memory_mb": metrics["memory_mb"],
        "memory_delta_mb": metrics["memory_delta_mb"],
        "disk_read_mb": metrics["disk_read_mb"],
        "disk_write_mb": metrics["disk_write_mb"]
    }

def benchmark_decay(mem) -> Dict[str, Any]:
    """Benchmark decay process."""
    print("Benchmarking decay process...")
    monitor = PerformanceMonitor()
    mem._apply_decay_to_all()
    metrics = monitor.get_metrics()

    return {
        "total_time": metrics["time_elapsed"],
        "cpu_percent": metrics["cpu_percent"],
        "memory_mb": metrics["memory_mb"],
        "memory_delta_mb": metrics["memory_delta_mb"],
        "disk_read_mb": metrics["disk_read_mb"],
        "disk_write_mb": metrics["disk_write_mb"]
    }

def benchmark_annealing(mem) -> Dict[str, Any]:
    """Benchmark annealing process."""
    print("Benchmarking annealing process...")
    monitor = PerformanceMonitor()
    mem._fractal_annealing_scheduler()
    metrics = monitor.get_metrics()

    return {
        "total_time": metrics["time_elapsed"],
        "cpu_percent": metrics["cpu_percent"],
        "memory_mb": metrics["memory_mb"],
        "memory_delta_mb": metrics["memory_delta_mb"],
        "disk_read_mb": metrics["disk_read_mb"],
        "disk_write_mb": metrics["disk_write_mb"]
    }

def run_full_benchmark(
    scale: str = "medium",
    backend: Optional[str] = None,
    output_json: Optional[str] = None,
    output_csv: Optional[str] = None,
    check_slo: bool = False,
    profile: Optional[str] = None,
):
    """Run complete performance benchmark with baselines."""
    print(f"=== SomaFractalMemory Performance Benchmark ({scale} scale) ===\n")

    # Scale configuration
    if scale == "small":
        num_items = 1000
        num_queries = 50
    elif scale == "medium":
        num_items = 10000
        num_queries = 100
    elif scale == "large":
        num_items = 100000
        num_queries = 500
    elif scale == "xl":
        num_items = 1000000
        num_queries = 1000
    else:
        num_items = 10000
        num_queries = 100

    # Create memory system
    # Choose vector backend via config
    vec_backend_cfg: Dict[str, Any] = {"backend": (backend or os.getenv("SOMA_BENCH_BACKEND", "inmemory"))}
    config: Dict[str, Any] = {"redis": {"testing": True}, "vector": vec_backend_cfg}
    bench_profile = (profile or os.getenv("SOMA_BENCH_PROFILE", "fast")).lower()
    # For faiss_aperture, set a small profile to keep runtime reasonable
    if vec_backend_cfg["backend"] == "faiss_aperture":
        config["faiss_aperture"] = {"profile": bench_profile}
        config["memory_enterprise"] = {"vector_dim": int(os.getenv("SOMA_BENCH_DIM", "128"))}
    # For fractal backend, map profiles to reasonable defaults
    if vec_backend_cfg["backend"] == "fractal":
        fcfg: Dict[str, Any] = {}
        if bench_profile == "fast":
            fcfg = {"centroids": 64, "beam_width": 3, "max_candidates": 256}
        elif bench_profile == "balanced":
            fcfg = {"centroids": 128, "beam_width": 4, "max_candidates": 1024}
        elif bench_profile == "high_recall":
            fcfg = {"centroids": 256, "beam_width": 6, "max_candidates": 2048}
        else:
            # default
            fcfg = {"centroids": 128, "beam_width": 4, "max_candidates": 1024}
        config["vector"]["fractal"] = fcfg

    mem = create_memory_system(MemoryMode.LOCAL_AGENT, f"benchmark_{scale}_ns", config=config)

    results = {}

    # Run baselines
    print("Running baseline comparisons...")
    results["redis_baseline"] = benchmark_redis_baseline(min(num_items, 10000))
    results["faiss_baseline"] = benchmark_faiss_baseline(min(num_items, 10000))

    # Run SomaFractalMemory benchmarks
    print("\nRunning SomaFractalMemory benchmarks...")
    results["store"] = benchmark_store(mem, num_items)
    gc.collect()

    results["retrieve"] = benchmark_retrieve(mem, num_items)
    gc.collect()

    results["search"] = benchmark_search(mem, num_queries)
    gc.collect()

    results["decay"] = benchmark_decay(mem)
    gc.collect()

    results["annealing"] = benchmark_annealing(mem)
    gc.collect()

    # Print results (human)
    print("\n=== Results ===")
    for operation, metrics in results.items():
        print(f"\n{operation.upper()}:")
        if isinstance(metrics, dict) and "error" in metrics:
            print(f"  Error: {metrics['error']}")
            continue
        for metric, value in (metrics or {}).items():
            if isinstance(value, float):
                if any(x in metric for x in ["latency", "time"]):
                    print(f"  {metric}: {value:.4f}")
                elif any(x in metric for x in ["throughput"]):
                    print(f"  {metric}: {value:.2f}")
                elif any(x in metric for x in ["mb", "percent"]):
                    print(f"  {metric}: {value:.2f}")
                else:
                    print(f"  {metric}: {value:.4f}")
            else:
                print(f"  {metric}: {value}")

    # Performance comparison
    print("\n=== Performance Comparison ===")
    if isinstance(results.get("redis_baseline"), dict) and "error" not in results["redis_baseline"]:
        soma_store = results.get("store", {}).get("throughput_items_per_sec", 0.0)
        redis_store = results["redis_baseline"].get("store_throughput", 0.0)
        if soma_store and redis_store:
            print(f"  Store throughput vs Redis: {soma_store / redis_store:.2f}x")

    if isinstance(results.get("faiss_baseline"), dict) and "error" not in results["faiss_baseline"]:
        soma_search = results.get("search", {}).get("throughput_queries_per_sec", 0.0)
        faiss_search = 1.0 / results["faiss_baseline"].get("search_time", 1.0) if results["faiss_baseline"].get("search_time", 0.0) > 0 else 0
        if soma_search and faiss_search:
            print(f"  Search throughput vs FAISS flat: {soma_search / faiss_search:.2f}x")

    # Optional JSON/CSV outputs
    if output_json:
        try:
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"\nWrote JSON results to {output_json}")
        except Exception as e:
            print(f"Failed to write JSON: {e}")

    if output_csv:
        try:
            # Flatten simple metrics into rows: op, metric, value
            with open(output_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["operation", "metric", "value"])
                for op, metrics in results.items():
                    if isinstance(metrics, dict):
                        for k, v in metrics.items():
                            writer.writerow([op, k, v])
            print(f"Wrote CSV results to {output_csv}")
        except Exception as e:
            print(f"Failed to write CSV: {e}")

    # Simple SLO checks (CPU-only estimates)
    if check_slo:
        slo_pass = True
        # Targets: p95 latency proxy using average; adjust as needed
        target_latency_store = 1.0 / 50.0  # ~0.02s per item (50 ops/s)
        target_latency_search = 1.0 / 50.0  # ~0.02s per query
        store_lat = results.get("store", {}).get("latency_per_item", 1.0)
        search_lat = results.get("search", {}).get("latency_per_query", 1.0)
        if store_lat > target_latency_store:
            print(f"SLO FAIL: store latency {store_lat:.4f}s > {target_latency_store:.4f}s")
            slo_pass = False
        if search_lat > target_latency_search:
            print(f"SLO FAIL: search latency {search_lat:.4f}s > {target_latency_search:.4f}s")
            slo_pass = False
        if not slo_pass:
            raise SystemExit(2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run SomaFractalMemory performance benchmark")
    parser.add_argument("--scale", default="medium", choices=["small", "medium", "large", "xl"], help="Benchmark scale")
    parser.add_argument("--backend", default=None, help="Vector backend to use (inmemory, fractal, faiss_aperture, qdrant)")
    parser.add_argument("--profile", default=None, choices=["fast", "balanced", "high_recall"], help="Optional profile for backend tuning (affects fractal/faiss)")
    parser.add_argument("--json", dest="output_json", default=None, help="Path to write JSON output")
    parser.add_argument("--csv", dest="output_csv", default=None, help="Path to write CSV output")
    parser.add_argument("--check-slo", action="store_true", help="Enable simple SLO checks and non-zero exit on failure")
    args = parser.parse_args()
    run_full_benchmark(scale=args.scale, backend=args.backend, output_json=args.output_json, output_csv=args.output_csv, check_slo=args.check_slo, profile=args.profile)