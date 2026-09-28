"""Unit tests for the precomputed-embedding contract.

Pure logic tests — no database and no external services required.

Covers:
- Precomputed embeddings are accepted and stored verbatim (never re-hashed).
- HashEmbedder is only the fallback and the record is flagged for lower ranking.
- Search ranking demotes hash-fallback hits below precomputed hits.
- Precomputed embedding dimension is enforced (SOMA_VECTOR_DIM / MEM_EMBED_DIM).
- Tenant scoping precedence (tenant_id body field, X-Soma-Tenant header, auth).
"""

import pytest
from ninja.errors import HttpError
from pydantic import ValidationError

from somafractalmemory.admin.core.services import (
    EMBEDDING_SOURCE_HASH,
    EMBEDDING_SOURCE_PRECOMPUTED,
    EmbeddingDimensionError,
    MemoryService,
    rank_by_embedding_source,
)
from somafractalmemory.api.schemas import MemorySearchRequest, MemoryStoreRequest
from somafractalmemory.api.utils import (
    ensure_embedding_dim,
    get_tenant_from_request,
    safe_parse_coord,
)


class FakeRequest:
    """Minimal request stand-in for tenant-resolution tests."""

    def __init__(self, auth: dict | None = None, headers: dict | None = None):
        self.auth = auth or {}
        self.headers = headers or {}


class TestResolveEmbedding:
    """Precomputed vectors must be used verbatim; hash only as fallback."""

    def setup_method(self):
        self.service = MemoryService(namespace="unit_test")

    def test_precomputed_embedding_stored_verbatim(self):
        vector = [((i % 17) - 8) / 8.0 for i in range(self.service.vector_dim)]
        resolved, source = self.service._resolve_embedding({"text": "hello"}, list(vector))
        assert resolved == vector
        assert source == EMBEDDING_SOURCE_PRECOMPUTED

    def test_precomputed_embedding_not_rehashed(self):
        """The hash of the payload must not leak into a supplied vector."""
        vector = [1.0] + [0.0] * (self.service.vector_dim - 1)
        resolved, _ = self.service._resolve_embedding(
            {"text": "completely different"}, list(vector)
        )
        hashed = self.service.embedder.embed('{"text": "completely different"}')
        assert resolved == vector
        assert resolved != hashed

    def test_fallback_uses_hash_embedder_and_is_flagged(self):
        resolved, source = self.service._resolve_embedding({"text": "hello"}, None)
        expected = self.service.embedder.embed('{"text": "hello"}')
        assert source == EMBEDDING_SOURCE_HASH
        assert resolved == pytest.approx(expected)

    def test_fallback_vector_dimension_matches_config(self):
        resolved, _ = self.service._resolve_embedding({"text": "x"}, None)
        assert len(resolved) == self.service.vector_dim

    def test_dimension_mismatch_raises(self):
        wrong = [0.0] * (self.service.vector_dim + 1)
        with pytest.raises(EmbeddingDimensionError):
            self.service._resolve_embedding({"text": "x"}, wrong)

    def test_non_finite_values_raise(self):
        bad = [0.0] * self.service.vector_dim
        bad[0] = float("nan")
        with pytest.raises(EmbeddingDimensionError):
            self.service._resolve_embedding({"text": "x"}, bad)

    def test_vector_dim_matches_settings(self):
        """Seam contract: vector_dim is the configured SOMA_VECTOR_DIM (fail-hard)."""
        from django.conf import settings

        expected = int(settings.SOMA_VECTOR_DIM)
        assert self.service.vector_dim == expected
        assert expected > 0


