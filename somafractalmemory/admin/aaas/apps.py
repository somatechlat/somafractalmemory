"""Django App Configuration for AAAS module."""

from django.apps import AppConfig


class AaasConfig(AppConfig):
    """Configuration for the AAAS application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "somafractalmemory.admin.aaas"
    verbose_name = "SomaFractalMemory AAAS"
