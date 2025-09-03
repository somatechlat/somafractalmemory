# Contributing to somafractalmemory

Thank you for your interest in contributing to SomaFractalMemory.

## Quick start (local)

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   . .venv/bin/activate
   ```

2. Install development dependencies:

   ```bash
   pip install -e '.[dev]'
   ```

3. Run tests and linters:

   ```bash
   pytest -q
   ruff check .
   mypy
   ```

## Branching and PRs

- Fork the repo and create feature branches from `master`.
- Keep PRs focused and include tests for new behavior.
- CI must pass (tests + linters) before merging.

## Code style

- Format with `black` and check with `ruff`.
- Type-check with `mypy` where applicable.

## Optional extras and integrations

- Optional integrations live behind extras in `pyproject.toml`. Guard heavy imports to keep core lightweight.

## Reporting issues

- Use GitHub Issues and include a minimal reproducible example.

Thank you — contributions are welcome!