class TestRankByEmbeddingSource:
    """Hash-fallback hits must rank below precomputed hits."""

    def test_hash_hit_demoted_below_equal_raw_score(self):
        hits = [
            {"coord": "1.0", "score": 0.9, "embedding_source": EMBEDDING_SOURCE_HASH},
            {"coord": "2.0", "score": 0.9, "embedding_source": EMBEDDING_SOURCE_PRECOMPUTED},
        ]
        ranked = rank_by_embedding_source(hits)
        assert ranked[0]["coord"] == "2.0"
        assert ranked[0]["score"] == pytest.approx(0.9)
        assert ranked[1]["coord"] == "1.0"
        assert ranked[1]["score"] == pytest.approx(0.9 * 0.25)

    def test_precomputed_hit_beats_stronger_hash_noise(self):
        """Raw hash noise (0.8) must not outrank a real hit (0.3) after penalty."""
        hits = [
            {"coord": "1.0", "score": 0.8, "embedding_source": EMBEDDING_SOURCE_HASH},
            {"coord": "2.0", "score": 0.3, "embedding_source": EMBEDDING_SOURCE_PRECOMPUTED},
        ]
        ranked = rank_by_embedding_source(hits)
        assert [h["coord"] for h in ranked] == ["2.0", "1.0"]

    def test_hash_score_is_penalized(self):
        hits = [{"coord": "1.0", "score": 0.8, "embedding_source": EMBEDDING_SOURCE_HASH}]
        ranked = rank_by_embedding_source(hits, hash_penalty=0.25)
        assert ranked[0]["score"] == pytest.approx(0.2)

    def test_precomputed_score_is_raw(self):
        hits = [{"coord": "1.0", "score": 0.8, "embedding_source": EMBEDDING_SOURCE_PRECOMPUTED}]
        ranked = rank_by_embedding_source(hits)
        assert ranked[0]["score"] == pytest.approx(0.8)

    def test_missing_flag_treated_as_hash(self):
        hits = [{"coord": "1.0", "score": 0.8}]
        ranked = rank_by_embedding_source(hits, hash_penalty=0.25)
        assert ranked[0]["score"] == pytest.approx(0.2)

    def test_none_score_treated_as_zero(self):
        hits = [{"coord": "1.0", "score": None, "embedding_source": EMBEDDING_SOURCE_HASH}]
        ranked = rank_by_embedding_source(hits)
        assert ranked[0]["score"] == pytest.approx(0.0)

    def test_sort_is_deterministic_for_ties(self):
        hits = [
            {"coord": "2.0", "score": 0.5, "embedding_source": EMBEDDING_SOURCE_PRECOMPUTED},
            {"coord": "1.0", "score": 0.5, "embedding_source": EMBEDDING_SOURCE_PRECOMPUTED},
        ]
        ranked = rank_by_embedding_source(hits)
        assert [h["coord"] for h in ranked] == ["1.0", "2.0"]

    def test_does_not_mutate_input(self):
        hits = [{"coord": "1.0", "score": 0.8, "embedding_source": EMBEDDING_SOURCE_HASH}]
        rank_by_embedding_source(hits)
        assert hits[0]["score"] == 0.8


class TestEnsureEmbeddingDim:
    """API-level validation of precomputed embeddings."""

    def _dim(self) -> int:
        from django.conf import settings

        return int(settings.SOMA_VECTOR_DIM)

    def test_none_is_allowed(self):
        ensure_embedding_dim(None)

    def test_correct_dim_is_allowed(self):
        ensure_embedding_dim([0.0] * self._dim())

    def test_wrong_dim_raises_400(self):
        dim = self._dim()
        with pytest.raises(HttpError) as exc:
            ensure_embedding_dim([0.0] * (dim + 1))
        assert exc.value.status_code == 400
        assert str(dim) in str(exc.value)

    def test_empty_list_raises_400(self):
        with pytest.raises(HttpError) as exc:
            ensure_embedding_dim([])
        assert exc.value.status_code == 400

    def test_non_finite_raises_400(self):
        bad = [0.0] * self._dim()
        bad[3] = float("inf")
        with pytest.raises(HttpError) as exc:
            ensure_embedding_dim(bad)
        assert exc.value.status_code == 400


