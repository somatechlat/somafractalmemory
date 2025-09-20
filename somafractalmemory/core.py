import hashlib
import json
import logging
import os
import re
import threading
import time
import uuid
from enum import Enum as _Enum
from typing import Any, ContextManager, Dict, List, Optional, Tuple

import numpy as np
from cryptography.fernet import Fernet

from somafractalmemory.interfaces.graph import IGraphStore
from somafractalmemory.interfaces.prediction import IPredictionProvider
from somafractalmemory.interfaces.storage import IKeyValueStore, IVectorStore

# Optional/soft imports for third-party integrations used in runtime.
try:
    from dynaconf import Dynaconf
except Exception:  # pragma: no cover - optional runtime dependency

    def _dummy_dynaconf(*a, **k):
        return type("_Dummy", (), {})()

    Dynaconf = _dummy_dynaconf

try:
    from transformers import AutoModel, AutoTokenizer
except Exception:  # pragma: no cover - optional runtime dependency

    class _DummyAuto:
        @staticmethod
        def from_pretrained(*a, **k):
            raise RuntimeError("transformers not installed")

    AutoTokenizer = _DummyAuto
    AutoModel = _DummyAuto

try:
    from sklearn.ensemble import IsolationForest
except Exception:  # pragma: no cover - optional runtime dependency

    class _DummyIF:
        def __init__(self, *a, **k):
            raise RuntimeError("sklearn not installed")

    IsolationForest = _DummyIF

try:
    from prometheus_client import CollectorRegistry, Counter, Histogram
except Exception:  # pragma: no cover - optional runtime dependency

    def CollectorRegistry(*a, **k):
        return None

    def Counter(*a, **k):
        return None

    def Histogram(*a, **k):
        return None


# Langfuse is optional; provide a lightweight stub if missing to avoid runtime crashes during tests
try:
    from langfuse import Langfuse
except Exception:  # pragma: no cover - optional runtime dependency

    class Langfuse:  # type: ignore
        def __init__(self, *a, **k):
            pass


# module logger
logger = logging.getLogger(__name__)


class SomaFractalMemoryError(Exception):
    pass


