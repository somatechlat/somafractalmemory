"""Minimal, math-first memory core for exploratory development.

Design goals:
- Small, dependency-light (only numpy).
- Mathematical clarity: coordinates are vectors, memories are simple payloads.
- Deterministic, testable behavior with simple L2 similarity recall.

This module is intentionally tiny and self-contained so it can replace the
complex production core during focused development or demos.
"""

from __future__ import annotations

import numpy as np


class MinimalSoma:
    """A tiny memory store that keeps in-memory vectors and payloads.

    API:
    - store(coord, payload): store a payload at a numeric coordinate (tuple/ndarray)
    - recall(query_coord, top_k=3): return nearest payloads by L2 distance
    - all(): return all stored entries
    """

    def __init__(self, dim: int = 3):
        self.dim = int(dim)
        # Initialize internal storage lists
        self._coords: list[np.ndarray] = []
        self._payloads: list[dict] = []

    def _to_vec(self, coord: tuple[float, ...]) -> np.ndarray:
        arr = np.asarray(coord, dtype=np.float64).reshape(-1)
        if arr.size != self.dim:
            raise ValueError(f"coord length {arr.size} != dim {self.dim}")
        return arr

    def store(self, coord: tuple[float, ...], payload: dict) -> None:
        v = self._to_vec(coord)
        self._coords.append(v.copy())
        self._payloads.append(dict(payload))

    def all(self) -> list[dict]:
        return list(self._payloads)
