"""WSGI config for SomaFractalMemory.

100% Django - NO uvicorn.
Use with gunicorn:
    gunicorn somafractalmemory.wsgi:application --bind 0.0.0.0:9595
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somafractalmemory.settings")

application = get_wsgi_application()
