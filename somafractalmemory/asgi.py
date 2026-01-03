"""ASGI config for SomaFractalMemory.

100% Django patterns.
Run via daphne or gunicorn:
    daphne somafractalmemory.asgi:application -b 0.0.0.0 -p 9595
    gunicorn somafractalmemory.asgi:application -k daphne.server.DaphneServer --bind 0.0.0.0:9595
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somafractalmemory.settings")

# Initialize Django ASGI application early
django_asgi_app = get_asgi_application()

# Import Ninja API after Django is set up

# Standard Django ASGI application
application = django_asgi_app
