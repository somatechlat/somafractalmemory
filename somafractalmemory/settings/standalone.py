"""
Standalone Settings Profile.

Same core as :mod:`somafractalmemory.settings.django_core`, with the
single-tenant namespace defaults this deployment uses. There is no product
overlay to strip any more: the core settings carry no commerce surface.

Usage: DJANGO_SETTINGS_MODULE=somafractalmemory.settings.standalone
"""

import logging

from .django_core import *  # noqa: F403
from .infra import *  # noqa: F403

# Standalone defaults
SOMA_NAMESPACE = "standalone"
SOMA_MEMORY_NAMESPACE = "standalone_memory"

# There is no re-read of ``os.environ`` here any more. There used to be a block
# that re-applied SOMA_DB_* and SOMA_REDIS_* "to ensure Vault injection is
# respected regardless of import order". It existed only because
# ``settings/infra`` wrote Vault credentials into ``os.environ`` *after*
# ``django_core`` had already read them -- so plain ``somafractalmemory.settings``
# silently kept the code defaults while ``settings.standalone`` did not. Two
# behaviours for one configuration is a fork, not a safeguard.
#
# Credentials are now resolved once, in ``django_core._credential``: Vault
# first, the deployment's injection channel second, never a code default.

logger = logging.getLogger(__name__)
logger.info("Loaded STANDALONE settings. Apps: %s", len(INSTALLED_APPS))  # noqa: F405
