"""SomaFractalMemory SaaS App.

Provides API key authentication and usage tracking.

Models are imported lazily via get_models() to avoid Django
AppRegistryNotReady errors during startup.
"""


def get_models():
    """Lazy import of models to avoid AppRegistryNotReady errors."""
    from .models import APIKey, UsageRecord

    return APIKey, UsageRecord


__all__ = ["get_models"]
