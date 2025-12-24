"""
SomaFractalMemory - A coordinate-based fractal memory system.

This package provides a Django-based API for storing and retrieving memories
using coordinate vectors. It supports:

- Memory CRUD operations with coordinate-based addressing
- Graph relationships between memory coordinates
- Vector similarity search via Milvus
- Multi-tenancy with namespace isolation

Architecture:
    - Django 5.2 + Django Ninja for the API layer
    - PostgreSQL for persistent storage (via Django ORM)
    - Redis for caching
    - Milvus for vector similarity search

Modules:
    models      Django ORM models (Memory, GraphLink, etc.)
    services    Business logic (MemoryService)
    settings    Django configuration
    api         Django Ninja API (routers, schemas)

Usage:
    # Start via Docker Compose
    docker compose --profile core up -d

    # Or run Django development server
    python manage.py runserver

Example:
    >>> import requests
    >>> response = requests.post(
    ...     "http://localhost:9595/memories",
    ...     json={"coord": "1.0,2.0,3.0", "payload": {"content": "Hello"}},
    ...     headers={"Authorization": "Bearer YOUR_TOKEN"}
    ... )
    >>> response.json()
    {'coord': '1.0,2.0,3.0', 'memory_type': 'episodic'}

Version: 0.2.0
License: MIT
"""

__version__ = "0.2.0"
__author__ = "SomaTech LAT"
__all__ = ["__version__"]
