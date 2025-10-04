# Learning Benchmarks (Blueprint)

This folder will contain the runnable benchmark suite that proves learning with elegant, simple math.

Planned components:
- generators.py – deterministic semantic/keyword/graph data generators
- metrics.py – Recall@K, MRR, NDCG@K, latency percentiles
- protocols.py – warmup/drift/decay and continual-learning flows
- runner.py – executes runs against the live API (9595) and writes JSON reports
- plots.py – optional matplotlib helpers for quick charts

See the repository README for goals, acceptance thresholds, and how to run (to be added when implementation lands).
