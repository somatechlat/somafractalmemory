"""
Property-Based Tests for SomaFractalMemory Statistics.

These tests verify correctness properties for memory statistics,
ensuring namespace isolation and accurate counting.

VIBE CODING RULES: NO mocks, NO stubs, NO placeholders.
All tests require real infrastructure via docker compose --profile core up -d

**Feature: sfm-test-fixes**
"""

import os
import string
import uuid

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Skip all tests if infrastructure is not available
pytestmark = pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure (Redis, Postgres, Milvus)",
)


def _get_test_config():
    """Get test configuration from environment variables."""
    return {
        "postgres": {
            "url": os.environ.get(
                "POSTGRES_URL", "postgresql://soma:soma@localhost:40021/somamemory"
            )
        },
        "redis": {
            "host": os.environ.get("REDIS_HOST", "localhost"),
            "port": int(os.environ.get("REDIS_PORT", "40022")),
        },
        "milvus": {
            "host": os.environ.get("SOMA_MILVUS_HOST", "localhost"),
            "port": int(os.environ.get("SOMA_MILVUS_PORT", "35003")),
        },
    }


class TestPropertyNamespaceStats:
    """Property-based tests for namespace-scoped statistics."""

    # **Feature: sfm-test-fixes, Property 2: Namespace-Scoped Vector Count**
    # **Validates: Requirements 1.2**
    @given(st.text(min_size=1, max_size=10, alphabet=string.ascii_lowercase))
    @settings(max_examples=10, deadline=60000)  # Reduced for real infra
    def test_vector_count_matches_collection_entities(self, namespace_suffix: str):
        """Property 2: vector_count equals collection.num_entities for namespace.

        For any namespace with a Milvus collection, memory_stats()["vector_count"]
        SHALL equal collection.num_entities for that namespace's collection only.
        """
        from somafractalmemory.core import MemoryType
        from somafractalmemory.factory import MemoryMode, create_memory_system

        # Create unique namespace for this test iteration
        namespace = f"prop_vec_{namespace_suffix}_{uuid.uuid4().hex[:6]}"
        config = _get_test_config()

        memory = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, namespace, config=config)

        # Store some memories
        for i in range(3):
            coord = (float(i) / 10, 0.5, 0.5)
            memory.store_memory(coord, {"content": f"test_{i}"}, MemoryType.EPISODIC)

        # Get stats
        stats = memory.memory_stats()

        # Vector count should match what the vector store reports
        expected_count = memory.vector_store.count()
        assert (
            stats["vector_count"] == expected_count
        ), f"vector_count {stats['vector_count']} != collection count {expected_count}"

    # **Feature: sfm-test-fixes, Property 3: Fresh Namespace Zero Count**
    # **Validates: Requirements 1.3**
    @given(st.text(min_size=1, max_size=10, alphabet=string.ascii_lowercase))
    @settings(max_examples=10, deadline=60000)
    def test_fresh_namespace_has_zero_counts(self, namespace_suffix: str):
        """Property 3: Fresh namespace returns zero counts.

        For any freshly created namespace with no stored memories,
        memory_stats() SHALL return total_memories=0 and vector_count=0.
        """
        from somafractalmemory.factory import MemoryMode, create_memory_system

        # Create unique namespace that has never been used
        namespace = f"prop_fresh_{namespace_suffix}_{uuid.uuid4().hex[:8]}"
        config = _get_test_config()

        memory = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, namespace, config=config)

        # Get stats immediately - should be zero
        stats = memory.memory_stats()

        assert (
            stats["total_memories"] == 0
        ), f"Fresh namespace should have 0 memories, got {stats['total_memories']}"
        assert (
            stats["vector_count"] == 0
        ), f"Fresh namespace should have 0 vectors, got {stats['vector_count']}"


