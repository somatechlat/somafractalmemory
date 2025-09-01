# Contributing to somafractalmemory

Thank you for your interest in contributing!

## Workflow at a glance
- Use a local venv: `python -m venv .venv && . .venv/bin/activate`.
- Install dev deps: `pip install -e '.[dev]'` or `pip install -r requirements.txt`.
- Run tests: `pytest -q`.
- Lint/typecheck (optional): `ruff check .` and `mypy`.

## Status and Roadmap
Product-facing plans can live in `docs/ROADMAP.md`.
For local state and personal plans, use `recovery/` (git-ignored) to avoid cluttering the repo.

## Optional extras
Heavy integrations are behind extras; core should import without them. If you add a new integration, guard imports and add fallbacks.
# Contributing to somafractalmemory

Thank you for your interest in contributing!

## How to contribute
- Fork the repository and create your branch from `main`.
- Write clear, concise commit messages.
- Add tests for new features and bug fixes.
- Run `pytest` and ensure all tests pass before submitting a PR.
- Follow PEP8 and use `black` for formatting.

## Reporting issues
- Use GitHub Issues for bug reports and feature requests.
- Include as much detail as possible.
