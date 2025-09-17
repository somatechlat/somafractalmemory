"""Top-level package for somafractalmemory.

This module exposes lightweight metadata and keeps runtime imports minimal.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

# Public package version for introspection/tools
try:  # pragma: no cover - trivial metadata access
    __version__ = _version("somafractalmemory")
except PackageNotFoundError:  # Local, editable, or missing dist metadata
    __version__ = "0.0.0.dev0"

__all__ = [
    "__version__",
]
