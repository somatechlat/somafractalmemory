"""Production settings with strict validation."""

import os

from .base import *  # noqa: F403
from .service_registry import SERVICES

DEBUG = False
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
ENVIRONMENT = "production"

missing_services = SERVICES.validate_required(ENVIRONMENT)
if missing_services:
    raise ValueError(
        f"SomaFractalMemory production startup blocked:\n"
        f"{', '.join(missing_services)}\n"
        f"See .env.example for configuration"
    )
