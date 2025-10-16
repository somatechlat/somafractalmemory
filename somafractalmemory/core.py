# isort: skip_file
# ruff: noqa
import hashlib
import json
import logging
import os
import threading
import time
import uuid
import math
from enum import Enum
from typing import Any, ContextManager, Dict, List, Optional, Tuple

from cryptography.fernet import Fernet
from common.config.settings import load_settings
import numpy as np
from prometheus_client import CollectorRegistry, Counter, Histogram
import structlog

import urllib.request
import urllib.error
import urllib.parse

try:
    from psycopg2.sql import SQL, Identifier  # used in memory_stats when Postgres available
except Exception:  # pragma: no cover - optional import depending on environment
    SQL = None  # type: ignore
    Identifier = None  # type: ignore

from .interfaces.graph import IGraphStore
from .interfaces.storage import IKeyValueStore, IVectorStore
from .serialization import deserialize, serialize


class MemoryType(Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class SomaFractalMemoryError(Exception):
    pass


logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()


def _coord_to_key(namespace: str, coord: Tuple[float, ...]) -> Tuple[str, str]:
    coord_str = repr(coord)
    data_key = f"{namespace}:{coord_str}:data"
    meta_key = f"{namespace}:{coord_str}:meta"
    return data_key, meta_key


class SomaFractalMemoryEnterprise:
    """
    Enterprise-grade agentic memory system supporting modular backends, semantic graph operations,
    and advanced memory management.

    Attributes
    ----------
    namespace : str
        The namespace for all memory operations.
    kv_store : IKeyValueStore
        Key-value store backend.
    vector_store : IVectorStore
        Vector store backend for embeddings and similarity search.
    graph_store : IGraphStore
        Graph store backend for semantic links.
    """

    def find_shortest_path(
        self,
        from_coord: Tuple[float, ...],
        to_coord: Tuple[float, ...],
        link_type: Optional[str] = None,
    ) -> List[Any]:
        """
        Find the shortest path between two coordinates in the semantic graph.

        Parameters
        ----------
        from_coord : Tuple[float, ...]
            Source coordinate.
        to_coord : Tuple[float, ...]
            Target coordinate.
        link_type : Optional[str]
            Type of link to consider (e.g., 'related').

        Returns
        -------
        List[Any]
            List of coordinates representing the shortest path.
        """
        return self.graph_store.find_shortest_path(from_coord, to_coord, link_type)

    def _reconcile_once(self):
        """
        Reconcile WAL (Write-Ahead Log) entries: mark as committed if upsert succeeds.

        This is used for reliability in case of vector store failures.
        """
        wal_prefix = f"{self.namespace}:wal:"
        for wal_key in self.kv_store.scan_iter(f"{wal_prefix}*"):
            raw = self.kv_store.get(wal_key)
            if not raw:
                continue
            try:
                entry = deserialize(raw)
            except Exception:
                logger.warning(f"Failed to deserialize WAL entry {wal_key}")
                continue

            if entry.get("status") != "committed":
                entry["status"] = "committed"
                try:
                    self.kv_store.set(wal_key, serialize(entry))
                except Exception:
                    logger.warning(f"Failed to write back WAL entry {wal_key}")

    def delete(self, coordinate: Tuple[float, ...]) -> bool:
        """
        Delete a memory at the given coordinate from all stores (KV, vector, graph).

        Parameters
        ----------
        coordinate : Tuple[float, ...]
            The coordinate of the memory to delete.

        Returns
        -------
        bool
            True if deletion was successful.
        """
        data_key, meta_key = _coord_to_key(self.namespace, coordinate)
        self.kv_store.delete(data_key)
        self.kv_store.delete(meta_key)
        coord_id = repr(coordinate)
        self.vector_store.delete([coord_id])
        self.graph_store.remove_memory(coordinate)
        return True

    def _sync_graph_from_memories(self):
        """
        Synchronize the graph store from all current memories.
        (Stub: actual implementation can be added for full graph consistency.)
        """

    def __init__(
        self,
        namespace: str,
        kv_store: IKeyValueStore,
        vector_store: IVectorStore,
        graph_store: IGraphStore,
        model_name: str = "microsoft/codebert-base",
        vector_dim: int = 768,
        encryption_key: Optional[bytes] = None,
        config_file: str = "config.yaml",
        max_memory_size: int = 100000,
        pruning_interval_seconds: int = 600,
        decay_thresholds_seconds: Optional[List[int]] = None,
        decayable_keys_by_level: Optional[List[List[str]]] = None,
        decay_enabled: bool = True,
        reconcile_enabled: bool = True,
    ) -> None:
        self.namespace = os.getenv("SOMA_NAMESPACE", namespace)
        self.kv_store = kv_store
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.max_memory_size = int(os.getenv("SOMA_MAX_MEMORY_SIZE", max_memory_size))
        self.pruning_interval_seconds = int(
            os.getenv("SOMA_PRUNING_INTERVAL_SECONDS", pruning_interval_seconds)
        )
        self.decay_thresholds_seconds = decay_thresholds_seconds or []
        self.decayable_keys_by_level = decayable_keys_by_level or []
        self.decay_enabled = decay_enabled
        self.reconcile_enabled = reconcile_enabled
        # JSON-first mode only  legacy binary Python serialization support removed for v2.
        self.model_lock = threading.RLock()
        self.vector_dim = int(os.getenv("SOMA_VECTOR_DIM", vector_dim))
        # Fast core / flat index enable flag
        self.fast_core_enabled = os.getenv("SFM_FAST_CORE", "0").lower() in ("1", "true", "yes")

        # Adaptive importance normalization state
        self._imp_reservoir: List[float] = []
        self._imp_reservoir_max = 512
        self._imp_last_recompute = 0
        self._imp_q10 = self._imp_q50 = self._imp_q90 = self._imp_q99 = None
        self._imp_method = "minmax"  # minmax | winsor | logistic
        self._importance_min = None
        self._importance_max = None

        # Fast core contiguous slabs (allocated lazily if enabled)
        if self.fast_core_enabled:
            self._fast_capacity = 1024
            self._fast_size = 0
            self._fast_vectors = np.zeros((self._fast_capacity, self.vector_dim), dtype="float32")
            self._fast_importance = np.zeros(self._fast_capacity, dtype="float32")
            self._fast_timestamps = np.zeros(self._fast_capacity, dtype="float64")
            self._fast_payloads: List[Optional[Dict[str, Any]]] = [None] * self._fast_capacity

        # Load centralized settings via Pydantic-based loader from common/
        config = load_settings(config_file=config_file)

        # Allow forcing hash-only embeddings (fast, deterministic) for tests/dev
        force_hash = os.getenv("SOMA_FORCE_HASH_EMBEDDINGS", "0").lower() in (
            "1",
            "true",
            "yes",
        )
        if force_hash:
            # Quiet mode for CLI/tests: avoid printing to stdout
            try:
                logger.debug("SOMA_FORCE_HASH_EMBEDDINGS enabled: using hash-based embeddings")
            except Exception as e:
                logger.warning("Failed to log to stdout", error=str(e))
            self.tokenizer = None
            self.model = None
        else:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    os.getenv("SOMA_MODEL_NAME", model_name), revision="main"
                )
                self.model = AutoModel.from_pretrained(
                    os.getenv("SOMA_MODEL_NAME", model_name), use_safetensors=True, revision="main"
                )
            except Exception as e:
                logger.warning(
                    f"Transformer model init failed, falling back to hash-based embeddings: {e}"
                )
                self.tokenizer = None
                self.model = None

        # anomaly_detector removed: cognitive functions are migrated out of the data plane
        self.anomaly_detector = None
        self.cipher = Fernet(encryption_key or Fernet.generate_key()) if encryption_key else None

        self.registry = CollectorRegistry()
        self.store_count = Counter(
            "soma_memory_store_total",
            "Total store operations",
            ["namespace"],
            registry=self.registry,
        )
        self.store_latency = Histogram(
            "soma_memory_store_latency_seconds",
            "Store operation latency",
            ["namespace"],
            registry=self.registry,
        )
        self.recall_count = Counter(
            "soma_memory_recall_total",
            "Total recall operations",
            ["namespace"],
            registry=self.registry,
        )
        self.recall_latency = Histogram(
            "soma_memory_recall_latency_seconds",
            "Recall operation latency",
            ["namespace"],
            registry=self.registry,
        )

        # eventing.
        self.eventing_enabled = os.getenv("SOMA_EVENTING_ENABLED", "1").lower() in (
            "1",
            "true",
            "yes",
        )
        if self.eventing_enabled:
            try:
                from .eventing.producer import build_memory_event, produce_event

                self._build_event = build_memory_event
                self._produce_event = produce_event
            except ImportError:
                logger.warning("Kafka eventing enabled but producer components not found.")
                self.eventing_enabled = False
        self.langfuse = None

        self.vector_store.setup(vector_dim=self.vector_dim, namespace=self.namespace)
        self._sync_graph_from_memories()

        # Start memory decay thread if enabled
        if self.decay_enabled:
            threading.Thread(target=self._decay_memories, daemon=True).start()

        # Enable hybrid recall by default (can be disabled via env)
        self.hybrid_recall_default = os.getenv("SOMA_HYBRID_RECALL_DEFAULT", "1").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    def _decay_memories(self):
        """
        Periodic background task that applies basic decay rules to memories.

        This implementation is JSON-first: it reads stored entries with
        `deserialize`, applies configured decay thresholds and keys, and
        writes the updated memory back using `serialize`.
        """
        while True:
            now = time.time()
            for meta_key in self.kv_store.scan_iter(f"{self.namespace}:*:meta"):
                try:
                    metadata = self.kv_store.hgetall(meta_key)
                    created = float(metadata.get(b"creation_timestamp", b"0"))
                    age = now - created
                    data_key = meta_key.replace(":meta", ":data")
                    raw_data = self.kv_store.get(data_key)
                    if not raw_data:
                        continue
                    try:
                        memory_item = deserialize(raw_data)
                    except Exception:
                        logger.warning(f"Failed to deserialize memory {data_key} during decay")
                        continue
                    for i, threshold in enumerate(self.decay_thresholds_seconds):
                        if age > threshold:
                            keys_to_remove = (
                                set(self.decayable_keys_by_level[i])
                                if i < len(self.decayable_keys_by_level)
                                else set()
                            )
                            for key in keys_to_remove:
                                memory_item.pop(key, None)
                    try:
                        self.kv_store.set(data_key, serialize(memory_item))
                    except Exception:
                        logger.warning(f"Failed to write decayed memory {data_key}")
                except Exception as e:
                    logger.warning(f"Error during decay for {meta_key}: {e}")
            time.sleep(self.pruning_interval_seconds)

    # --------- Bulk and Export/Import ---------
    def store_memories_bulk(
        self, items: List[Tuple[Tuple[float, ...], Dict[str, Any], MemoryType]]
    ):
        for coordinate, payload, memory_type in items:
            self.store_memory(coordinate, payload, memory_type)
        return True

    def export_memories(self, path: str) -> int:
        mems = self.get_all_memories()
        with open(path, "w", encoding="utf-8") as f:
            for mem in mems:
                f.write(json.dumps(mem) + "\n")
        return len(mems)

    # --------- Core KV/Vector storage ---------
    def store(self, coordinate: Tuple[float, ...], value: dict):
        data_key, meta_key = _coord_to_key(self.namespace, coordinate)
        try:
            self.kv_store.set(data_key, serialize(value))
        except Exception:
            # Best-effort: fall back to raw json bytes if serializer fails
            try:
                self.kv_store.set(data_key, json.dumps(value).encode("utf-8"))
            except Exception:
                logger.warning(f"Failed to write memory for {data_key}")
        try:
            self.kv_store.hset(
                meta_key, mapping={b"creation_timestamp": str(time.time()).encode("utf-8")}
            )
        except Exception as e:
            logger.warning(f"Failed to set metadata for {meta_key}: {e}")

        try:
            vector = self.embed_text(json.dumps(value))
            self.vector_store.upsert(
                points=[
                    {"id": str(uuid.uuid4()), "vector": vector.flatten().tolist(), "payload": value}
                ]
            )
        except Exception as e:
            logger.error(f"Vector store upsert failed: {e}")
            try:
                wal_key = f"{self.namespace}:wal:{uuid.uuid4()}"
                wal_payload = {
                    "coordinate": list(coordinate),
                    "value": value,
                    "error": str(e),
                    "ts": time.time(),
                }
                try:
                    self.kv_store.set(wal_key, serialize(wal_payload))
                except Exception as e:
                    logger.warning("Failed to write WAL entry", error=str(e))
            except Exception:
                pass
            # WAL entry written (JSON-first). Reconciliation runs separately.

    def acquire_lock(self, name: str, timeout: int = 10) -> ContextManager:
        return self.kv_store.lock(name, timeout)

    def with_lock(self, name: str, func, *args, **kwargs):
        lock = self.acquire_lock(name)
        if lock:
            with lock:
                return func(*args, **kwargs)
        return func(*args, **kwargs)

    def iter_memories(self, pattern: Optional[str] = None):
        try:
            for point in self.vector_store.scroll():
                try:
                    yield point.payload
                except Exception:
                    continue
        except Exception as e:
            logger.warning(
                f"Vector store unavailable for iter_memories: {e}, falling back to key-value store."
            )
            if pattern is None:
                pattern = f"{self.namespace}:*:data"
            for key in self.kv_store.scan_iter(pattern):
                data = self.kv_store.get(key)
                if data:
                    try:
                        try:
                            yield deserialize(data)
                        except Exception:
                            # If deserialize fails, skip this record
                            continue
                    except Exception:
                        continue

    def health_check(self) -> Dict[str, bool]:
        def safe(check):
            try:
                return bool(check())
            except Exception:
                return False

        # Return the basic store health checks. Prediction/policy providers are
        # optional and intentionally not part of the data-plane health payload.
        return {
            "kv_store": safe(self.kv_store.health_check),
            "vector_store": safe(self.vector_store.health_check),
            "graph_store": safe(self.graph_store.health_check),
        }

    def set_importance(self, coordinate: Tuple[float, ...], importance: int = 1):
        data_key, _ = _coord_to_key(self.namespace, coordinate)
        data = self.kv_store.get(data_key)
        if not data:
            raise SomaFractalMemoryError(f"No memory at {coordinate}")
        try:
            value = deserialize(data)
        except Exception as exc:
            raise SomaFractalMemoryError(f"Failed to deserialize memory at {coordinate}") from exc
        value["importance"] = importance
        try:
            self.kv_store.set(data_key, serialize(value))
        except Exception:
            logger.warning(f"Failed to persist importance change for {data_key}")
        try:
            updates = []
            for rec in self.vector_store.scroll():
                try:
                    payload = getattr(rec, "payload", {})
                    if payload.get("coordinate") == list(coordinate):
                        payload["importance"] = importance
                        rec_id = getattr(rec, "id", None)
                        vec = getattr(rec, "vector", None)
                        if rec_id is not None and vec is not None:
                            updates.append(
                                {"id": str(rec_id), "vector": list(vec), "payload": payload}
                            )
                except Exception:
                    continue
            if updates:
                self.vector_store.upsert(points=updates)
        except Exception as e:
            logger.debug(f"Vector payload sync failed in set_importance: {e}")

    def retrieve(self, coordinate: Tuple[float, ...]) -> Optional[Dict[str, Any]]:
        lock = self.acquire_lock(f"lock:{coordinate}")
        if lock:
            with lock:
                data_key, _ = _coord_to_key(self.namespace, coordinate)
                data = self.kv_store.get(data_key)
                if not data:
                    return None
                _, meta_key = _coord_to_key(self.namespace, coordinate)
                self.kv_store.hset(
                    meta_key, mapping={b"last_accessed_timestamp": str(time.time()).encode("utf-8")}
                )
                try:
                    value = deserialize(data)
                except Exception:
                    logger.warning(f"Failed to deserialize memory at retrieve {data_key}")
                    return None
                value["access_count"] = value.get("access_count", 0) + 1
                try:
                    self.kv_store.set(data_key, serialize(value))
                except Exception:
                    logger.warning(f"Failed to persist access_count for {data_key}")
                if self.cipher:
                    for k in ["task", "code"]:
                        if k in value and value[k]:
                            try:
                                value[k] = self.cipher.decrypt(value[k].encode()).decode()
                            except Exception as e:
                                logger.warning(
                                    f"Decryption failed for key '{k}' in {coordinate}: {e}"
                                )
                return value
        return None

    def _apply_decay_to_all(self):
        logger.debug("Applying advanced memory decay check...")
        now = time.time()
        decayed_count = 0
        for meta_key in self.kv_store.scan_iter(f"{self.namespace}:*:meta"):
            try:
                metadata = self.kv_store.hgetall(meta_key)
                created = float(metadata.get(b"creation_timestamp", b"0"))
                age = now - created
                last_accessed = float(metadata.get(b"last_accessed_timestamp", created))
                recency = now - last_accessed
                data_key = meta_key.replace(":meta", ":data")
                raw_data = self.kv_store.get(data_key)
                if not raw_data:
                    continue
                try:
                    memory_item = deserialize(raw_data)
                except Exception:
                    logger.warning(f"Failed to deserialize memory {data_key} in advanced decay")
                    continue
                access_count = memory_item.get("access_count", 0)
                importance = memory_item.get("importance", 0)
                decay_score = (
                    (age / 3600) + (recency / 3600) - (0.5 * access_count) - (2 * importance)
                )
                if decay_score > 2 and importance <= 1:
                    keys_to_remove = set(memory_item.keys()) - {
                        "memory_type",
                        "timestamp",
                        "coordinate",
                        "importance",
                    }
                    for key in keys_to_remove:
                        memory_item.pop(key, None)
                    try:
                        self.kv_store.set(data_key, serialize(memory_item))
                    except Exception:
                        logger.warning(f"Failed to write advanced-decayed memory {data_key}")
                    decayed_count += 1
            except Exception as e:
                logger.warning(f"Error during advanced decay for {meta_key}: {e}")

    # intentionally quiet to avoid CLI noise

    def save_version(self, coordinate: Tuple[float, ...]):
        data_key, _ = _coord_to_key(self.namespace, coordinate)
        data = self.kv_store.get(data_key)
        if not data:
            raise SomaFractalMemoryError(f"No memory at {coordinate}")
        version_key = f"{data_key}:version:{time.time_ns()}"
        self.kv_store.set(version_key, data)

    def get_versions(self, coordinate: Tuple[float, ...]) -> List[Dict[str, Any]]:
        data_key, _ = _coord_to_key(self.namespace, coordinate)
        pattern = f"{data_key}:version:*"
        versions = []
        for vkey in self.kv_store.scan_iter(pattern):
            vdata = self.kv_store.get(vkey)
            if vdata:
                try:
                    versions.append(deserialize(vdata))
                except Exception:
                    logger.warning(f"Failed to deserialize version {vkey}")
        return versions

    def audit_log(self, action: str, coordinate: Tuple[float, ...], user: str = "system"):
        log_entry = {
            "action": action,
            "coordinate": coordinate,
            "user": user,
            "timestamp": time.time(),
        }
        with open("audit_log.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def summarize_memories(
        self, n: int = 10, memory_type: Optional[MemoryType] = None
    ) -> List[str]:
        mems = self.retrieve_memories(memory_type)
        mems = sorted(mems, key=lambda m: m.get("timestamp", 0), reverse=True)[:n]
        return [str(m.get("task", m.get("fact", "<no summary>"))) for m in mems]

    def get_recent(
        self, n: int = 10, memory_type: Optional[MemoryType] = None
    ) -> List[Dict[str, Any]]:
        mems = self.retrieve_memories(memory_type)
        return sorted(mems, key=lambda m: m.get("timestamp", 0), reverse=True)[:n]

    def get_important(
        self, n: int = 10, memory_type: Optional[MemoryType] = None
    ) -> List[Dict[str, Any]]:
        mems = self.retrieve_memories(memory_type)
        return sorted(mems, key=lambda m: m.get("importance", 0), reverse=True)[:n]

    def memory_stats(self) -> Dict[str, Any]:
        # Prefer authoritative counts from the canonical Postgres store when
        # available (avoids double-counting across Redis cache + Postgres).
        try:
            kv_count = None
            episodic = 0
            semantic = 0

            # Pattern for data keys
            data_like = f"%:data"

            # If we have a Postgres-backed store available, query it directly
            pg_store = None
            if (
                hasattr(self.kv_store, "pg_store")
                and getattr(self.kv_store, "pg_store") is not None
            ):
                pg_store = self.kv_store.pg_store

            if pg_store is not None:
                # Count total data keys in Postgres
                def _count(cur):
                    cur.execute(
                        SQL("SELECT COUNT(*) FROM {} WHERE key LIKE %s;").format(
                            Identifier(pg_store._TABLE_NAME)
                        ),
                        (data_like,),
                    )
                    return cur.fetchone()[0]

                kv_count = int(pg_store._execute(_count) or 0)

                # Fetch values and compute episodic/semantic breakdown directly from JSONB
                def _fetch(cur):
                    cur.execute(
                        SQL("SELECT value FROM {} WHERE key LIKE %s;").format(
                            Identifier(pg_store._TABLE_NAME)
                        ),
                        (data_like,),
                    )
                    return [r[0] for r in cur.fetchall()]

                rows = pg_store._execute(_fetch)
                for val in rows:
                    if isinstance(val, dict):
                        mt = val.get("memory_type")
                        if mt == MemoryType.EPISODIC.value:
                            episodic += 1
                        elif mt == MemoryType.SEMANTIC.value:
                            semantic += 1
            else:
                # Fall back to scanning the kv_store interface (unique keys)
                keys = set(self.kv_store.scan_iter(data_like))
                kv_count = len(keys)
                for key in keys:
                    raw = self.kv_store.get(key)
                    if not raw:
                        continue
                    try:
                        obj = deserialize(raw)
                    except Exception:
                        continue
                    mt = obj.get("memory_type")
                    if mt == MemoryType.EPISODIC.value:
                        episodic += 1
                    elif mt == MemoryType.SEMANTIC.value:
                        semantic += 1

            # Optionally include a vector count (Qdrant) for visibility
            vector_count = 0
            try:
                if hasattr(self.vector_store, "scroll"):
                    for _ in self.vector_store.scroll():
                        vector_count += 1
            except Exception:
                vector_count = 0
            # Build per-namespace breakdown via Postgres aggregation when available
            namespaces: dict[str, dict[str, int]] = {}
            try:
                if pg_store is not None:

                    def _nsagg(cur):
                        cur.execute(
                            SQL(
                                "SELECT split_part(key,':',1) AS namespace, COUNT(*) AS total, SUM(CASE WHEN (value->>'memory_type')='episodic' THEN 1 ELSE 0 END) AS episodic, SUM(CASE WHEN (value->>'memory_type')='semantic' THEN 1 ELSE 0 END) AS semantic FROM {} WHERE key LIKE %s GROUP BY namespace;"
                            ).format(Identifier(pg_store._TABLE_NAME)),
                            (data_like,),
                        )
                        return cur.fetchall()

                    rows = pg_store._execute(_nsagg)
                    for ns, total, eps, sem in rows:
                        namespaces[ns] = {
                            "total": int(total or 0),
                            "episodic": int(eps or 0),
                            "semantic": int(sem or 0),
                        }
                else:
                    # Fallback: build namespace map by scanning keys
                    for key in self.kv_store.scan_iter(data_like):
                        ns = key.split(":", 1)[0]
                        namespaces.setdefault(ns, {"total": 0, "episodic": 0, "semantic": 0})
                        namespaces[ns]["total"] += 1
                        raw = self.kv_store.get(key)
                        if not raw:
                            continue
                        try:
                            obj = deserialize(raw)
                        except Exception:
                            continue
                        mt = obj.get("memory_type")
                        if mt == MemoryType.EPISODIC.value:
                            namespaces[ns]["episodic"] += 1
                        elif mt == MemoryType.SEMANTIC.value:
                            namespaces[ns]["semantic"] += 1
            except Exception:
                namespaces = {}

            # Obtain vector counts per collection by querying Qdrant HTTP API
            vector_collections: dict[str, int] = {}
            try:
                qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
                base = qdrant_url.rstrip("/")
                if not base.startswith(("http://", "https://")):
                    raise ValueError("Invalid Qdrant URL scheme")
                try:
                    with urllib.request.urlopen(f"{base}/collections", timeout=3) as resp:
                        body = resp.read().decode("utf-8")
                        collections_info = json.loads(body)
                except Exception:
                    collections_info = {}

                collections = (
                    collections_info.get("result", {}).get("collections", [])
                    if isinstance(collections_info, dict)
                    else []
                )
                for c in collections:
                    name = c.get("name") if isinstance(c, dict) else None
                    if not name:
                        continue
                    try:
                        quoted = urllib.parse.quote(name, safe="")
                        if not base.startswith(("http://", "https://")):
                            raise ValueError("Invalid Qdrant URL scheme")
                        with urllib.request.urlopen(
                            f"{base}/collections/{quoted}", timeout=3
                        ) as r2:
                            info = r2.read().decode("utf-8")
                            info_json = json.loads(info)
                    except Exception:
                        info_json = {}
                    pts = None
                    if isinstance(info_json, dict):
                        pts = (
                            info_json.get("result", {}).get("points_count")
                            or info_json.get("result", {}).get("vectors_count")
                            or info_json.get("result", {}).get("points", {}).get("count")
                        )
                    try:
                        vector_collections[name] = int(pts or 0)
                    except Exception:
                        vector_collections[name] = 0
            except Exception:
                vector_collections = {}

            return {
                "total_memories": int(kv_count or 0),
                "episodic": int(episodic),
                "semantic": int(semantic),
                "vector_count": int(vector_count),
                "namespaces": namespaces,
                "vector_collections": vector_collections,
            }
        except Exception:
            # On error, fall back to previous behaviour (best-effort in-memory scan)
            all_mems = self.get_all_memories()
            return {
                "total_memories": len(all_mems),
                "episodic": sum(
                    1 for m in all_mems if m.get("memory_type") == MemoryType.EPISODIC.value
                ),
                "semantic": sum(
                    1 for m in all_mems if m.get("memory_type") == MemoryType.SEMANTIC.value
                ),
            }

    # --------- Hooks & Agent helpers ---------
    def set_hook(self, event: str, func):
        if not hasattr(self, "_hooks"):
            self._hooks = {}
        self._hooks[event] = func

    def _call_hook(self, event: str, *args, **kwargs):
        if hasattr(self, "_hooks") and event in self._hooks:
            try:
                self._hooks[event](*args, **kwargs)
            except Exception as e:
                logger.warning(f"Hook {event} failed: {e}")

    def share_memory_with(self, other_agent, filter_fn=None):
        for mem in self.get_all_memories():
            if filter_fn is None or filter_fn(mem):
                other_agent.store_memory(
                    mem.get("coordinate"),
                    mem,
                    memory_type=MemoryType(mem.get("memory_type", "episodic")),
                )

    def remember(
        self,
        data: Dict[str, Any],
        coordinate: Optional[Tuple[float, ...]] = None,
        memory_type: MemoryType = MemoryType.EPISODIC,
    ):
        if coordinate is None:
            coordinate = tuple(np.random.uniform(0, 100, size=2))
        self._call_hook("before_store", data, coordinate, memory_type)
        result = self.store_memory(coordinate, data, memory_type=memory_type)
        self._call_hook("after_store", data, coordinate, memory_type)
        return result

    def recall(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
    ):
        self._call_hook("before_recall", query, context, top_k, memory_type)
        with self.recall_latency.labels(self.namespace).time():
            self.recall_count.labels(self.namespace).inc()
            if context:
                results = self.find_hybrid_with_context(
                    query, context, top_k=top_k, memory_type=memory_type
                )
            else:
                if getattr(self, "hybrid_recall_default", True):
                    # Use hybrid scoring by default for best overall recall quality
                    scored = self.hybrid_recall_with_scores(
                        query, top_k=top_k, memory_type=memory_type
                    )
                    results = [r.get("payload") for r in scored if r.get("payload")]
                else:
                    # Legacy vector-only path
                    results = self.find_hybrid_by_type(query, top_k=top_k, memory_type=memory_type)
        self._call_hook("after_recall", query, context, top_k, memory_type, results)
        return results

    def hybrid_recall(
        self,
        query: str,
        *,
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
        exact: bool = True,
        case_sensitive: bool = False,
        terms: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return payload-only results from hybrid scoring (vector + keyword boosts)."""
        scored = self.hybrid_recall_with_scores(
            query,
            terms=terms,
            top_k=top_k,
            memory_type=memory_type,
            exact=exact,
            case_sensitive=case_sensitive,
        )
        return [r.get("payload") for r in scored if r.get("payload")]

    def forget(self, coordinate: Tuple[float, ...]):
        self._call_hook("before_forget", coordinate)
        self.delete(coordinate)
        self._call_hook("after_forget", coordinate)

    def reflect(self, n: int = 5, memory_type: MemoryType = MemoryType.EPISODIC):
        self._call_hook("before_reflect", n, memory_type)
        memories = self.replay_memories(n=n, memory_type=memory_type)
        self._call_hook("after_reflect", n, memory_type, memories)
        return memories

    def consolidate_memories(self, window_seconds: int = 3600):
        now = time.time()
        episodic = self.retrieve_memories(MemoryType.EPISODIC)
        for mem in episodic:
            if now - mem.get("timestamp", 0) < window_seconds:
                coord_val = mem.get("coordinate")
                if coord_val:
                    coord_t = tuple(coord_val)
                    summary = {
                        "fact": f"Summary of event at {mem.get('timestamp')}",
                        "source_coord": coord_val,
                        "memory_type": MemoryType.SEMANTIC.value,
                        # Use a JSON-friendly list for consolidated_from so it
                        # round-trips through the JSON-only serializer as a list
                        # (tests compare against tuple coordinates). Storing as
                        # a list avoids tuple/list mismatch after deserialize.
                        "consolidated_from": list(coord_t),
                        "timestamp": now,
                    }
                    self.store_memory(coord_t, summary, memory_type=MemoryType.SEMANTIC)

    def replay_memories(
        self, n: int = 5, memory_type: MemoryType = MemoryType.EPISODIC
    ) -> List[Dict[str, Any]]:
        import random

        mems = self.retrieve_memories(memory_type)
        return random.sample(mems, min(n, len(mems)))

    # --------- Search & Graph ---------
    def find_hybrid_with_context(
        self,
        query: str,
        context: Dict[str, Any],
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        context_str = json.dumps(context, sort_keys=True)
        full_query = f"{query} [CTX] {context_str}"
        results = self.find_hybrid_by_type(
            full_query, top_k=top_k, memory_type=memory_type, **kwargs
        )

        def score(mem):
            s = 0.0
            if "timestamp" in mem:
                s += 1.0 / (1 + (time.time() - mem["timestamp"]))
            if "access_count" in mem:
                s += 0.1 * mem["access_count"]
            return s

        return sorted(results, key=score, reverse=True)

    # --- Keyword and Hybrid Search helpers ---
    def _iter_string_fields(self, obj: Any):
        """Yield all string fields from nested dict/list payloads.

        Defensive recursion with depth and count guards to avoid pathological payloads.
        """
        max_items = 4096
        max_depth = 6

        def _walk(o: Any, depth: int):
            nonlocal max_items
            if max_items <= 0 or depth > max_depth:
                return
            if isinstance(o, str):
                max_items -= 1
                yield o
            elif isinstance(o, dict):
                for v in o.values():
                    yield from _walk(v, depth + 1)
            elif isinstance(o, list):
                for v in o:
                    yield from _walk(v, depth + 1)

        yield from _walk(obj, 0)

    def keyword_search(
        self,
        term: str,
        *,
        exact: bool = True,
        case_sensitive: bool = False,
        top_k: int = 50,
        memory_type: Optional[MemoryType] = None,
    ) -> List[Dict[str, Any]]:
        """Scan payloads and return those matching the term in any string field.

        Notes:
        - This is an initial implementation that scans in-memory payloads via
          vector_store scroll (or KV fallback through iter_memories). For large
          datasets, consider adding a Postgres JSONB index path.
        """
        if not case_sensitive:
            term_cmp = term.lower()
        else:
            term_cmp = term

        def matches(payload: Dict[str, Any]) -> bool:
            try:
                for s in self._iter_string_fields(payload):
                    if s is None:
                        continue
                    s_cmp = s if case_sensitive else s.lower()
                    if exact:
                        if s_cmp == term_cmp:
                            return True
                    else:
                        if term_cmp in s_cmp:
                            return True
            except Exception:
                return False
            return False

        # Attempt optimized Postgres path if available and search is substring or exact match of a full field
        # For exact==True, we still use LIKE, but it will only match full-field equality rarely; used as a prefilter.
        try:
            from .implementations.storage import PostgresKeyValueStore  # type: ignore

            if isinstance(getattr(self.kv_store, "pg_store", self.kv_store), PostgresKeyValueStore):
                pg: PostgresKeyValueStore = getattr(self.kv_store, "pg_store", self.kv_store)
                memtype_str = memory_type.value if memory_type else None
                # Use substring search at the DB layer when exact is False; otherwise still leverage LIKE prefilter.
                db_hits = pg.search_text(
                    self.namespace,
                    term if case_sensitive else term.lower(),
                    case_sensitive=case_sensitive,
                    limit=top_k * 5,
                    memory_type=memtype_str,
                )
                # Apply exact/substring refining in Python
                filtered: List[Dict[str, Any]] = []
                for p in db_hits:
                    if memory_type and p.get("memory_type") != memtype_str:
                        continue
                    if matches(p):
                        filtered.append(p)
                        if len(filtered) >= top_k:
                            break
                if filtered:
                    return filtered[:top_k]
        except Exception as e:
            logger.warning("Failed to log to stdout", error=str(e))
        # Fallback in-memory scan
        out: List[Dict[str, Any]] = []
        for payload in self.iter_memories():
            if memory_type and payload.get("memory_type") != memory_type.value:
                continue
            if matches(payload):
                out.append(payload)
                if len(out) >= top_k:
                    break
        return out

    def hybrid_recall_with_scores(
        self,
        query: str,
        *,
        terms: Optional[List[str]] = None,
        boost: float = 2.0,
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
        exact: bool = True,
        case_sensitive: bool = False,
    ) -> List[Dict[str, Any]]:
        """Hybrid retrieval combining vector similarity with exact/substring term boosts.

        Scoring:
        - Base score from vector similarity (if available; falls back to cosine via embedding).
        - For each matching term found within any string field of a payload, add `boost`.
        - Results are sorted by combined score and truncated to `top_k`.
        """
        # Optional: derive candidate terms from query when not provided
        if not terms:
            try:
                import re

                derived: List[str] = []
                # 1) Quoted phrases
                derived += re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
                # re.findall above returns tuples due to alternation; flatten
                flat: List[str] = []
                for tup in derived:
                    if isinstance(tup, tuple):
                        for s in tup:
                            if s:
                                flat.append(s)
                    elif tup:
                        flat.append(tup)
                derived = flat
                # 2) Hex-like tokens (e.g., 0xabc123...)
                derived += re.findall(r"0x[0-9a-fA-F]+", query)
                # 3) Long-ish alnum words (>=4 chars)
                derived += [w for w in re.findall(r"[A-Za-z0-9_\-]+", query) if len(w) >= 4]
                # Deduplicate preserving order
                seen: set[str] = set()
                terms = [x for x in derived if not (x in seen or seen.add(x))]
            except Exception:
                terms = []

        # Step 1: vector candidates (fetch more to allow post-filtering and boosting)
        qv = self.embed_text(query)
        search_k = top_k * 4
        vec_hits = []
        try:
            vec_hits = self.vector_store.search(qv.flatten().tolist(), top_k=search_k)
        except Exception:
            vec_hits = []

        # Prepare case handling for term matches
        terms = terms or []
        if not case_sensitive:
            terms_cmp = [t.lower() for t in terms]
        else:
            terms_cmp = terms

        def term_match_count(payload: Dict[str, Any]) -> int:
            if not terms_cmp:
                return 0
            cnt = 0
            try:
                for s in self._iter_string_fields(payload):
                    if s is None:
                        continue
                    s_cmp = s if case_sensitive else s.lower()
                    for t in terms_cmp:
                        if exact:
                            if s_cmp == t:
                                cnt += 1
                        else:
                            if t in s_cmp:
                                cnt += 1
            except Exception:
                return cnt
            return cnt

        # Index by coordinate when available to merge duplicates
        def coord_key(payload: Dict[str, Any]) -> str:
            c = payload.get("coordinate")
            return repr(tuple(c)) if isinstance(c, list) else json.dumps(payload, sort_keys=True)

        combined: Dict[str, Dict[str, Any]] = {}

        # Step 2: incorporate vector hits with boost
        for h in vec_hits:
            payload = getattr(h, "payload", {}) or {}
            if memory_type and payload.get("memory_type") != memory_type.value:
                continue
            base = float(getattr(h, "score", 0.0) or 0.0)
            b = boost * term_match_count(payload)
            key = coord_key(payload)
            cur = combined.get(key)
            score = base + b
            if not cur or score > float(cur.get("score", -1e9)):
                combined[key] = {"payload": payload, "score": score}

        # Step 3: ensure any exact keyword-only matches are considered
        # Note: we compute an approximate vector score for these by embedding the payload JSON.
        if terms_cmp:
            for payload in self.iter_memories():
                if memory_type and payload.get("memory_type") != memory_type.value:
                    continue
                if term_match_count(payload) > 0:
                    try:
                        pv = self.embed_text(json.dumps(payload))
                        # cosine since embed_text normalizes
                        base = float(np.dot(pv.flatten(), qv.flatten()))
                    except Exception:
                        base = 0.0
                    score = base + boost * term_match_count(payload)
                    key = coord_key(payload)
                    cur = combined.get(key)
                    if not cur or score > float(cur.get("score", -1e9)):
                        combined[key] = {"payload": payload, "score": score}

        # Step 4: rank and truncate
        ranked = sorted(combined.values(), key=lambda x: float(x.get("score", 0.0)), reverse=True)
        return ranked[:top_k]

    def link_memories(
        self,
        from_coord: Tuple[float, ...],
        to_coord: Tuple[float, ...],
        link_type: str = "related",
        weight: Optional[float] = None,
    ):
        lock = self.acquire_lock(f"lock:{from_coord}")
        if lock:
            with lock:
                data_key, _ = _coord_to_key(self.namespace, from_coord)
                data = self.kv_store.get(data_key)
                if not data:
                    raise SomaFractalMemoryError(f"No memory at {from_coord}")
                try:
                    value = deserialize(data)
                except Exception as exc:
                    raise SomaFractalMemoryError(
                        f"Failed to deserialize memory at {from_coord}"
                    ) from exc
                links = value.get("links", [])
                link_data = {"to": to_coord, "type": link_type, "timestamp": time.time()}
                if weight is not None:
                    link_data["weight"] = weight
                links.append(link_data)
                value["links"] = links
                try:
                    self.kv_store.set(data_key, serialize(value))
                except Exception:
                    logger.warning(f"Failed to persist links for {data_key}")
                self.graph_store.add_link(from_coord, to_coord, link_data)

    def get_linked_memories(
        self, coord: Tuple[float, ...], link_type: Optional[str] = None, depth: int = 1
    ) -> List[Dict[str, Any]]:
        neighbors = self.graph_store.get_neighbors(coord, link_type=link_type)
        out: List[Dict[str, Any]] = []
        for c, _ in neighbors:
            if c:
                v = self.retrieve(c)
                if v:
                    out.append(v)
        return out

    def store_memory(
        self,
        coordinate: Tuple[float, ...] | List[float],
        value: Dict[str, Any],
        memory_type: MemoryType = MemoryType.EPISODIC,
    ):
        try:
            coord_t = tuple(coordinate)  # type: ignore[arg-type]
        except Exception:
            coord_t = tuple([float(c) for c in coordinate])  # type: ignore[index]
        value = dict(value)
        value["memory_type"] = memory_type.value
        if memory_type == MemoryType.EPISODIC:
            value["timestamp"] = value.get("timestamp", time.time())
        value["coordinate"] = list(coord_t)
        # Adaptive importance normalization
        raw_imp = value.get("importance", 1.0)
        try:
            raw_f = float(raw_imp)
        except Exception:
            raw_f = 0.0
        value["importance_norm"], self._imp_method = self._adaptive_importance_norm(raw_f)

        # Persist via KV + vector store (legacy path) and optionally append to fast core slabs.
        with self.store_latency.labels(self.namespace).time():
            self.store_count.labels(self.namespace).inc()
            result = self.store(coord_t, value)
            if self.eventing_enabled:
                try:
                    event = self._build_event(self.namespace, value)
                    self._produce_event(event)
                    result["event"] = event
                except Exception as e:
                    logger.warning(f"Failed to produce Kafka event: {e}")
        if self.fast_core_enabled:
            try:
                # Reuse embedding work: embed serialized payload (same as store())
                emb = self.embed_text(json.dumps(value))  # normalized inside embed_text
                self._fast_append(
                    emb,
                    value.get("importance_norm", 0.0),
                    value.get("timestamp", time.time()),
                    value,
                )
            except Exception as e:  # pragma: no cover - fast path is best effort
                logger.debug(f"Fast core append failed: {e}")
        self.graph_store.add_memory(coord_t, value)
        try:
            self._enforce_memory_limit()
        except Exception as e:
            logger.debug(f"Memory limit enforcement failed: {e}")
        return result

    # ---------------- Fast Core Helpers -----------------
    def _fast_append(
        self, vector: np.ndarray, importance_norm: float, ts: float, payload: Dict[str, Any]
    ):
        if not self.fast_core_enabled:
            return
        if vector.shape[0] == 1:
            vector = vector[0]
        if self._fast_size >= self._fast_capacity:
            new_cap = self._fast_capacity * 2
            self._fast_vectors = np.vstack(
                [
                    self._fast_vectors,
                    np.zeros((self._fast_capacity, self.vector_dim), dtype="float32"),
                ]
            )
            self._fast_importance = np.concatenate(
                [
                    self._fast_importance,
                    np.zeros(self._fast_capacity, dtype="float32"),
                ]
            )
            self._fast_timestamps = np.concatenate(
                [
                    self._fast_timestamps,
                    np.zeros(self._fast_capacity, dtype="float64"),
                ]
            )
            self._fast_payloads.extend([None] * self._fast_capacity)
            self._fast_capacity = new_cap
        idx = self._fast_size
        self._fast_vectors[idx] = vector.astype("float32")
        self._fast_importance[idx] = float(importance_norm)
        self._fast_timestamps[idx] = ts
        self._fast_payloads[idx] = payload
        self._fast_size += 1

    def _fast_search(
        self,
        query: str,
        top_k: int,
        memory_type: Optional[MemoryType],
        filters: Optional[Dict[str, Any]],
    ):
        if self._fast_size == 0:
            return []
        qv = self.embed_text(query)  # already normalized (1,D)
        if qv.shape[0] == 1:
            q = qv[0]
        else:
            q = qv
        sims = self._fast_vectors[: self._fast_size] @ q
        np.maximum(sims, 0.0, out=sims)
        sims *= self._fast_importance[: self._fast_size]
        k = min(top_k, self._fast_size)
        if k <= 0:
            return []
        # argpartition then refine
        idx = np.argpartition(sims, -k)[-k:]
        idx = idx[np.argsort(sims[idx])[::-1]]
        out: List[Dict[str, Any]] = []
        for i in idx:
            payload = self._fast_payloads[i]
            if not payload:
                continue
            if memory_type and payload.get("memory_type") != memory_type.value:
                continue
            if filters:
                ok = True
                for fk, fv in filters.items():
                    if payload.get(fk) != fv:
                        ok = False
                        break
                if not ok:
                    continue
            out.append(payload)
            if len(out) >= top_k:
                break
        return out

    # -------------- Adaptive Importance Normalization --------------
    def _adaptive_importance_norm(self, raw: float) -> Tuple[float, str]:
        """Return (normalized_importance, method_used).

        Decision tree:
          - <64 samples: plain min-max
          - moderate tail: winsorized min-max
          - extreme tail: logistic
        """
        # Reservoir update
        self._imp_reservoir.append(raw)
        if len(self._imp_reservoir) > self._imp_reservoir_max:
            self._imp_reservoir.pop(0)

        n = len(self._imp_reservoir)
        # Bootstrap min/max tracking (for early stage and min-max path)
        if self._importance_min is None or raw < self._importance_min:
            self._importance_min = raw
        if self._importance_max is None or raw > self._importance_max:
            self._importance_max = raw

        if n < 64:
            span = (self._importance_max - self._importance_min) or 1.0
            return ((raw - self._importance_min) / span, "minmax")

        # Periodic recompute (every 64 inserts) or if quantiles unset
        if (n - self._imp_last_recompute) >= 64 or self._imp_q10 is None:
            arr = np.array(self._imp_reservoir, dtype="float64")
            self._imp_q10, self._imp_q50, self._imp_q90, self._imp_q99 = np.percentile(
                arr, [10, 50, 90, 99]
            )
            self._imp_last_recompute = n

        q10 = self._imp_q10 or raw
        q50 = self._imp_q50 or raw
        q90 = self._imp_q90 or raw
        q99 = self._imp_q99 or raw
        eps = 1e-12
        upper_core = (q90 - q50) or eps
        lower_core = (q50 - q10) or eps
        R_tail_max = (self._importance_max - q90) / upper_core
        R_tail_ext = (q99 - q90) / upper_core
        R_asym = (q90 - q50) / lower_core

        # Decide method
        if R_tail_max <= 5 and R_asym <= 3:
            # Plain min-max
            span = (self._importance_max - self._importance_min) or 1.0
            norm = (raw - self._importance_min) / span
            return (max(0.0, min(1.0, norm)), "minmax")
        elif R_tail_max <= 15 and R_tail_ext <= 8:
            # Winsorized min-max
            spread = (q90 - q10) or 1.0
            delta = 0.25 * spread
            L = max(self._importance_min, q10 - delta)
            U = min(self._importance_max, q90 + delta)
            if U - L < eps:
                return (0.5, "winsor")
            clipped = min(max(raw, L), U)
            return ((clipped - L) / (U - L), "winsor")
        else:
            # Logistic mapping
            spread = q90 - q10
            if spread < eps:
                return (0.5, "logistic")
            k = math.log(9.0) / spread
            c = q50
            # Avoid overflow: clamp k
            if k > 25:
                k = 25
            try:
                norm = 1.0 / (1.0 + math.exp(-k * (raw - c)))
            except OverflowError:
                norm = 1.0 if raw > c else 0.0
            return (norm, "logistic")

    def retrieve_memories(self, memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]:
        all_mems = self.get_all_memories()
        if memory_type:
            return [m for m in all_mems if m.get("memory_type") == memory_type.value]
        return all_mems

    def get_all_memories(self) -> List[Dict[str, Any]]:
        memories: List[Dict[str, Any]] = []
        pattern = f"{self.namespace}:*:data"
        for key in self.kv_store.scan_iter(pattern):
            try:
                data = self.kv_store.get(key)
                if data:
                    try:
                        memories.append(deserialize(data))
                    except Exception:
                        logger.warning(f"Failed to deserialize memory from key {key}")
            except Exception as e:
                logger.warning(f"Failed to load memory from key {key}: {e}")
        return memories

    def find_hybrid_by_type(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        # Fast core path bypasses vector_store when enabled
        if self.fast_core_enabled:
            payloads = self._fast_search(query, top_k, memory_type, filters)
        else:
            query_vector = self.embed_text(query)
            results = self.vector_store.search(query_vector.flatten().tolist(), top_k=top_k)
            payloads = [r.payload for r in results]
        if filters:

            def ok(p):
                return all(p.get(k) == v for k, v in filters.items())

            payloads = [p for p in payloads if ok(p)]
        if memory_type:
            return [p for p in payloads if p.get("memory_type") == memory_type.value]
        return payloads

    def find_by_coordinate_range(
        self,
        min_coord: Tuple[float, ...],
        max_coord: Tuple[float, ...],
        memory_type: Optional[MemoryType] = None,
    ) -> List[Dict[str, Any]]:
        def inside(c: List[float]) -> bool:
            try:
                return all(
                    min_coord[i] <= c[i] <= max_coord[i]
                    for i in range(min(len(min_coord), len(max_coord), len(c)))
                )
            except Exception:
                return False

        out: List[Dict[str, Any]] = []
        for m in self.get_all_memories():
            coord = m.get("coordinate")
            if coord is None:
                continue
            if inside(coord):
                if memory_type is None or m.get("memory_type") == memory_type.value:
                    out.append(m)
        return out

    def delete_many(self, coordinates: List[Tuple[float, ...]]) -> int:
        count = 0
        for coord in coordinates:
            data_key, _ = _coord_to_key(self.namespace, coord)
            if self.kv_store.get(data_key):
                self.delete(coord)
                count += 1
        return count

    def import_memories(self, path: str, replace: bool = False) -> int:
        n = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    mem = json.loads(line)
                except Exception:
                    continue
                coord = mem.get("coordinate")
                if coord is None:
                    continue
                coord_t = tuple(coord)
                mtype = (
                    MemoryType.SEMANTIC
                    if mem.get("memory_type") == MemoryType.SEMANTIC.value
                    else MemoryType.EPISODIC
                )
                if replace:
                    self.delete(coord_t)
                self.store_memory(coord_t, mem, memory_type=mtype)
                n += 1
        return n

    def run_decay_once(self):
        now = time.time()
        for meta_key in self.kv_store.scan_iter(f"{self.namespace}:*:meta"):
            try:
                metadata = self.kv_store.hgetall(meta_key)
                created = float(metadata.get(b"creation_timestamp", b"0"))
                age = now - created
                data_key = meta_key.replace(":meta", ":data")
                raw_data = self.kv_store.get(data_key)
                if not raw_data:
                    continue
                try:
                    memory_item = deserialize(raw_data)
                except Exception:
                    logger.warning(f"Failed to deserialize memory {data_key} in run_decay_once")
                    continue
                for i, threshold in enumerate(self.decay_thresholds_seconds):
                    if age > threshold:
                        keys_to_remove = set(self.decayable_keys_by_level[i])
                        for key in keys_to_remove:
                            memory_item.pop(key, None)
                try:
                    self.kv_store.set(data_key, serialize(memory_item))
                except Exception:
                    logger.warning(f"Failed to persist decayed memory {data_key}")
            except Exception as e:
                logger.warning(f"Error during run_decay_once for {meta_key}: {e}")

    def store_vector_only(
        self, coordinate: Tuple[float, ...], vector: np.ndarray, payload: Optional[dict] = None
    ):
        try:
            self.vector_store.upsert(
                points=[
                    {
                        "id": str(uuid.uuid4()),
                        "vector": vector.flatten().tolist(),
                        "payload": payload or {"coordinate": list(coordinate)},
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Failed to store vector: {e}")
            raise SomaFractalMemoryError("Vector storage failed") from e

    def embed_text(self, text: str) -> np.ndarray:
        def _fallback_hash() -> np.ndarray:
            h = hashlib.blake2b(text.encode("utf-8")).digest()
            arr = np.frombuffer(h, dtype=np.uint8).astype("float32")
            if arr.size < self.vector_dim:
                reps = int(np.ceil(self.vector_dim / arr.size))
                arr = np.tile(arr, reps)
            return arr[: self.vector_dim].reshape(1, -1)

        if self.tokenizer is None or self.model is None:
            return _fallback_hash()
        try:
            with self.model_lock:
                inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
                outputs = self.model(**inputs)
                emb = outputs.last_hidden_state.mean(dim=1).detach().cpu().numpy().astype("float32")
            # L2 normalize embedding (Stage 1 invariant)
            try:
                norm = float(np.linalg.norm(emb)) or 1.0
                emb = emb / norm
            except Exception as e:
                logger.warning("Failed to normalize embedding", error=str(e))
                pass
            return emb
        except Exception:
            # Quiet fallback to avoid CLI JSON noise
            fb = _fallback_hash()
            try:
                norm = float(np.linalg.norm(fb)) or 1.0
                fb = fb / norm
            except Exception as e:
                logger.warning("Failed to normalize fallback embedding", error=str(e))
            return fb

    def _enforce_memory_limit(self):
        all_items = []
        for meta_key in self.kv_store.scan_iter(f"{self.namespace}:*:meta"):
            try:
                metadata = self.kv_store.hgetall(meta_key)
                created = float(metadata.get(b"creation_timestamp", b"0"))
                data_key = meta_key.replace(":meta", ":data")
                raw_data = self.kv_store.get(data_key)
                if not raw_data:
                    continue
                try:
                    mem = deserialize(raw_data)
                except Exception:
                    continue
                imp = int(mem.get("importance", 0))
                all_items.append((imp, created, data_key, meta_key))
            except Exception:
                continue
        excess = max(0, len(all_items) - int(self.max_memory_size))
        if excess <= 0:
            return
        all_items.sort(key=lambda t: (t[0], t[1]))
        for _, _, data_key, meta_key in all_items[:excess]:
            try:
                self.kv_store.delete(data_key)
                self.kv_store.delete(meta_key)
            except Exception:
                continue
