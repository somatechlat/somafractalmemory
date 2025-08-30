import pytest
from somafractalmemory.core import SomaFractalMemoryEnterprise

def test_init():
    instance = SomaFractalMemoryEnterprise(redis_nodes=[{"host": "localhost", "port": 6379}], qdrant_url="http://localhost:6333")
    assert instance.namespace == "soma_enterprise"
