"""
SomaFractalMemory SaaS App.

Provides API key authentication and usage tracking.

Note: Do NOT import models here at module level - this causes
AppRegistryNotReady errors during Django startup. Import models
directly where needed instead.
"""

# Don't import models here - causes AppRegistryNotReady
# from .models import APIKey, UsageRecord


# Use lazy import pattern instead
def get_models():
    """Lazy import of models to avoid AppRegistryNotReady errors."""
    from .models import APIKey, UsageRecord

    return APIKey, UsageRecord


__all__ = ["get_models"]
