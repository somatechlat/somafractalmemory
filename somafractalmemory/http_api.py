"""HTTP API entrypoint wrapper.

This module intentionally re-exports the FastAPI ``app`` from the legacy
module path to provide a stable, descriptive import target
``somafractalmemory.http_api:app``.
"""

try:  # Prefer explicit attribute import to satisfy linters
    from examples.api import app  # type: ignore
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "Expected examples.api:app to exist; please ensure the FastAPI app is available."
    ) from exc

__all__ = ["app"]