class TestTenantScoping:
    """Every operation must resolve the caller's tenant_id."""

    def test_body_tenant_id_wins_in_standalone_mode(self):
        request = FakeRequest(auth={"tenant": "standalone", "auth_type": "standalone_token"})
        assert get_tenant_from_request(request, explicit_tenant="acme") == "acme"

    def test_header_tenant_when_no_body_tenant(self):
        request = FakeRequest(
            auth={"tenant": "standalone", "auth_type": "standalone_token"},
            headers={"X-Soma-Tenant": "acme"},
        )
        assert get_tenant_from_request(request) == "acme"

    def test_standalone_auth_label_fallback(self):
        request = FakeRequest(auth={"tenant": "standalone", "auth_type": "standalone_token"})
        assert get_tenant_from_request(request) == "standalone"

    def test_missing_tenant_raises_400(self):
        """No auth tenant, no body/query tenant, no header → 400 (fail-closed)."""
        request = FakeRequest()
        with pytest.raises(HttpError) as exc:
            get_tenant_from_request(request)
        assert exc.value.status_code == 400

    def test_real_auth_binding_wins_over_explicit_tenant(self):
        request = FakeRequest(auth={"tenant": "bound-tenant", "auth_type": "jwt"})
        assert get_tenant_from_request(request, explicit_tenant="spoofed") == "bound-tenant"

    def test_explicit_tenant_stripped(self):
        request = FakeRequest()
        assert get_tenant_from_request(request, explicit_tenant="  acme  ") == "acme"

    def test_blank_explicit_tenant_falls_through(self):
        request = FakeRequest(headers={"X-Soma-Tenant": "acme"})
        assert get_tenant_from_request(request, explicit_tenant="   ") == "acme"


class TestSchemas:
    """Backward-compatible request shapes with the new seam fields."""

    def test_store_request_accepts_embedding_and_tenant(self):
        req = MemoryStoreRequest(
            coord="0.1,0.2,0.3",
            payload={"text": "hello"},
            memory_type="episodic",
            embedding=[0.0] * 4,
            tenant_id="acme",
        )
        assert req.embedding == [0.0] * 4
        assert req.tenant_id == "acme"

    def test_store_request_old_shape_still_works(self):
        req = MemoryStoreRequest(coord="0.1,0.2,0.3", payload={"text": "hi"})
        assert req.embedding is None
        assert req.tenant_id is None
        assert req.memory_type == "episodic"

    def test_store_request_rejects_unknown_memory_type(self):
        with pytest.raises(ValidationError):
            MemoryStoreRequest(coord="0.1,0.2,0.3", payload={}, memory_type="bogus")

    def test_store_request_accepts_belief_kind(self):
        req = MemoryStoreRequest(coord="0.1,0.2,0.3", payload={}, memory_type="belief")
        assert req.memory_type == "belief"

    def test_search_request_embedding_only(self):
        req = MemorySearchRequest(embedding=[0.1] * 8, tenant_id="acme")
        assert req.query == ""
        assert req.embedding == [0.1] * 8

    def test_search_request_old_shape_still_works(self):
        req = MemorySearchRequest(query="apple", top_k=3)
        assert req.embedding is None
        assert req.offset == 0


class TestCoordValidation:
    """Regression: externally-supplied coords keep the float-tuple contract."""

    def test_valid_coord_parses(self):
        assert safe_parse_coord("0.9,0.8,0.7") == (0.9, 0.8, 0.7)

    def test_malformed_coord_raises_400(self):
        with pytest.raises(HttpError) as exc:
            safe_parse_coord("target-learnbench-3c6c5e16-282e3f50")
        assert exc.value.status_code == 400

    def test_empty_coord_raises_400(self):
        with pytest.raises(HttpError) as exc:
            safe_parse_coord("")
        assert exc.value.status_code == 400
