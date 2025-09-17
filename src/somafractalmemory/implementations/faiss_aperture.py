import math
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import numpy as np

from somafractalmemory.interfaces.storage import IVectorStore

try:
    import faiss
except ImportError:
    faiss = None


@dataclass
class FaissHit:
    """A search result hit, compatible with other store interfaces."""

    id: str
    score: float
    payload: dict


class FaissApertureStore(IVectorStore):
    """
    A production-grade vector store using Faiss for OPQ, IVF, and Residual PQ.
    This implementation uses IndexIDMap2 for robust deletions and supports multiple
    profiles, including IVF-PQ for speed and HNSW for high recall.
    """

    def __init__(
        self, vector_dim: int, profile: str = "fast", config: dict[str, Any] | None = None
    ) -> None:
        if faiss is None:
            raise ImportError(
                "faiss-cpu or faiss-gpu is required for FaissApertureStore. Run 'pip install faiss-cpu'."
            )

        self.d = vector_dim
        self.is_trained = False
        self.collection_name: str = ""
        config = config or {}

        # --- Performance Profiles & Configuration ---
        self.profile = profile

        default_profiles: dict[str, dict[str, Any]] = {
            "fast": {
                "index_type": "ivfpq",
                "nlist": 4096,
                "nprobe": 16,
                "m": 8,
                "nbits": 8,
                "rerank_k": 128,
            },
            "balanced": {
                "index_type": "ivfpq",
                "nlist": 4096,
                "nprobe": 32,
                "m": 8,
                "nbits": 8,
                "rerank_k": 256,
            },
            "high_recall": {
                "index_type": "hnsw",
                "hnsw_m": 64,
                "ef_construction": 128,
                "ef_search": 64,
                "rerank_k": 256,
            },
        }

        # Start with profile defaults, then override with user-provided config
        params: dict[str, Any] = default_profiles.get(profile, {}).copy()
        params.update(config)

        # Set attributes from the final parameters
        self.index_type = params.get("index_type")
        if not self.index_type:
            raise ValueError(f"index_type must be specified for profile '{profile}'")

        if self.index_type == "ivfpq":
            self.nlist = int(params.get("nlist", 4096))
            self.nprobe = int(params.get("nprobe", 16))
            self.m = int(params.get("m", 8))
            self.nbits = int(params.get("nbits", 8))
            # Fallback flag: when too few training points, use Flat index wrapped in IDMap2
            self._fallback_small = False
        elif self.index_type == "hnsw":
            self.hnsw_m = int(params.get("hnsw_m", 64))
            self.ef_construction = int(params.get("ef_construction", 128))
            self.ef_search = int(params.get("ef_search", 64))
        else:
            raise ValueError(f"Unsupported index_type: {self.index_type}")

        self.rerank_k = int(params.get("rerank_k", 128))

        # GPU configuration
        self.gpu_id = params.get("gpu_id")

        # Faiss index structures (avoid type annotations referencing faiss types)
        self.opq_matrix = None
        self.index = None

        # Stores for re-ranking, payloads, and ID mapping
        self._vector_store: dict[str, np.ndarray] = {}
        self._payload_store: dict[str, dict] = {}
        self._string_to_int_id: dict[str, int] = {}
        self._int_to_string_id: dict[int, str] = {}
        self._next_int_id = 0

    # ---------------- Internal helpers ----------------
    def _normalize_vector(self, v: Any) -> np.ndarray:
        """Return a 1D float32 vector of length self.d by flattening and pad/truncate.

        - Accepts list, tuple, or numpy array inputs.
        - Replaces NaN/inf with zeros.
        """
        arr = np.asarray(v, dtype=np.float32).reshape(-1)
        # Replace non-finite with zero
        if not np.isfinite(arr).all():
            arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)
        cur = arr.shape[0]
        if cur == self.d:
            return arr
        if cur < self.d:
            pad = np.zeros(self.d - cur, dtype=np.float32)
            return np.concatenate([arr, pad], axis=0)
        # cur > self.d
        return arr[: self.d]

    def setup(self, vector_dim: int, namespace: str) -> None:
        if self.d != vector_dim:
            raise ValueError(
                f"Store initialized with dim {self.d} but setup called with {vector_dim}"
            )
        self.collection_name = namespace

    def _initialize_index(self) -> None:
        """Initializes the Faiss index structure."""
        assert faiss is not None, "FAISS must be installed to initialize the index"
        if self.index_type == "ivfpq":
            if getattr(self, "_fallback_small", False):
                # Use a simple Flat index with ID mapping; no training needed
                flat = faiss.IndexFlatL2(self.d)
                self.index = faiss.IndexIDMap2(flat)
            else:
                self.opq_matrix = faiss.OPQMatrix(self.d, self.m)
                quantizer = faiss.IndexFlatL2(self.d)
                ivf_index = faiss.IndexIVFPQ(quantizer, self.d, self.nlist, self.m, self.nbits)
                id_mapped_index = faiss.IndexIDMap2(ivf_index)
                self.index = faiss.IndexPreTransform(self.opq_matrix, id_mapped_index)
        elif self.index_type == "hnsw":
            hnsw_index = faiss.IndexHNSWFlat(self.d, self.hnsw_m, faiss.METRIC_L2)
            hnsw_index.hnsw.efConstruction = self.ef_construction
            self.index = faiss.IndexIDMap2(hnsw_index)

        if self.gpu_id is not None and self.index:
            try:
                StdGpuRes = getattr(faiss, "StandardGpuResources", None)
                cpu_to_gpu = getattr(faiss, "index_cpu_to_gpu", None)
                if StdGpuRes is None or cpu_to_gpu is None:
                    raise AttributeError("faiss-gpu symbols not available")
                res = StdGpuRes()
                self.index = cpu_to_gpu(res, self.gpu_id, self.index)
            except AttributeError as e:
                raise ImportError(
                    "faiss-gpu is required for GPU support. Please install it."
                ) from e
            except Exception as e:
                raise RuntimeError(f"Failed to move index to GPU {self.gpu_id}: {e}") from e

    def _train(self, vectors: np.ndarray) -> None:
        """Trains the OPQ matrix and IVF-PQ index."""
        if self.index_type != "ivfpq":
            self.is_trained = True  # HNSW doesn't require training
            return

        if getattr(self, "_fallback_small", False):
            # No training necessary for Flat fallback
            if self.index is None:
                self._initialize_index()
            self.is_trained = True
            return

        if self.index is None:
            self._initialize_index()

        # The index is a IndexPreTransform, we need to train the sub-index
        if self.index:
            try:
                # Validate input vectors before training
                if vectors is None or len(vectors) == 0:
                    raise ValueError("Cannot train FAISS index with empty or None vectors")

                # Ensure vectors are 2D and have correct dimension
                if vectors.ndim == 1:
                    vectors = vectors.reshape(1, -1)
                elif vectors.ndim != 2:
                    raise ValueError(f"Vectors must be 2D array, got {vectors.ndim}D")

                # Normalize dims if needed (pad/truncate), to be robust to upstream variance
                if vectors.shape[1] != self.d:
                    vectors = np.vstack([self._normalize_vector(v) for v in vectors])

                # Check for NaN or infinite values
                if not np.isfinite(vectors).all():
                    raise ValueError("Training vectors contain NaN or infinite values")

                # Train the OPQ/IVF-PQ pipeline. Note: faiss train() returns None on success.
                if hasattr(self.index, "train"):
                    _ = self.index.train(vectors)  # type: ignore
                else:
                    raise RuntimeError("FAISS index does not support training")

                self.is_trained = True

            except Exception as e:
                # Log the error and fall back to Flat index if training fails
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"FAISS training failed: {e}. Falling back to Flat index.")

                # Reset to fallback mode
                self._fallback_small = True
                self.index = None
                self._initialize_index()
                self.is_trained = True
        else:
            raise TypeError("Index is not of expected type IndexPreTransform")

    def upsert(self, points: list[dict[str, Any]]) -> None:
        if not points:
            return

        # --- Step 1: Buffer new points and decide on indexing strategy ---
        ids_to_index: list[str] = []
        vectors_to_index: np.ndarray | None = None

        if (not self.is_trained) and self.index_type == "ivfpq":
            # Buffer all incoming points until we have enough to train (>= nlist)
            for p in points:
                self._vector_store[p["id"]] = self._normalize_vector(p["vector"])  # enforce dim
                self._payload_store[p["id"]] = p["payload"]

            if len(self._vector_store) < self.nlist:
                return  # keep buffering

            # Enough data accumulated: adapt parameters and train
            all_vectors = np.vstack(list(self._vector_store.values())).astype(np.float32)
            nx = int(all_vectors.shape[0])
            # If not enough points to train PQ (needs at least 2^nbits), fall back to Flat
            if nx < (1 << int(self.nbits)):
                self._fallback_small = True
                self.index = None
            else:
                # Clamp IVF lists to available training points
                if nx < self.nlist:
                    self.nlist = max(1, nx)
                    self.index = None
                # Ensure PQ has enough training points: 2^nbits <= nx
                max_bits = int(math.floor(math.log2(nx)))
                effective_nbits = max(4, min(int(self.nbits), max_bits))
                if effective_nbits != self.nbits:
                    self.nbits = effective_nbits
                    self.index = None
            # (Re-)initialize index if needed after parameter adjustments
            if self.index is None:
                self._initialize_index()
            self._train(all_vectors)
            ids_to_index = list(self._vector_store.keys())
            vectors_to_index = all_vectors
        else:
            # Index is already trained or is HNSW, so just index the new points
            for p in points:
                self._vector_store[p["id"]] = self._normalize_vector(p["vector"])  # enforce dim
                self._payload_store[p["id"]] = p["payload"]
            ids_to_index = [p["id"] for p in points]
            # Build a 2D matrix with guaranteed dimension
            vectors_to_index = np.vstack([self._vector_store[i] for i in ids_to_index]).astype(
                np.float32
            )

        if self.index is None:
            self._initialize_index()
            if self.index_type == "hnsw":
                # HNSW requires no training; mark as ready on first initialization
                self.is_trained = True

        if not ids_to_index or vectors_to_index is None or len(vectors_to_index) == 0:
            return

        # --- Step 2: Generate integer IDs and add to the Faiss index ---
        int_ids: list[int] = []
        for string_id in ids_to_index:
            if string_id not in self._string_to_int_id:
                self._string_to_int_id[string_id] = self._next_int_id
                self._int_to_string_id[self._next_int_id] = string_id
                self._next_int_id += 1
            int_ids.append(self._string_to_int_id[string_id])

        if vectors_to_index.ndim == 1:
            vectors_to_index = vectors_to_index.reshape(1, -1)

        if self.index is not None and len(vectors_to_index) > 0:
            self.index.add_with_ids(vectors_to_index, np.array(int_ids, dtype=np.int64))  # type: ignore

    def search(self, vector: list[float], top_k: int) -> list[FaissHit]:
        if not self.is_trained or self.index is None or self.index.ntotal == 0:
            return []

        # Normalize query vector to correct dimensionality
        query_vec = self._normalize_vector(vector).astype("float32", copy=False)
        query_vector = query_vec.reshape(1, -1)

        # Stage 1: Wide Aperture Scan (Approximate Search)
        candidate_k = max(top_k * 10, self.rerank_k)

        if self.index_type == "ivfpq":
            assert faiss is not None, "FAISS must be installed to search the index"
            # Get the underlying IVF index to set nprobe
            try:
                pretransform_index = faiss.downcast_index(self.index)  # type: ignore
                # If PreTransform, unwrap once
                id_map_index = getattr(pretransform_index, "index", pretransform_index)
                id_map_index = faiss.downcast_index(id_map_index)  # type: ignore
                # Unwrap to IVF if present (Flat index won't have nested index)
                ivf_index = getattr(id_map_index, "index", id_map_index)
                ivf_index = faiss.downcast_index(ivf_index)  # type: ignore
                # Ensure nprobe does not exceed nlist if available
                current_nlist = int(getattr(ivf_index, "nlist", self.nlist))
                if hasattr(ivf_index, "nprobe"):
                    ivf_index.nprobe = min(self.nprobe, current_nlist)
            except Exception:
                # Fallback index doesn't support nprobe; that's fine
                pass
        elif self.index_type == "hnsw":
            assert faiss is not None, "FAISS must be installed to search the index"
            id_map_index = faiss.downcast_index(self.index)  # type: ignore
            hnsw_index = faiss.downcast_index(id_map_index.index)  # type: ignore
            hnsw_index.hnsw.efSearch = self.ef_search

        distances, int_ids = self.index.search(query_vector, candidate_k)  # type: ignore

        # Stage 2: High-Fidelity Re-ranking (Exact Search on original vectors)
        valid_mask = int_ids[0] != -1
        candidate_int_ids = int_ids[0][valid_mask]

        if len(candidate_int_ids) == 0:
            return []

        # Map integer IDs back to string IDs and fetch full vectors, keeping IDs and vectors aligned
        filtered_ids: list[str] = []
        filtered_vecs: list[np.ndarray] = []
        for int_id in candidate_int_ids:
            sid = self._int_to_string_id.get(int_id)
            if sid is None:
                continue
            v = self._vector_store.get(sid)
            if v is None:
                continue
            filtered_ids.append(sid)
            filtered_vecs.append(self._normalize_vector(v))
        if not filtered_vecs:
            return []
        candidate_vectors = np.vstack(filtered_vecs).astype(np.float32)

        if len(candidate_vectors) == 0:
            return []

        # Calculate exact L2 distance (squared for speed)
        diff = candidate_vectors - query_vector  # (n,d) - (1,d)
        exact_distances_sq = np.sum(diff**2, axis=1)

        # Combine and sort by exact distance, preserving alignment
        reranked_results = sorted(
            zip(exact_distances_sq, filtered_ids, strict=False), key=lambda x: x[0]
        )

        # Build the final list of hits
        final_hits: list[FaissHit] = []
        for dist_sq, string_id in reranked_results[:top_k]:
            final_hits.append(
                FaissHit(
                    id=string_id,
                    score=math.sqrt(dist_sq),  # Return L2, not squared L2
                    payload=self._payload_store[string_id],
                )
            )
        return final_hits

    def delete(self, ids: list[str]) -> None:
        if not self.is_trained or self.index is None:
            return
        assert faiss is not None, "FAISS must be installed to delete from the index"

        int_ids_to_remove = [
            self._string_to_int_id[sid] for sid in ids if sid in self._string_to_int_id
        ]
        if int_ids_to_remove:
            # Try to find an index object that supports remove_ids
            target = None
            try:
                if self.index_type == "ivfpq":
                    pre = faiss.downcast_index(self.index)  # type: ignore
                    # If PreTransform, unwrap; else it might already be IDMap2
                    target = getattr(pre, "index", pre)
                else:
                    target = faiss.downcast_index(self.index)  # type: ignore
            except Exception:
                target = self.index

            # If target has nested .index (IDMap2), we need to call remove_ids on the IDMap2 wrapper
            try:
                if hasattr(target, "remove_ids"):
                    target.remove_ids(np.array(int_ids_to_remove, dtype=np.int64))
                elif hasattr(self.index, "remove_ids"):
                    self.index.remove_ids(np.array(int_ids_to_remove, dtype=np.int64))
            except Exception:
                # Best-effort; some underlying types may not support deletion
                pass

        for point_id in ids:
            self._vector_store.pop(point_id, None)
            self._payload_store.pop(point_id, None)
            int_id = self._string_to_int_id.pop(point_id, None)
            if int_id is not None:
                self._int_to_string_id.pop(int_id, None)

    def scroll(self) -> Iterator[Any]:
        for string_id, payload in self._payload_store.items():
            yield FaissHit(id=string_id, score=0.0, payload=payload)

    def health_check(self) -> bool:
        return self.index is not None
