"""B18: ``k_hop`` is a real traversal depth, not a decorative query param.

Every row and link is created through the real ORM against live Postgres.
The assertions are about graph shape: who is reachable at which hop distance,
and that the hop count on each neighbour is the SHORTEST path length.
"""

from __future__ import annotations

import pytest

from somafractalmemory.admin.core.services import GraphService


def _database_reachable() -> bool:
    try:
        from django.conf import settings

        cfg = settings.DATABASES["default"]
        try:
            import psycopg

            conn = psycopg.connect(
                host=cfg["HOST"],
                port=int(cfg["PORT"]),
                dbname=cfg["NAME"],
                user=cfg["USER"],
                password=cfg["PASSWORD"],
                connect_timeout=2,
            )
        except ImportError:
            import psycopg2

            conn = psycopg2.connect(
                host=cfg["HOST"],
                port=int(cfg["PORT"]),
                dbname=cfg["NAME"],
                user=cfg["USER"],
                password=cfg["PASSWORD"],
                connect_timeout=2,
            )
        conn.close()
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _database_reachable(),
    reason=(
        "Postgres credential refused at the configured SOMA_DB_HOST/SOMA_DB_PORT — "
        "k_hop tests must run against the real database"
    ),
)

# A short chain plus one shortcut. Coordinates are 3-D points; only their
# string keys matter for the graph.
A = (0.0, 0.0, 0.0)
B = (1.0, 0.0, 0.0)
C = (2.0, 0.0, 0.0)
D = (3.0, 0.0, 0.0)
E = (4.0, 0.0, 0.0)
NS = "unit_k_hop"
TENANT = "t-khop"


def _key(coord):
    return ",".join(str(c) for c in coord)


def _build_graph(graph: GraphService) -> None:
    """A->B->C->D->E plus a shortcut A->C.

    With the shortcut, C is 1 hop from A (not 2) — the BFS must report the
    SHORTEST hop count, not the first path it happened to walk.
    """
    for src, dst in ((A, B), (B, C), (C, D), (D, E), (A, C)):
        graph.add_link(src, dst, {"_tenant": TENANT, "link_type": "related"})


@requires_db
@pytest.mark.django_db(transaction=True)
class TestKHopIsRealBreadthFirstSearch:
    def test_k_hop_1_returns_only_direct_neighbours_with_hops_1(self):
        graph = GraphService(namespace=NS)
        _build_graph(graph)

        neighbors = graph.get_neighbors(A, tenant=TENANT, k_hop=1, limit=50)
        by_coord = {_key(n["coordinate"]): n for n in neighbors}

        assert set(by_coord) == {
            _key(B),
            _key(C),
        }, "k_hop=1 must return exactly the direct out-neighbours"
        for n in neighbors:
            assert n["hops"] == 1

    def test_k_hop_2_reaches_the_second_ring(self):
        graph = GraphService(namespace=NS)
        _build_graph(graph)

        neighbors = graph.get_neighbors(A, tenant=TENANT, k_hop=2, limit=50)
        by_coord = {_key(n["coordinate"]): n for n in neighbors}

        assert _key(D) in by_coord, "k_hop=2 must reach D (A->C->D or A->B->C->D)"
        assert (
            by_coord[_key(D)]["hops"] == 2
        ), "D is 2 hops from A; the reported hops must be the shortest path"
        # B is a direct neighbour and must still say 1, not 2.
        assert by_coord[_key(B)]["hops"] == 1

    def test_shortest_hop_wins_over_first_path_found(self):
        """A->C is a shortcut: C must report 1 hop even though A->B->C exists."""
        graph = GraphService(namespace=NS)
        _build_graph(graph)

        neighbors = graph.get_neighbors(A, tenant=TENANT, k_hop=3, limit=50)
        by_coord = {_key(n["coordinate"]): n for n in neighbors}

        assert (
            by_coord[_key(C)]["hops"] == 1
        ), "the shortcut A->C must make C a 1-hop neighbour, not 2-hop"

    def test_k_hop_5_walks_the_whole_chain(self):
        graph = GraphService(namespace=NS)
        _build_graph(graph)

        neighbors = graph.get_neighbors(A, tenant=TENANT, k_hop=5, limit=50)
        keys = {_key(n["coordinate"]) for n in neighbors}

        assert keys == {
            _key(B),
            _key(C),
            _key(D),
            _key(E),
        }, "k_hop=5 must reach the end of the chain and never echo the seed"

    def test_seed_is_never_returned_as_its_own_neighbour(self):
        graph = GraphService(namespace=NS)
        _build_graph(graph)
        # Close a cycle E->A so the seed is reachable from itself.
        graph.add_link(E, A, {"_tenant": TENANT, "link_type": "related"})

        neighbors = graph.get_neighbors(A, tenant=TENANT, k_hop=5, limit=50)
        keys = {_key(n["coordinate"]) for n in neighbors}
        assert _key(A) not in keys, "the seed coordinate is not a neighbour of itself"

    def test_neighbours_carry_hops_even_at_k_hop_1(self):
        graph = GraphService(namespace=NS)
        _build_graph(graph)

        neighbors = graph.get_neighbors(B, tenant=TENANT, k_hop=1, limit=50)
        assert neighbors, "B->C must exist"
        for n in neighbors:
            assert n["hops"] == 1, "every neighbour must carry its hop distance"

    def test_k_hop_bounds_are_enforced(self):
        graph = GraphService(namespace=NS)
        with pytest.raises(ValueError, match="k_hop"):
            graph.get_neighbors(A, tenant=TENANT, k_hop=0)
        with pytest.raises(ValueError, match="k_hop"):
            graph.get_neighbors(A, tenant=TENANT, k_hop=6)
        with pytest.raises(ValueError, match="k_hop"):
            graph.get_neighbors(A, tenant=TENANT, k_hop=-1)

    def test_k_hop_1_and_k_hop_5_bounds_are_inclusive(self):
        graph = GraphService(namespace=NS)
        _build_graph(graph)
        # Both ends of the legal range must be accepted.
        assert graph.get_neighbors(A, tenant=TENANT, k_hop=1, limit=50)
        assert graph.get_neighbors(A, tenant=TENANT, k_hop=5, limit=50)

    def test_link_type_filter_applies_at_every_hop(self):
        graph = GraphService(namespace=NS)
        graph.add_link(A, B, {"_tenant": TENANT, "link_type": "related"})
        graph.add_link(B, C, {"_tenant": TENANT, "link_type": "causes"})
        graph.add_link(A, C, {"_tenant": TENANT, "link_type": "causes"})

        only_related = graph.get_neighbors(A, link_type="related", tenant=TENANT, k_hop=5, limit=50)
        keys = {_key(n["coordinate"]) for n in only_related}
        assert keys == {_key(B)}, (
            "a link_type filter must prune the expansion at every hop, " "not just the first"
        )

    def test_pagination_applies_after_expansion(self):
        graph = GraphService(namespace=NS)
        _build_graph(graph)

        all_neighbors = graph.get_neighbors(A, tenant=TENANT, k_hop=5, limit=50)
        page = graph.get_neighbors(A, tenant=TENANT, k_hop=5, limit=1, offset=1)
        assert len(page) == 1
        assert _key(page[0]["coordinate"]) == _key(all_neighbors[1]["coordinate"])