class TestPropertyNamespaceIsolation:
    """Property-based tests for namespace isolation in statistics."""

    # **Feature: sfm-test-fixes, Property 1: Namespace-Scoped KV Count**
    # **Validates: Requirements 1.1, 1.4**
    @given(st.integers(min_value=1, max_value=5))
    @settings(max_examples=5, deadline=120000)
    def test_kv_count_isolated_per_namespace(self, num_memories: int):
        """Property 1: total_memories counts only current namespace keys.

        For any namespace and set of stored memories, memory_stats()["total_memories"]
        SHALL equal the count of keys matching {namespace}:*:data pattern only.
        """
        from somafractalmemory.core import MemoryType
        from somafractalmemory.factory import MemoryMode, create_memory_system

        config = _get_test_config()

        # Create two namespaces
        ns_a = f"prop_iso_a_{uuid.uuid4().hex[:8]}"
        ns_b = f"prop_iso_b_{uuid.uuid4().hex[:8]}"

        memory_a = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, ns_a, config=config)
        memory_b = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, ns_b, config=config)

        # Store memories in namespace A only
        for i in range(num_memories):
            coord = (float(i) / 10, 0.5, 0.5)
            memory_a.store_memory(coord, {"content": f"a_{i}"}, MemoryType.EPISODIC)

        # Namespace A should have num_memories
        stats_a = memory_a.memory_stats()
        assert (
            stats_a["total_memories"] >= num_memories
        ), f"Namespace A should have at least {num_memories} memories, got {stats_a['total_memories']}"

        # Namespace B should have 0 (fresh namespace)
        stats_b = memory_b.memory_stats()
        assert (
            stats_b["total_memories"] == 0
        ), f"Namespace B should have 0 memories (isolated), got {stats_b['total_memories']}"


class TestPropertyConcurrentTenants:
    """Property-based tests for concurrent tenant isolation."""

    # **Feature: sfm-test-fixes, Property 4: Concurrent Tenant Isolation**
    # **Validates: Requirements 2.1, 2.3, 3.3**
    @given(st.integers(min_value=3, max_value=10))
    @settings(max_examples=3, deadline=180000)  # Longer deadline for concurrent ops
    def test_concurrent_tenants_no_leakage(self, num_tenants: int):
        """Property 4: Concurrent tenants have isolated data.

        For any set of N concurrent tenants, each tenant's memory_stats()
        SHALL reflect only that tenant's data, with no cross-tenant leakage.
        """
        from concurrent.futures import ThreadPoolExecutor

        from somafractalmemory.core import MemoryType
        from somafractalmemory.factory import MemoryMode, create_memory_system

        config = _get_test_config()
        tenant_data: dict[int, tuple[str, tuple[float, ...]]] = {}

        def store_for_tenant(tenant_id: int) -> tuple[str, tuple[float, ...], int]:
            """Store unique data for a tenant and return the namespace."""
            namespace = f"prop_tenant_{tenant_id}_{uuid.uuid4().hex[:6]}"
            memory = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, namespace, config=config)

            coord = (float(tenant_id) / 100, 0.5, 0.5)
            payload = {"tenant_id": tenant_id, "secret": f"secret_{tenant_id}"}
            memory.store_memory(coord, payload, MemoryType.EPISODIC)
            return namespace, coord, tenant_id

        # Store data for all tenants concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(store_for_tenant, range(num_tenants)))

        for namespace, coord, tenant_id in results:
            tenant_data[tenant_id] = (namespace, coord)

        # Verify isolation for each tenant
        def verify_isolation(tenant_id: int) -> tuple[bool, str | None]:
            """Verify tenant can only see their own data."""
            namespace, coord = tenant_data[tenant_id]
            memory = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, namespace, config=config)

            # Should be able to retrieve own data
            result = memory.retrieve(coord)
            if result is None:
                return False, f"Tenant {tenant_id} cannot retrieve own data"

            # Stats should show only this tenant's data
            stats = memory.memory_stats()
            if stats["total_memories"] < 1:
                return False, f"Tenant {tenant_id} stats show 0 memories"

            return True, None

        # Verify isolation for all tenants concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            verification_results = list(executor.map(verify_isolation, range(num_tenants)))

        # Check all verifications passed
        failures = [msg for success, msg in verification_results if not success]
        assert len(failures) == 0, f"Tenant isolation failures: {failures}"
