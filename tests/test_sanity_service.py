"""Module test_sanity_service."""

from django.test import TestCase

from somafractalmemory.services import get_graph_service, get_memory_service


class MemoryServiceSanityTest(TestCase):
    """Memoryservicesanitytest class implementation."""

    def test_store_and_retrieve(self):
        """Execute test store and retrieve."""

        service = get_memory_service(namespace="test_ns")
        coord = (1.0, 2.0, 3.0)
        payload = {"data": "test_memory"}

        # Store
        memory = service.store(coordinate=coord, payload=payload, tenant="tenant_1")
        self.assertEqual(memory.payload, payload)
        self.assertEqual(memory.coordinate, list(coord))

        # Retrieve
        retrieved = service.retrieve(coordinate=coord, tenant="tenant_1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["payload"], payload)

        # Delete
        deleted = service.delete(coordinate=coord, tenant="tenant_1")
        self.assertTrue(deleted)

        # Retrieve after delete
        retrieved_again = service.retrieve(coordinate=coord, tenant="tenant_1")
        self.assertIsNone(retrieved_again)

    def test_search(self):
        """Execute test search."""

        service = get_memory_service(namespace="test_ns")
        service.store((0, 0, 0), {"content": "apple pie"}, tenant="t1")
        service.store((1, 1, 1), {"content": "banana bread"}, tenant="t1")

        results = service.search(query="apple", tenant="t1")
        self.assertTrue(len(results) >= 1)
        self.assertIn("apple", results[0]["payload"]["content"])


class GraphServiceSanityTest(TestCase):
    """Graphservicesanitytest class implementation."""

    def test_link_and_traverse(self):
        """Execute test link and traverse."""

        graph = get_graph_service(namespace="test_ns")
        c1 = (0.0, 0.0, 0.0)
        c2 = (1.0, 1.0, 1.0)

        # Add link
        link = graph.add_link(c1, c2, {"strength": 0.9, "_tenant": "t1"})
        self.assertEqual(link.from_coordinate, list(c1))
        self.assertEqual(link.to_coordinate, list(c2))

        # Neighbors
        neighbors = graph.get_neighbors(c1)
        self.assertEqual(len(neighbors), 1)
        self.assertEqual(neighbors[0]["coordinate"], list(c2))
