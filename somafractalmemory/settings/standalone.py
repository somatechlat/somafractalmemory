"""
Standalone Settings Profile.
STRICTLY ISOLATED from AAAS/Multi-tenancy logic.
Usage: DJANGO_SETTINGS_MODULE=somafractalmemory.settings.standalone
"""

from .django_core import *  # noqa: F403
from .infra import *  # noqa: F403

# =============================================================================
# STANDALONE ISOLATION - STRIP AAAS
# =============================================================================

# Remove AAAS Application
if "somafractalmemory.apps.aaas" in INSTALLED_APPS:  # noqa: F405
    INSTALLED_APPS.remove("somafractalmemory.apps.aaas")  # noqa: F405

# Remove AAAS Middleware
MIDDLEWARE = [  # noqa: F405
    m
    for m in MIDDLEWARE  # noqa: F405
    if "somafractalmemory.apps.aaas" not in m and "UsageTrackingMiddleware" not in m
]

# Standalone defaults
SOMA_NAMESPACE = "standalone"
SOMA_MEMORY_NAMESPACE = "standalone_memory"

print(f"Loaded STANDALONE settings. Apps: {len(INSTALLED_APPS)}")  # noqa: F405
