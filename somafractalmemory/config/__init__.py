"""Configuration package for SomaFractalMemory.

Exports a singleton ``settings`` instance that reads all environment
variables (or a ``.env`` file) using :class:`pydantic.BaseSettings`.

All application code should import ``settings`` from this package instead
of calling ``os.getenv`` directly.  This is the first step of the
centralisation sprint and satisfies the Vibe coding rule **Consistency**.
"""

from .settings import settings  # noqa: F401  (re‑export for convenience)
