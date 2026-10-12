"""API request bounds — top_k / offset / limit must reject DoS-sized pages.

An unbounded ``top_k`` or ``limit`` lets one request pull an entire store (or
an entire adjacency set) into a response body. The bounds mirror the somabrain
pattern in ``somabrain/api/memory/models.py`` (``Field(3, ge=1, le=50)``).

VIBE Coding Rules:
- NO mocks, only pure Pydantic validation
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from somafractalmemory.api.schemas import MemorySearchRequest


class TestMemorySearchRequestBounds:
    """``top_k`` is [1, 200]; ``offset`` is [0, ∞)."""

    def test_defaults_are_inside_bounds(self):
        req = MemorySearchRequest(query="q")
        assert req.top_k == 5
        assert req.offset == 0

    def test_top_k_accepts_lower_bound(self):
        assert MemorySearchRequest(query="q", top_k=1).top_k == 1

    def test_top_k_accepts_upper_bound(self):
        assert MemorySearchRequest(query="q", top_k=200).top_k == 200

    def test_top_k_rejects_zero(self):
        with pytest.raises(ValidationError):
            MemorySearchRequest(query="q", top_k=0)

    def test_top_k_rejects_negative(self):
        with pytest.raises(ValidationError):
            MemorySearchRequest(query="q", top_k=-1)

    def test_top_k_rejects_above_ceiling(self):
        with pytest.raises(ValidationError):
            MemorySearchRequest(query="q", top_k=201)

    def test_top_k_rejects_absurd_page_size(self):
        # The DoS shape this bound exists to stop.
        with pytest.raises(ValidationError):
            MemorySearchRequest(query="q", top_k=10_000_000)

    def test_offset_accepts_zero(self):
        assert MemorySearchRequest(query="q", offset=0).offset == 0

    def test_offset_accepts_large_positive(self):
        # Offset is unbounded above on purpose: paging deep into a result set
        # is legal. Only a negative offset is nonsense.
        assert MemorySearchRequest(query="q", offset=10_000).offset == 10_000

    def test_offset_rejects_negative(self):
        with pytest.raises(ValidationError):
            MemorySearchRequest(query="q", offset=-1)


class TestQueryParameterBounds:
    """GET route query params carry the same bounds as the POST body.

    ``ninja.Query`` is a ``pydantic.FieldInfo``; its ``Ge``/``Le`` metadata is
    what the OpenAPI schema and the request validator both consume.
    """

    @staticmethod
    def _bounds(field_info) -> tuple[int | None, int | None]:
        """(ge, le) pulled from the FieldInfo metadata chain."""
        ge = le = None
        for item in field_info.metadata:
            if type(item).__name__ == "Ge":
                ge = item.ge
            elif type(item).__name__ == "Le":
                le = item.le
        return ge, le

    def test_search_get_top_k_and_offset_are_bounded(self):
        from somafractalmemory.api.routers.search import search_memories_get

        params = inspect.signature(search_memories_get).parameters
        assert self._bounds(params["top_k"].default) == (1, 200)
        assert self._bounds(params["offset"].default)[0] == 0

    def test_graph_neighbors_limit_and_offset_are_bounded(self):
        from somafractalmemory.api.routers.graph import get_graph_neighbors

        params = inspect.signature(get_graph_neighbors).parameters
        assert self._bounds(params["limit"].default) == (1, 200)
        assert self._bounds(params["offset"].default)[0] == 0
