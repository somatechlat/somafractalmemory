import numpy as np
import pytest

try:
    from somafractalmemory.implementations.faiss_aperture import FaissApertureStore

    faiss_available = True
except ImportError:
    faiss_available = False

pytestmark = pytest.mark.skipif(not faiss_available, reason="faiss-cpu not installed")


# Parameterize the fixture to test both profiles
@pytest.fixture(params=["fast", "balanced", "high_recall"])
def faiss_aperture_store(request):
    dim = 64
    profile = request.param
    store = FaissApertureStore(vector_dim=dim, profile=profile)
    # Override nlist for faster testing, especially for the balanced profile
    store.nlist = 4
    store.setup(vector_dim=dim, namespace=f"test_faiss_aperture_{profile}")
    return store


def test_faiss_aperture_init(faiss_aperture_store):
    assert faiss_aperture_store is not None
    assert faiss_aperture_store.d == 64
    assert faiss_aperture_store.profile in ["fast", "balanced", "high_recall"]


def test_faiss_aperture_upsert_and_search(faiss_aperture_store):
    # Generate enough data to train
    num_vectors = 200
    dim = faiss_aperture_store.d
    vectors = np.random.rand(num_vectors, dim).astype("float32")
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)  # Normalize for L2

    points_to_upsert = [
        {"id": f"id_{i}", "vector": vectors[i].tolist(), "payload": {"index": i}}
        for i in range(num_vectors)
    ]

    faiss_aperture_store.upsert(points_to_upsert)

    # HNSW is "trained" immediately, IVF needs to meet nlist
    if faiss_aperture_store.index_type == "ivfpq":
        assert faiss_aperture_store.is_trained
    else:
        assert faiss_aperture_store.is_trained is True
    assert faiss_aperture_store.index is not None
    assert faiss_aperture_store.index.ntotal == num_vectors

    # Search for a known vector
    query_vector = vectors[42].tolist()
    results = faiss_aperture_store.search(query_vector, top_k=1)

    assert len(results) == 1
    assert results[0].id == "id_42"
    assert results[0].payload["index"] == 42
    assert results[0].score < 1e-5  # L2 distance for identical vector


def test_faiss_aperture_delete(faiss_aperture_store):
    dim = faiss_aperture_store.d
    # Add enough points to train the index first
    training_points = [
        {"id": f"train_{i}", "vector": np.random.rand(dim).tolist(), "payload": {}}
        for i in range(10)
    ]
    faiss_aperture_store.upsert(training_points)
    if faiss_aperture_store.index_type == "ivfpq":
        assert faiss_aperture_store.is_trained

    # Add the point to be deleted
    vec_to_del = np.random.rand(dim).astype("float32")
    vec_to_del /= np.linalg.norm(vec_to_del)
    point_to_del = {
        "id": "id_del",
        "vector": vec_to_del.tolist(),
        "payload": {"data": "to_delete"},
    }
    faiss_aperture_store.upsert([point_to_del])

    # Verify it exists
    assert "id_del" in faiss_aperture_store._payload_store
    results_before = faiss_aperture_store.search(vec_to_del.tolist(), top_k=1)
    assert len(results_before) > 0 and results_before[0].id == "id_del"

    # Delete it
    faiss_aperture_store.delete(["id_del"])

    # Verify it's gone from internal stores and search results
    assert "id_del" not in faiss_aperture_store._payload_store
    assert "id_del" not in faiss_aperture_store._string_to_int_id
    results_after = faiss_aperture_store.search(vec_to_del.tolist(), top_k=1)
    assert len(results_after) == 0 or results_after[0].id != "id_del"


def test_faiss_aperture_buffering_and_training(faiss_aperture_store):
    if faiss_aperture_store.profile == "high_recall":
        pytest.skip("HNSW does not require training, so no buffering logic.")

    """Tests that the store correctly buffers points until enough are present to train."""
    dim = faiss_aperture_store.d
    nlist = faiss_aperture_store.nlist

    # Add fewer points than nlist
    num_buffered = nlist - 1
    buffered_points = [
        {"id": f"buf_{i}", "vector": np.random.rand(dim).tolist(), "payload": {}}
        for i in range(num_buffered)
    ]
    faiss_aperture_store.upsert(buffered_points)

    # Assert index is not trained yet, but points are buffered
    assert not faiss_aperture_store.is_trained
    assert faiss_aperture_store.index is None
    assert len(faiss_aperture_store._vector_store) == num_buffered

    # Add one more point to trigger training
    trigger_point = [{"id": "trigger", "vector": np.random.rand(dim).tolist(), "payload": {}}]
    faiss_aperture_store.upsert(trigger_point)

    # Assert index is now trained and contains all points
    assert faiss_aperture_store.is_trained
    assert faiss_aperture_store.index is not None
    assert faiss_aperture_store.index.ntotal == nlist
    assert len(faiss_aperture_store._vector_store) == nlist


def test_faiss_aperture_search_empty_store(faiss_aperture_store):
    """Tests that searching an empty store returns an empty list without errors."""
    dim = faiss_aperture_store.d
    query_vector = np.random.rand(dim).tolist()
    results = faiss_aperture_store.search(query_vector, top_k=5)
    assert results == []


def test_faiss_aperture_custom_config_override():
    """Tests that profile defaults can be overridden by the config dict."""
    dim = 64
    custom_config = {
        "nprobe": 99,
        "rerank_k": 555,
    }
    store = FaissApertureStore(vector_dim=dim, profile="fast", config=custom_config)

    # Check that the custom values were applied, not the 'fast' profile defaults
    assert store.nprobe == 99
    assert store.rerank_k == 555

    # Check that other 'fast' profile defaults are still there
    assert store.index_type == "ivfpq"
    assert store.nlist == 4096
