"""
Batched Store implementation for SomaFractalMemory.

This module provides a wrapper that batches writes to KV and Vector stores
in-process, flushing them periodically or when a configured batch size is reached.
"""

import logging
import threading
from collections.abc import Iterator, Mapping
from typing import Any

from somafractalmemory.interfaces.storage import IKeyValueStore, IVectorStore

logger = logging.getLogger(__name__)


class BatchedStore(IKeyValueStore, IVectorStore):
    """Wraps a KV store and a Vector store and batches writes in-process.

    This class is opt-in via configuration (env var). It collects KV `set`
    calls and vector `upsert` calls into an in-memory queue and flushes them
    periodically or when a configured batch size is reached. The flush runs
    on a daemon background thread so it doesn't block request processing.
    """

    def __init__(
        self,
        kv_store: IKeyValueStore,
        vector_store: IVectorStore,
        batch_size: int = 100,
        flush_interval_ms: int = 5,
    ):
        self._kv = kv_store
        self._vec = vector_store
        self._batch_size = int(batch_size)
        self._flush_interval = max(int(flush_interval_ms), 1) / 1000.0
        self._kv_queue: list[tuple[str, bytes]] = []
        self._vec_queue: list[dict[str, Any]] = []
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    # ----- IKeyValueStore methods -----
    def set(self, key: str, value: bytes):
        """Enqueue KV set for batch flush."""
        with self._lock:
            self._kv_queue.append((key, value))
            if len(self._kv_queue) + len(self._vec_queue) >= self._batch_size:
                # flush synchronously when threshold reached to avoid unbounded memory
                self._flush_locked()

    def get(self, key: str) -> bytes | None:
        """Reads must be strongly consistent; delegate directly to underlying store."""
        return self._kv.get(key)

    def delete(self, key_or_ids):
        """Delete either a KV key (str) or vector ids (list[str]).

        BatchedStore implements both IKeyValueStore and IVectorStore delete
        contracts. To avoid duplicate method names with incompatible
        signatures, provide a single dispatcher that accepts either a string
        key (delegated to the underlying KV store) or an iterable of ids
        (delegated to the underlying vector store).
        """
        # Vector delete path (list/tuple of ids)
        try:
            if isinstance(key_or_ids, list) or isinstance(key_or_ids, tuple):
                return self._vec.delete(key_or_ids)
        except Exception as exc:
            # Log and fallthrough to KV path - type: ignore[union-attr] for mixed types
            logger.debug("Vector delete failed, trying KV path", extra={"error": str(exc)})
        # KV delete path (single key)
        return self._kv.delete(key_or_ids)

    def scan_iter(self, pattern: str) -> Iterator[str]:
        """Delegate to underlying KV store."""
        return self._kv.scan_iter(pattern)

    def hgetall(self, key: str) -> dict[bytes, bytes]:
        """Delegate to underlying KV store."""
        return self._kv.hgetall(key)

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        """Delegate to underlying KV store."""
        return self._kv.hset(key, mapping)

    def lock(self, name: str, timeout: int = 10):
        """Delegate to underlying KV store."""
        return self._kv.lock(name, timeout)

    def health_check(self) -> bool:
        """Check both underlying stores are healthy."""
        return self._kv.health_check() and self._vec.health_check()

    # ----- IVectorStore methods -----
    def setup(self, vector_dim: int, namespace: str):
        """Delegate to underlying vector store."""
        return self._vec.setup(vector_dim, namespace)

    def upsert(self, points: list[dict[str, Any]]):
        """Enqueue points for batch upsert."""
        with self._lock:
            self._vec_queue.extend(points)
            if len(self._kv_queue) + len(self._vec_queue) >= self._batch_size:
                self._flush_locked()

    def search(self, vector: list[float], top_k: int):
        """Delegate to underlying vector store."""
        return self._vec.search(vector, top_k)

    def scroll(self) -> Iterator[Any]:
        """Delegate to underlying vector store."""
        return self._vec.scroll()

    # ----- Background worker & flush -----
    def _run(self):
        """Background worker that periodically flushes queued items."""
        while not self._stop.is_set():
            try:
                with self._lock:
                    self._flush_locked()
            except Exception as exc:
                # Log background flush errors to avoid silent failures
                logger.debug("Background flush failed", extra={"error": str(exc)})
            self._stop.wait(self._flush_interval)

    def _flush_locked(self):
        """Flush queued items. Caller must hold self._lock."""
        if not self._kv_queue and not self._vec_queue:
            return
        kv_items = self._kv_queue
        vec_items = self._vec_queue
        self._kv_queue = []
        self._vec_queue = []

        # Flush KV items
        try:
            # Best-effort: try to use pipeline if underlying Redis client exposes it
            if hasattr(self._kv, "client") and hasattr(self._kv.client, "pipeline"):
                pipe = self._kv.client.pipeline()
                for k, v in kv_items:
                    pipe.set(k, v)
                try:
                    pipe.execute()
                except Exception as exc:
                    # Fallback to individual writes
                    logger.debug(
                        "Pipeline execute failed, falling back to individual writes",
                        extra={"error": str(exc), "item_count": len(kv_items)},
                    )
                    for k, v in kv_items:
                        try:
                            self._kv.set(k, v)
                        except Exception as item_exc:
                            logger.debug(
                                "Individual KV set failed", extra={"key": k, "error": str(item_exc)}
                            )
            else:
                for k, v in kv_items:
                    try:
                        self._kv.set(k, v)
                    except Exception as item_exc:
                        logger.debug("KV set failed", extra={"key": k, "error": str(item_exc)})
        except Exception as exc:
            logger.debug("KV flush failed", extra={"error": str(exc), "item_count": len(kv_items)})

        # Flush vector items
        try:
            if vec_items:
                try:
                    self._vec.upsert(vec_items)
                except Exception as exc:
                    # If upsert fails, attempt individual upserts to avoid losing data
                    logger.debug(
                        "Batch vector upsert failed, falling back to individual upserts",
                        extra={"error": str(exc), "item_count": len(vec_items)},
                    )
                    for p in vec_items:
                        try:
                            self._vec.upsert([p])
                        except Exception as item_exc:
                            logger.debug(
                                "Individual vector upsert failed",
                                extra={"point_id": p.get("id"), "error": str(item_exc)},
                            )
        except Exception as exc:
            logger.debug(
                "Vector flush failed", extra={"error": str(exc), "item_count": len(vec_items)}
            )

    def flush(self, timeout: float = 5.0):
        """Flush pending items synchronously (useful for tests)."""
        with self._lock:
            self._flush_locked()

    def stop(self):
        """Stop the background worker."""
        self._stop.set()
        try:
            self._worker.join(timeout=1.0)
        except Exception as exc:
            logger.debug("Worker join failed during stop", extra={"error": str(exc)})

    def __del__(self):
        try:
            self.stop()
        except Exception as exc:
            # Destructor exceptions are expected during interpreter shutdown
            logger.debug("Stop failed during destructor", extra={"error": str(exc)})
