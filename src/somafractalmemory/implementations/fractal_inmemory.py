import math
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional

import numpy as np

from somafractalmemory.interfaces.storage import IVectorStore


@dataclass
class _Hit:
    id: str
    score: float | None
    payload: dict


class FractalInMemoryVectorStore(IVectorStore):
    """Hierarchical in-memory ANN with exact rerank, NumPy-only.

    - Coarse centroids + inverted lists; beam search over top centroids.
    - Candidate cap + exact cosine rerank for final top_k.
    - Rebuild triggers by size delta or time interval; thread-safe swaps.
    - Memory-only; no external deps beyond NumPy.
    """

    def __init__(
        self,
        centroids: Optional[int] = None,
        beam_width: int = 4,
        max_candidates: int = 1024,
        rebuild_enabled: bool = True,
        rebuild_size_delta: float = 0.1,
        rebuild_interval_seconds: int = 600,
    ) -> None:
        self._vector_dim = 0
        self.collection_name = ""
        self._lock = threading.RLock()
        self._points: Dict[str, dict] = {}
        self._vectors: Optional[np.ndarray] = None  # [N, D]
        self._ids: List[str] = []
        self._id_to_idx: Dict[str, int] = {}
        self._tombstones: set[str] = set()

        # Index structures
        self._centroids: Optional[np.ndarray] = None  # [C, D]
        self._assignments: Optional[np.ndarray] = None  # [N]
        self._lists: List[List[int]] = []  # indices per centroid

        # Config
        self._requested_centroids = centroids  # may be None (auto)
        self._beam_width = max(1, int(beam_width))
        self._max_candidates = max(1, int(max_candidates))
        self._rebuild_enabled = bool(rebuild_enabled)
        self._rebuild_size_delta = float(rebuild_size_delta)
        self._rebuild_interval_seconds = int(rebuild_interval_seconds)

        # Rebuild bookkeeping
        self._last_build_n = 0
        self._last_build_time = 0.0

    # ---- Public API ----
    def setup(self, vector_dim: int, namespace: str) -> None:
        with self._lock:
            self._vector_dim = int(vector_dim)
            self.collection_name = namespace
            self._maybe_rebuild(force=True)

    def upsert(self, points: List[Dict[str, Any]]) -> None:
        if not points:
            return
        with self._lock:
            for p in points:
                try:
                    pid = str(p.get("id"))
                    if not pid:
                        continue
                    vec = p.get("vector")
                    if isinstance(vec, list):
                        v = np.asarray(vec, dtype=np.float32)
                    elif isinstance(vec, np.ndarray):
                        v = vec.astype(np.float32)
                    else:
                        continue
                    if v.ndim > 1:
                        v = v.flatten()
                    # pad/truncate to vector_dim
                    if self._vector_dim and v.size != self._vector_dim:
                        if v.size < self._vector_dim:
                            v = np.pad(v, (0, self._vector_dim - v.size))
                        else:
                            v = v[: self._vector_dim]
                    if not np.isfinite(v).all():
                        continue
                    payload = dict(p.get("payload", {}))

                    # insert/replace
                    if pid in self._id_to_idx and self._vectors is not None:
                        idx = self._id_to_idx[pid]
                        self._vectors[idx, :] = v
                        self._points[pid] = payload
                        if pid in self._tombstones:
                            self._tombstones.discard(pid)
                    else:
                        # append
                        if self._vectors is None:
                            self._vectors = v.reshape(1, -1)
                        else:
                            self._vectors = np.vstack([self._vectors, v.reshape(1, -1)])
                        self._ids.append(pid)
                        self._id_to_idx[pid] = len(self._ids) - 1
                        self._points[pid] = payload
                        if pid in self._tombstones:
                            self._tombstones.discard(pid)
                except Exception:
                    # Skip malformed entries
                    continue

            self._maybe_rebuild(force=False)

    def search(self, vector: List[float], top_k: int) -> List[_Hit]:
        k = max(0, int(top_k))
        if k == 0:
            return []
        with self._lock:
            if self._vectors is None or self._vectors.shape[0] == 0:
                return []
            q = np.asarray(vector, dtype=np.float32).flatten()
            if q.size != self._vector_dim:
                if q.size < self._vector_dim:
                    q = np.pad(q, (0, self._vector_dim - q.size))
                else:
                    q = q[: self._vector_dim]

            # Candidate selection
            cand_indices: List[int]
            if self._centroids is None or self._assignments is None or not self._lists:
                # Fallback to scanning all
                cand_indices = [i for i, pid in enumerate(self._ids) if pid not in self._tombstones]
            else:
                # Score centroids by cosine ~ dot if normalized
                c = self._centroids
                qn = self._safe_norm(q)
                if qn > 0:
                    qn_vec = q / qn
                else:
                    qn_vec = q
                cn = np.linalg.norm(c, axis=1)
                valid = cn > 0
                sims = np.zeros(c.shape[0], dtype=np.float32)
                sims[valid] = (c[valid] @ qn_vec) / cn[valid]
                order = np.argsort(-sims)
                beams = order[: min(self._beam_width, order.size)]
                cand_indices = []
                seen = set()
                # First, take from top beams
                for b in beams:
                    for idx in self._lists[int(b)]:
                        if len(cand_indices) >= self._max_candidates:
                            break
                        pid = self._ids[idx]
                        if pid in self._tombstones or idx in seen:
                            continue
                        cand_indices.append(idx)
                        seen.add(idx)
                # Then, fill from remaining centroids in order until cap
                if len(cand_indices) < self._max_candidates:
                    for b in order:
                        if b in beams:
                            continue
                        for idx in self._lists[int(b)]:
                            if len(cand_indices) >= self._max_candidates:
                                break
                            pid = self._ids[idx]
                            if pid in self._tombstones or idx in seen:
                                continue
                            cand_indices.append(idx)
                            seen.add(idx)

            if not cand_indices:
                return []

            # Exact cosine rerank on candidates
            V = self._vectors[np.array(cand_indices, dtype=np.int32), :]
            scores = self._cosine_batch(q, V)
            top_idx = np.argsort(-scores)[:k]
            hits: List[_Hit] = []
            for j in top_idx:
                idx = cand_indices[int(j)]
                pid = self._ids[idx]
                hits.append(_Hit(id=pid, score=float(scores[int(j)]), payload=dict(self._points.get(pid, {}))))
            return hits

    def delete(self, ids: List[str]) -> None:
        if not ids:
            return
        with self._lock:
            for pid in ids:
                if pid in self._id_to_idx:
                    self._tombstones.add(pid)

    def scroll(self) -> Iterator[Any]:
        with self._lock:
            if self._vectors is None:
                return iter(())
            # yield shallow records with payload attribute
            @dataclass
            class _Record:
                id: str
                vector: list[float]
                payload: dict

            for i, pid in enumerate(self._ids):
                if pid in self._tombstones:
                    continue
                yield _Record(id=pid, vector=self._vectors[i, :].tolist(), payload=dict(self._points.get(pid, {})))

    def health_check(self) -> bool:
        with self._lock:
            if self._vectors is None:
                return True
            n = self._vectors.shape[0]
            if n == 0:
                return True
            # If rebuild enabled and stale, still healthy but suggests maintenance.
            return self._centroids is not None and self._assignments is not None and len(self._lists) > 0

    # ---- Internals ----
    def _maybe_rebuild(self, force: bool) -> None:
        now = time.time()
        n = 0 if self._vectors is None else int(self._vectors.shape[0])
        need = force
        if self._rebuild_enabled and not need:
            if self._last_build_n == 0 and n > 0:
                need = True
            elif n >= (1 + self._rebuild_size_delta) * max(1, self._last_build_n):
                need = True
            elif now - self._last_build_time >= self._rebuild_interval_seconds:
                need = True
        if not need:
            return

        # Small-N fallback
        if n < 64:
            self._centroids = None
            self._assignments = None
            self._lists = []
            self._last_build_n = n
            self._last_build_time = now
            return

        C = self._requested_centroids or max(8, int(math.ceil(math.sqrt(n))))
        C = min(C, n)
        if self._vectors is None:
            # Nothing to build
            self._centroids = None
            self._assignments = None
            self._lists = []
            self._last_build_n = n
            self._last_build_time = now
            return
        X = self._vectors.astype(np.float32, copy=False)
        # Init centroids via random sample of non-tombstoned indices
        available = [i for i, pid in enumerate(self._ids) if pid not in self._tombstones]
        if len(available) < C:
            C = max(2, len(available))
        if C < 2:
            self._centroids = None
            self._assignments = None
            self._lists = []
            self._last_build_n = n
            self._last_build_time = now
            return
        sel = np.random.choice(np.array(available, dtype=np.int32), size=C, replace=False)
        centroids = X[sel, :].copy()

        # Run a few Lloyd iterations
        for _ in range(5):
            # assign
            assign = self._nearest_centroid(X, centroids)
            # update
            for c in range(C):
                mask = assign == c
                if not np.any(mask):
                    continue
                centroids[c, :] = X[mask, :].mean(axis=0)

        # Final assignments
        assign = self._nearest_centroid(X, centroids)
        lists: List[List[int]] = [[] for _ in range(C)]
        for i, cidx in enumerate(assign):
            pid = self._ids[i]
            if pid in self._tombstones:
                continue
            lists[int(cidx)].append(i)

        # Atomically swap
        self._centroids = centroids
        self._assignments = assign
        self._lists = lists
        self._last_build_n = n
        self._last_build_time = now

    @staticmethod
    def _safe_norm(v: np.ndarray) -> float:
        n = float(np.linalg.norm(v))
        if not math.isfinite(n):
            return 0.0
        return n

    @staticmethod
    def _cosine_batch(q: np.ndarray, M: np.ndarray) -> np.ndarray:
        qn = np.linalg.norm(q)
        if qn <= 0:
            return np.zeros(M.shape[0], dtype=np.float32)
        qn_vec = q / qn
        denom = np.linalg.norm(M, axis=1)
        valid = denom > 0
        out = np.zeros(M.shape[0], dtype=np.float32)
        out[valid] = (M[valid] @ qn_vec) / denom[valid]
        return out

    @staticmethod
    def _nearest_centroid(X: np.ndarray, C: np.ndarray) -> np.ndarray:
        # cosine distance ~ 1 - cosine similarity, choose max similarity
        Cn = np.linalg.norm(C, axis=1)
        Cn[Cn == 0] = 1.0
        CnC = C / Cn[:, None]
        Xn = np.linalg.norm(X, axis=1)
        Xn[Xn == 0] = 1.0
        XnX = X / Xn[:, None]
        sims = XnX @ CnC.T  # [N, C]
        assign = np.argmax(sims, axis=1)
        return assign.astype(np.int32)
