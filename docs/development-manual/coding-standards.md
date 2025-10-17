# Coding Standards

- **Language**: Python 3.11 with `ruff` and `black` enforced via pre-commit.
- **Imports**: Follow the `isort` profile already configured in `pyproject.toml`.
- **Typing**: Use `typing.Annotated` sparingly; prefer concrete `TypedDict`/`pydantic` models for API payloads.
- **Logging**: Emit structured logs through `structlog`. Never `print` in production code.
- **HTTP API**: New routes must go through the FastAPI app in `http_api.py`. Do not reintroduce `/store`, `/recall`, or graph endpoints.
- **CLI**: Mirror the `/memories` capabilities only. Commands must be idempotent and return JSON on stdout.
- **Docs**: Update the appropriate manual when changing behaviour. The docs tree must remain compliant with the 4-manual structure.
