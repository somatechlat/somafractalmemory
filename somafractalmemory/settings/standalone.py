"""
Standalone Settings Profile.
STRICTLY ISOLATED from AAAS/Multi-tenancy logic.
Usage: DJANGO_SETTINGS_MODULE=somafractalmemory.settings.standalone
"""

import logging
import os

from .django_core import *  # noqa: F403
from .infra import *  # noqa: F403

# =============================================================================
# STANDALONE ISOLATION - STRIP AAAS
# =============================================================================

# Remove AAAS Application
if "somafractalmemory.admin.aaas" in INSTALLED_APPS:  # noqa: F405
    INSTALLED_APPS.remove("somafractalmemory.admin.aaas")  # noqa: F405

# Remove AAAS Middleware
MIDDLEWARE = [  # noqa: F405
    m
    for m in MIDDLEWARE  # noqa: F405
    if "somafractalmemory.admin.aaas" not in m and "UsageTrackingMiddleware" not in m
]

# Standalone defaults
SOMA_NAMESPACE = "standalone"
SOMA_MEMORY_NAMESPACE = "standalone_memory"

# FORCE DATABASES update to ensure Vault injection is respected
# regardless of import order or cache state.
if "SOMA_DB_USER" in os.environ:
    DATABASES["default"]["USER"] = os.environ["SOMA_DB_USER"]  # noqa: F405
if "SOMA_DB_PASSWORD" in os.environ:
    DATABASES["default"]["PASSWORD"] = os.environ["SOMA_DB_PASSWORD"]  # noqa: F405
if "SOMA_DB_HOST" in os.environ:
    DATABASES["default"]["HOST"] = os.environ["SOMA_DB_HOST"]  # noqa: F405
if "SOMA_DB_PORT" in os.environ:
    DATABASES["default"]["PORT"] = os.environ["SOMA_DB_PORT"]  # noqa: F405
if "SOMA_DB_NAME" in os.environ:
    DATABASES["default"]["NAME"] = os.environ["SOMA_DB_NAME"]  # noqa: F405

# Override Redis if injected
if "SOMA_REDIS_HOST" in os.environ:
    SOMA_REDIS_HOST = os.environ["SOMA_REDIS_HOST"]
if "SOMA_REDIS_PORT" in os.environ:
    SOMA_REDIS_PORT = int(os.environ["SOMA_REDIS_PORT"])
if "SOMA_REDIS_PASSWORD" in os.environ:
    SOMA_REDIS_PASSWORD = os.environ["SOMA_REDIS_PASSWORD"]

logger = logging.getLogger(__name__)
logger.info("Loaded STANDALONE settings. Apps: %s", len(INSTALLED_APPS))  # noqa: F405
