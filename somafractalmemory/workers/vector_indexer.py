"""DEPRECATED shim module.

This module exists only to preserve backward compatibility for imports like
``somafractalmemory.workers.vector_indexer``. The canonical implementation now
resides at ``workers/vector_indexer.py`` at the repository root. Importing from
this module will re-export symbols from the canonical module.

Do not add new code here; update ``workers/vector_indexer.py`` instead.
"""

# Re-export everything from the canonical workers module
from workers.vector_indexer import *  # type: ignore  # noqa: F401,F403
