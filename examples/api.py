"""Compatibility shim for the legacy FastAPI import path.

This module now delegates to ``somafractalmemory.http_api`` to provide the
``app`` object. Update your imports to ``somafractalmemory.http_api:app``.
"""

from somafractalmemory.http_api import app  # noqa: F401