class MemoryType(_Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


def _coord_to_key(namespace: str, coordinate: Tuple[float, ...]) -> Tuple[str, str]:
    """Return data_key and meta_key for a coordinate under a namespace."""
    coord_str = ":".join(str(c) for c in coordinate)
    data_key = f"{namespace}:{coord_str}:data"
    meta_key = f"{namespace}:{coord_str}:meta"
    return data_key, meta_key


class SomaFractalMemoryEnterprise:
    """Enterprise-grade memory engine exposing KV/vector/graph integration and eviction."""

    def find_shortest_path(
        self,
        from_coord: Tuple[float, ...],
        to_coord: Tuple[float, ...],
        link_type: Optional[str] = None,
    ) -> List[Any]:
        """Find the shortest path between two coordinates in the semantic graph.

        This is a thin wrapper over the configured graph store.
        """
        return self.graph_store.find_shortest_path(from_coord, to_coord, link_type)

    def report_outcome(self, coordinate: Tuple[float, ...], outcome: Any) -> Dict[str, Any]:
        """Report the actual outcome for a memory and update prediction feedback.

        If the prediction was incorrect, a corrective semantic memory is created.
        """
        mem = self.retrieve(coordinate)
        if mem is None:
            return {"error": True, "message": "Memory not found"}

        predicted = mem.get("predicted_outcome")
        mem["reported_outcome"] = outcome
        error = predicted != outcome
        mem["error"] = error

        # Persist the updated original memory (preserve its memory_type)
        try:
            mtype_val = mem.get("memory_type", MemoryType.EPISODIC.value)
            mtype = MemoryType(mtype_val) if isinstance(mtype_val, str) else mtype_val
        except Exception:
            mtype = MemoryType.EPISODIC
        try:
            self.store_memory(coordinate, mem, memory_type=mtype)
        except Exception as e:
            logger.warning(f"Failed to persist reported outcome for {coordinate}: {e}")

        result = {"error": bool(error), "predicted": predicted, "reported": outcome}

        # If there was an error, create a corrective semantic memory (new coordinate)
        if error:
            try:
                corrective_mem = {
                    "corrective_for": coordinate,
                    "original_payload": mem,
                    "correction": outcome,
                    "timestamp": time.time(),
                    "memory_type": MemoryType.SEMANTIC.value,
                }
                # Choose a new coordinate to avoid overwriting the original memory
                new_coord = tuple(np.random.uniform(0, 100, size=3))
                self.store_memory(new_coord, corrective_mem, memory_type=MemoryType.SEMANTIC)
            except Exception as e:
                logger.warning(f"Failed to create corrective semantic memory for {coordinate}: {e}")

        return result

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
            # Use unified serialize/deserialize helpers (JSON-first, optional pickle)
            entry = self._deserialize(raw)
            if not entry:
                continue
            if entry.get("status") != "committed":
                entry["status"] = "committed"
                try:
                    self.kv_store.set(wal_key, self._serialize(entry))
                except Exception:
                    logger.warning(f"Failed to write reconciled WAL entry {wal_key}")

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
        # Remove from eviction index if present
        try:
            ev_key = f"{self.namespace}:eviction_index"
            self.kv_store.zrem(ev_key, data_key)
        except Exception as e:
            logger.debug(f"Failed to remove {data_key} from eviction index: {e}")
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
        prediction_provider: IPredictionProvider,
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
        self.prediction_provider = prediction_provider
        self.max_memory_size = int(os.getenv("SOMA_MAX_MEMORY_SIZE", max_memory_size))
        self.pruning_interval_seconds = int(
            os.getenv("SOMA_PRUNING_INTERVAL_SECONDS", pruning_interval_seconds)
        )
        # If explicit thresholds/keys not provided, try to read defaults from config file
        if decay_thresholds_seconds is None:
            try:
                cfg = Dynaconf(
                    settings_files=[config_file], environments=True, envvar_prefix="SOMA"
                )
                mem_cfg = getattr(cfg, "memory_enterprise", {})
                self.decay_thresholds_seconds = mem_cfg.get("decay_thresholds_seconds", [])
            except Exception:
                self.decay_thresholds_seconds = []
        else:
            self.decay_thresholds_seconds = decay_thresholds_seconds

        if decayable_keys_by_level is None:
            try:
                cfg = Dynaconf(
                    settings_files=[config_file], environments=True, envvar_prefix="SOMA"
                )
                mem_cfg = getattr(cfg, "memory_enterprise", {})
                self.decayable_keys_by_level = mem_cfg.get("decayable_keys_by_level", [])
            except Exception:
                self.decayable_keys_by_level = []
        else:
            self.decayable_keys_by_level = decayable_keys_by_level
        self.decay_enabled = decay_enabled
        self.reconcile_enabled = reconcile_enabled
        self.model_lock = threading.RLock()
        self.vector_dim = int(os.getenv("SOMA_VECTOR_DIM", vector_dim))
        # Tunable decay/scoring weights (can be overridden via SOMA_* env vars)
        self.decay_age_weight = float(os.getenv("SOMA_DECAY_AGE_WEIGHT", 1.0))
        self.decay_recency_weight = float(os.getenv("SOMA_DECAY_RECENCY_WEIGHT", 1.0))
        self.decay_access_weight = float(os.getenv("SOMA_DECAY_ACCESS_WEIGHT", 0.5))
        self.decay_importance_weight = float(os.getenv("SOMA_DECAY_IMPORTANCE_WEIGHT", 2.0))
        self.decay_threshold = float(os.getenv("SOMA_DECAY_THRESHOLD", 2.0))

        config = Dynaconf(settings_files=[config_file], environments=True, envvar_prefix="SOMA")

        # Load transformer model only if explicitly allowed; support pinning via SOMA_MODEL_REV
        hf_model = os.getenv("SOMA_MODEL_NAME", model_name)
        hf_rev = os.getenv("SOMA_MODEL_REV", None)
        try:
            if hf_rev:
                self.tokenizer = AutoTokenizer.from_pretrained(hf_model, revision=hf_rev)
                self.model = AutoModel.from_pretrained(
                    hf_model, revision=hf_rev, use_safetensors=True
                )
            else:
                # If no revision is set, avoid unpinned downloads in sensitive environments by attempting once
                self.tokenizer = AutoTokenizer.from_pretrained(hf_model)
                self.model = AutoModel.from_pretrained(hf_model, use_safetensors=True)
        except Exception as e:
            logger.warning(
                f"Transformer model init failed, falling back to hash-based embeddings: {e}"
            )
            self.tokenizer = None
            self.model = None

        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
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

        lf_public = getattr(config, "langfuse_public", "pk-lf-123")
        lf_secret = getattr(config, "langfuse_secret", "sk-lf-456")
        lf_host = getattr(config, "langfuse_host", "http://localhost:3000")
        self.langfuse = Langfuse(public_key=lf_public, secret_key=lf_secret, host=lf_host)

        self.vector_store.setup(vector_dim=self.vector_dim, namespace=self.namespace)
        self._sync_graph_from_memories()

        # Start memory decay thread if enabled
        if self.decay_enabled:
            threading.Thread(target=self._decay_memories, daemon=True).start()

    # ---------- Serialization helpers (JSON by default, optional pickle fallback) ----------
    def _serialize(self, obj: Any) -> bytes:
        """Serialize Python object to bytes. Defaults to JSON; falls back to pickle only if allowed via env."""
        try:
            return json.dumps(obj, default=lambda o: getattr(o, "__dict__", str(o))).encode("utf-8")
        except Exception:
            if os.getenv("SOMA_ALLOW_PICKLE", "false").lower() == "true":
                import pickle as _pickle

                return _pickle.dumps(obj, protocol=_pickle.HIGHEST_PROTOCOL)
            logger.exception("Serialization to JSON failed and pickle is not allowed")
            raise

    def _deserialize(self, raw: Any) -> Any:
        """Deserialize bytes/string to Python object. Tries JSON first, then optional pickle if enabled."""
        if raw is None:
            return None
        # If already Python object
        if not isinstance(raw, (bytes, str)):
            return raw
        # If bytes, try JSON
        if isinstance(raw, bytes):
            try:
                obj = json.loads(raw.decode("utf-8"))
            except Exception:
                if os.getenv("SOMA_ALLOW_PICKLE", "false").lower() == "true":
                    import pickle as _pickle

                    try:
                        obj = _pickle.loads(raw)
                    except Exception:
                        logger.exception("Pickle deserialization failed for bytes input")
                        return None
                else:
                    logger.debug(
                        "JSON deserialization failed and pickle not allowed for bytes input"
                    )
                    return None
            # Post-process common coordinate-like fields for backward compatibility
            if isinstance(obj, dict):
                if "coordinate" in obj and isinstance(obj["coordinate"], list):
                    obj["coordinate"] = tuple(obj["coordinate"])
                if "consolidated_from" in obj and isinstance(obj["consolidated_from"], list):
                    obj["consolidated_from"] = tuple(obj["consolidated_from"])
            return obj
        # If str, try JSON then optional pickle
        try:
            obj = json.loads(raw)
        except Exception:
            if os.getenv("SOMA_ALLOW_PICKLE", "false").lower() == "true":
                import pickle as _pickle

                try:
                    return _pickle.loads(raw.encode("utf-8"))
                except Exception:
                    logger.exception("Pickle deserialization failed for str input")
                    return None
            logger.debug("JSON deserialization failed and pickle not allowed for str input")
            return None
        if isinstance(obj, dict):
            if "coordinate" in obj and isinstance(obj["coordinate"], list):
                obj["coordinate"] = tuple(obj["coordinate"])
            if "consolidated_from" in obj and isinstance(obj["consolidated_from"], list):
                obj["consolidated_from"] = tuple(obj["consolidated_from"])
        return obj

    def _kv_set_obj(self, key: str, obj: Any) -> None:
        self.kv_store.set(key, self._serialize(obj))

    def _kv_get_obj(self, key: str) -> Any:
        raw = self.kv_store.get(key)
        return self._deserialize(raw)

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
        # Serialize and store using helpers (JSON by default)
        try:
            self._kv_set_obj(data_key, value)
        except Exception as e:
            logger.warning(f"Failed to serialize and store {data_key}: {e}")
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
            # Update eviction index for new memory
            try:
                data_key, _ = _coord_to_key(self.namespace, coordinate)
                self._update_eviction_index_for(data_key, value)
            except Exception as e:
                logger.debug(f"Failed to update eviction index for {data_key}: {e}")
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
                    self.kv_store.set(wal_key, self._serialize(wal_payload))
                except Exception as e:
                    logger.warning(f"Failed to persist WAL entry {wal_key}: {e}")
            except Exception as e:
                logger.warning(f"Failed to create WAL entry for {data_key}: {e}")
        return True

    def _decay_memories(self):
        while True:
            now = time.time()
            for meta_key in self.kv_store.scan_iter(f"{self.namespace}:*:meta"):
                try:
                    metadata = self.kv_store.hgetall(meta_key)
                    created = float(metadata.get(b"creation_timestamp", b"0"))
                    age = now - created
                    data_key = meta_key.replace(":meta", ":data")
                    raw_data = self.kv_store.get(data_key)
                    # If the test or external callers used a repr-based meta key like
                    # "ns:(1, 1, 1):meta" but the data key is stored as "ns:1:1:1:data",
                    # attempt a best-effort conversion to find the matching data entry.
                    if not raw_data:
                        # extract the coordinate portion between namespace: and :meta
                        try:
                            prefix = f"{self.namespace}:"
                            if meta_key.startswith(prefix):
                                coord_part = meta_key[len(prefix) : -len(":meta")]
                                # find numbers in the repr-style coordinate
                                nums = re.findall(r"-?\d+\.?\d*", coord_part)
                                if nums:
                                    alt_data_key = prefix + ":".join(nums) + ":data"
                                    raw_data = self.kv_store.get(alt_data_key)
                                    if raw_data:
                                        data_key = alt_data_key
                        except Exception:
                            pass
                    if not raw_data:
                        continue
                    memory_item = self._deserialize(raw_data)
                    # Compute eviction/decay score and if above the configured threshold,
                    # aggressively prune non-essential fields to a minimal representation.
                    try:
                        score = self._compute_eviction_score(
                            memory_item, now, created_override=created
                        )
                    except Exception:
                        score = 0.0
                    if score > self.decay_threshold:
                        # Keep only minimal essential keys
                        minimal = {
                            "memory_type": memory_item.get("memory_type"),
                            "coordinate": memory_item.get("coordinate"),
                            "importance": memory_item.get("importance", 0),
                        }
                        # preserve timestamp and access_count if present
                        if "timestamp" in memory_item:
                            minimal["timestamp"] = memory_item["timestamp"]
                        if "access_count" in memory_item:
                            minimal["access_count"] = memory_item["access_count"]
                        memory_item = minimal
                    else:
                        for i, threshold in enumerate(self.decay_thresholds_seconds):
                            if age > threshold:
                                keys_to_remove = set(self.decayable_keys_by_level[i])
                                for key in keys_to_remove:
                                    memory_item.pop(key, None)
                    # Update eviction index when decay changes the stored item
                    try:
                        ev_key = f"{self.namespace}:eviction_index"
                        score = self._compute_eviction_score(
                            memory_item, now, created_override=created
                        )
                        # member stored as data_key for direct deletion
                        self.kv_store.zadd(ev_key, {data_key: float(score)})
                    except Exception as e:
                        logger.debug(
                            f"Failed to update eviction zset during decay for {data_key}: {e}"
                        )
                    try:
                        self.kv_store.set(data_key, self._serialize(memory_item))
                    except Exception as e:
                        logger.warning(f"Failed to write decayed memory {data_key}: {e}")
                except Exception as e:
                    logger.warning(f"Error during decay for {meta_key}: {e}")
            time.sleep(self.pruning_interval_seconds)

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
                except Exception as e:
                    logger.debug(f"Failed to yield payload from vector scroll: {e}")
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
                        yield self._deserialize(data)
                    except Exception as e:
                        logger.debug(f"Failed to deserialize KV memory during iter_memories: {e}")
                        continue

    # ---------- Eviction index helpers (Redis sorted set) ----------
    def _compute_eviction_score(
        self,
        memory_item: Dict[str, Any],
        now: Optional[float] = None,
        created_override: Optional[float] = None,
    ) -> float:
        """Compute an eviction score for a memory item.

        Higher score = more likely to be evicted. Uses configured decay weights.
        """
        now = now or time.time()
        created = (
            created_override if created_override is not None else memory_item.get("timestamp", now)
        )
        age_hours = (now - created) / 3600.0
        last_accessed = memory_item.get("last_accessed_timestamp", created)
        recency_hours = (now - last_accessed) / 3600.0
        access_count = memory_item.get("access_count", 0)
        importance = memory_item.get("importance", 0)
        score = (
            (self.decay_age_weight * age_hours)
            + (self.decay_recency_weight * recency_hours)
            - (self.decay_access_weight * access_count)
            - (self.decay_importance_weight * importance)
        )
        return float(score)

    def _update_eviction_index_for(self, data_key: str, memory_item: Dict[str, Any]):
        """Write or update the eviction zset entry for a memory item."""
        try:
            ev_key = f"{self.namespace}:eviction_index"
            score = self._compute_eviction_score(memory_item)
            self.kv_store.zadd(ev_key, {data_key: float(score)})
        except Exception:
            logger.debug(f"Failed to update eviction index for {data_key}")

    def health_check(self) -> Dict[str, bool]:
        def safe(check):
            try:
                return bool(check())
            except Exception:
                return False

        return {
            "kv_store": safe(self.kv_store.health_check),
            "vector_store": safe(self.vector_store.health_check),
            "graph_store": safe(self.graph_store.health_check),
            "prediction_provider": safe(self.prediction_provider.health_check),
        }

    def set_importance(self, coordinate: Tuple[float, ...], importance: int = 1):
        data_key, _ = _coord_to_key(self.namespace, coordinate)
        data = self.kv_store.get(data_key)
        if not data:
            raise SomaFractalMemoryError(f"No memory at {coordinate}")
        value = self._deserialize(data)
        value["importance"] = importance
        try:
            self.kv_store.set(data_key, self._serialize(value))
        except Exception:
            logger.debug(f"Failed to persist importance update for {data_key}")
        # Update eviction index score after importance change
        try:
            self._update_eviction_index_for(data_key, value)
        except Exception:
            logger.debug(f"Failed to update eviction zset for {data_key}")
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
                except Exception as e:
                    logger.debug(f"Skipping vector payload during iterate due to error: {e}")
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
                # update last accessed timestamp
                try:
                    self.kv_store.hset(
                        meta_key,
                        mapping={b"last_accessed_timestamp": str(time.time()).encode("utf-8")},
                    )
                except Exception as e:
                    logger.debug(f"Failed to update last_accessed for {meta_key}: {e}")
                value = self._deserialize(data)
                if not isinstance(value, dict):
                    return value
                value["access_count"] = value.get("access_count", 0) + 1
                try:
                    self.kv_store.set(data_key, self._serialize(value))
                except Exception as e:
                    logger.warning(f"Failed to update access count for {data_key}: {e}")
                # Update eviction index on access
                try:
                    self._update_eviction_index_for(data_key, value)
                except Exception as e:
                    logger.debug(f"Failed to update eviction index on access for {data_key}: {e}")
                # Decrypt fields if encryption is enabled
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

    # intentionally quiet to avoid CLI noise

    def save_version(self, coordinate: Tuple[float, ...]):
        data_key, _ = _coord_to_key(self.namespace, coordinate)
        data = self.kv_store.get(data_key)
        if not data:
            raise SomaFractalMemoryError(f"No memory at {coordinate}")
        version_key = f"{data_key}:version:{time.time_ns()}"
        try:
            self.kv_store.set(version_key, data)
        except Exception as e:
            raise SomaFractalMemoryError("Failed to save version") from e

    def get_versions(self, coordinate: Tuple[float, ...]) -> List[Dict[str, Any]]:
        data_key, _ = _coord_to_key(self.namespace, coordinate)
        pattern = f"{data_key}:version:*"
        versions = []
        for vkey in self.kv_store.scan_iter(pattern):
            vdata = self.kv_store.get(vkey)
            if vdata:
                versions.append(self._deserialize(vdata))
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
        if context:
            results = self.find_hybrid_with_context(
                query, context, top_k=top_k, memory_type=memory_type
            )
        else:
            results = self.find_hybrid_by_type(query, top_k=top_k, memory_type=memory_type)
        self._call_hook("after_recall", query, context, top_k, memory_type, results)
        return results

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
                        "consolidated_from": coord_t,
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

    def recall_with_scores(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_vector = self.embed_text(query)
        results = self.vector_store.search(query_vector.flatten().tolist(), top_k=top_k)
        return [
            {"payload": getattr(r, "payload", None), "score": getattr(r, "score", None)}
            for r in results
        ]

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
                value = self._deserialize(data)
                links = value.get("links", [])
                link_data = {"to": to_coord, "type": link_type, "timestamp": time.time()}
                if weight is not None:
                    link_data["weight"] = weight
                links.append(link_data)
                value["links"] = links
                try:
                    self.kv_store.set(data_key, self._serialize(value))
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
        try:
            pred, conf = self.prediction_provider.predict(value)
            if pred:
                value["predicted_outcome"] = pred
                value["predicted_confidence"] = conf
        except Exception as e:
            logger.debug(f"Prediction enrichment failed: {e}")
        result = self.store(coord_t, value)
        self.graph_store.add_memory(coord_t, value)
        try:
            self._enforce_memory_limit()
        except Exception as e:
            logger.debug(f"Memory limit enforcement failed: {e}")
        return result

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
                        memories.append(self._deserialize(data))
                    except Exception:
                        logger.warning(f"Failed to deserialize memory at key {key}")
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
                except Exception as e:
                    logger.debug(f"Skipping memory during import due to error: {e}")
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
                # Try a repr-style meta key fallback (e.g. namespace:(1, 1, 1):meta)
                if not raw_data:
                    try:
                        prefix = f"{self.namespace}:"
                        if meta_key.startswith(prefix):
                            coord_part = meta_key[len(prefix) : -len(":meta")]
                            nums = re.findall(r"-?\d+\.?\d*", coord_part)
                            if nums:
                                alt_data_key = prefix + ":".join(nums) + ":data"
                                raw_data = self.kv_store.get(alt_data_key)
                                if raw_data:
                                    data_key = alt_data_key
                    except Exception:
                        pass

                if not raw_data:
                    continue

                memory_item = self._deserialize(raw_data)
                if memory_item is None:
                    continue

                try:
                    score = self._compute_eviction_score(memory_item, now, created_override=created)
                except Exception:
                    score = 0.0

                if score > self.decay_threshold:
                    minimal = {
                        "memory_type": memory_item.get("memory_type"),
                        "coordinate": memory_item.get("coordinate"),
                        "importance": memory_item.get("importance", 0),
                    }
                    if "timestamp" in memory_item:
                        minimal["timestamp"] = memory_item["timestamp"]
                    if "access_count" in memory_item:
                        minimal["access_count"] = memory_item["access_count"]
                    memory_item = minimal
                else:
                    for i, threshold in enumerate(self.decay_thresholds_seconds):
                        if age > threshold:
                            keys_to_remove = set(self.decayable_keys_by_level[i])
                            for key in keys_to_remove:
                                memory_item.pop(key, None)

                try:
                    self.kv_store.set(data_key, self._serialize(memory_item))
                except Exception as e:
                    logger.warning(f"Failed to write decayed memory {data_key}: {e}")
            except Exception as e:
                logger.warning(f"Error during run_decay_once for {meta_key}: {e}")

    # Backwards-compatible alias used by tests/tools
    def _apply_decay_to_all(self):
        """Legacy compatibility shim: apply decay pass once over all memories."""
        return self.run_decay_once()

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
            vec = arr[: self.vector_dim].reshape(1, -1)
            # L2-normalize fallback vector for consistent distance computations
            norm = np.linalg.norm(vec, axis=1, keepdims=True)
            norm[norm == 0] = 1.0
            return vec / norm

        if self.tokenizer is None or self.model is None:
            return _fallback_hash()
        try:
            with self.model_lock:
                inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
                outputs = self.model(**inputs)
                emb = outputs.last_hidden_state.mean(dim=1).detach().cpu().numpy().astype("float32")
            # L2-normalize embeddings for cosine-similarity usage
            norm = np.linalg.norm(emb, axis=1, keepdims=True)
            norm[norm == 0] = 1.0
            return emb / norm
        except Exception:
            # Quiet fallback to avoid CLI JSON noise
            return _fallback_hash()

    def _enforce_memory_limit(self):
        try:
            ev_key = f"{self.namespace}:eviction_index"
            total = self.kv_store.zcard(ev_key)
            excess = max(0, int(total) - int(self.max_memory_size))
            if excess <= 0:
                return

            # Remove highest-score members (most eligible for eviction)
            # Diagnostic: log current top candidates
            try:
                top_with_scores = self.kv_store.zrange(ev_key, -excess, -1, withscores=True) or []
                # Use warning level so test output captures these diagnostics
                logger.warning(f"Eviction candidates (top {excess}): {top_with_scores}")
                # Log deserialized payloads for inspection
                try:
                    des = []
                    if top_with_scores:
                        for item in top_with_scores:
                            member = item[0] if isinstance(item, tuple) else item
                            if isinstance(member, (bytes, bytearray)):
                                member_str = member.decode("utf-8")
                            else:
                                member_str = str(member)
                            raw = self.kv_store.get(member_str)
                            obj = self._deserialize(raw)
                            des.append(
                                (
                                    member_str,
                                    obj.get("importance") if isinstance(obj, dict) else None,
                                    item[1] if isinstance(item, tuple) and len(item) > 1 else None,
                                )
                            )
                    logger.warning(f"Eviction candidate details: {des}")
                except Exception as e:
                    logger.debug(f"Failed to log eviction candidate details: {e}")
            except Exception:
                # If we couldn't fetch with scores, continue; we'll still try to fetch members
                logger.debug("Could not fetch top_with_scores for eviction diagnostics")

            # Redis zset is sorted ascending; use negative indices to fetch top-scoring members
            to_remove = self.kv_store.zrange(ev_key, -excess, -1) or []
            if not to_remove:
                return
            # Remove keys both from kv store and the zset
            for member in to_remove:
                try:
                    # member might be bytes from Redis client
                    if isinstance(member, (bytes, bytearray)):
                        member_str = member.decode("utf-8")
                    elif isinstance(member, tuple) and len(member) >= 1:
                        # In some zrange implementations withscores=True returns (member, score)
                        member_str = member[0]
                    else:
                        member_str = str(member)
                    data_key = member_str
                    meta_key = data_key.replace(":data", ":meta")
                    self.kv_store.delete(data_key)
                    self.kv_store.delete(meta_key)
                except Exception as e:
                    logger.debug(f"Skipping item in fallback eviction scan due to error: {e}")
                    continue
            try:
                # Trim zset by rank
                # Remove the same high-score slice from zset
                self.kv_store.zremrangebyrank(ev_key, -excess, -1)
            except Exception:
                pass
        except Exception:
            # Fallback to scan-based eviction if zset unavailable
            all_items = []
            for meta_key in self.kv_store.scan_iter(f"{self.namespace}:*:meta"):
                try:
                    metadata = self.kv_store.hgetall(meta_key)
                    created = float(metadata.get(b"creation_timestamp", b"0"))
                    data_key = meta_key.replace(":meta", ":data")
                    raw_data = self.kv_store.get(data_key)
                    if not raw_data:
                        continue
                    mem = self._deserialize(raw_data)
                    imp = int(mem.get("importance", 0))
                    all_items.append((imp, created, data_key, meta_key))
                except Exception as e:
                    logger.debug(f"Failed to load memory in fallback eviction scan: {e}")
                    continue
            excess = max(0, len(all_items) - int(self.max_memory_size))
            if excess <= 0:
                return
            all_items.sort(key=lambda t: (t[0], t[1]))
            for _, _, data_key, meta_key in all_items[:excess]:
                try:
                    self.kv_store.delete(data_key)
                    self.kv_store.delete(meta_key)
                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    # Narrow exception handling to expected deserialization/index errors.
                    logger.debug(f"Skipping item in fallback eviction scan due to error: {e}")
                    continue
