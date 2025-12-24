"""Django App Configuration for SaaS module."""

from django.apps import AppConfig


class SaasConfig(AppConfig):
    """Configuration for the SaaS application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "somafractalmemory.saas"
    verbose_name = "SomaFractalMemory SaaS"
