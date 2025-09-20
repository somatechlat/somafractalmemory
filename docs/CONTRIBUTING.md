Contributing to SomaFractalMemory
=================================

Guidelines

- Run tests: `pytest -q` and ensure green before opening a PR.
- Formatting: use `ruff` and `black` (project has `pyproject.toml` configured).
- Static checks: run `mypy` for type hints and `bandit` for security scanning where applicable.

New features

- Open an issue describing the user-visible behavior and edge-cases.
- If the change affects storage or eviction math, include performance benchmarks in `examples/benchmark.py`.

PR etiquette

- Keep changes small and scoped to one logical change.
- Include unit tests for new behaviors and regression tests for bug fixes.
- Do not push changes to main or tags without explicit release approval.
