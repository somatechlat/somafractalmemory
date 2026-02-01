"""Django URL configuration for SomaFractalMemory.

This module wires the Django Ninja API into Django's URL routing.
100% Django patterns - no FastAPI.
"""

from django.urls import path

from somafractalmemory.api import api

urlpatterns = [
    # Mount Django Ninja API at root
    path("", api.urls),
]
