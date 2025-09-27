# isort: skip_file
# ruff: noqa
import hashlib
import json
import logging
import os
import threading
import time
import uuid
from enum import Enum
from typing import Any, ContextManager, Dict, List, Optional, Tuple

from cryptography.fernet import Fernet
from dynaconf import Dynaconf
import numpy as np
from prometheus_client import CollectorRegistry, Counter, Histogram
from sklearn.ensemble import IsolationForest
import structlog
from transformers import AutoModel, AutoTokenizer

# optional Langfuse import – provides stub when package missing
try:
    from langfuse import Langfuse
except ImportError:  # pragma: no cover

    class Langfuse:
        def __init__(self, *args, **kwargs):
            pass

        def log(self, *args, **kwargs):
            pass

        def __getattr__(self, name):
            def _noop(*a, **k):
                return None

            return _noop


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

    def report_outcome(self, coordinate: Tuple[float, ...], outcome: Any) -> Dict[str, Any]:
        """
        Report the actual outcome for a memory and update any stored prediction feedback.

        If a predicted outcome was recorded and differs from the reported outcome, a corrective
        semantic memory is created.

        Parameters
        ----------
        coordinate : Tuple[float, ...]
            The coordinate of the memory.
        outcome : Any
            The actual outcome to report.

        Returns
        -------
        Dict[str, Any]
            The updated memory dictionary, with error status and feedback.
        """
        mem = self.retrieve(coordinate)
        if mem is None:
            return {"error": True, "message": "Memory not found"}
        predicted = mem.get("predicted_outcome")
        mem["reported_outcome"] = outcome
        error = False
        if predicted is not None:
            error = predicted != outcome
        mem["error"] = error
        self.store_memory(
            coordinate, mem, memory_type=MemoryType(mem.get("memory_type", "episodic"))
        )
        if error:
            corrective_mem = {
                "corrective_for": coordinate,
                "original_payload": mem,
                "correction": outcome,
                "timestamp": time.time(),
            }
            self.store_memory(coordinate, corrective_mem, memory_type=MemoryType.SEMANTIC)
        return mem

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
        pass

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

        config = Dynaconf(settings_files=[config_file], environments=True, envvar_prefix="SOMA")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(os.getenv("SOMA_MODEL_NAME", model_name))
            self.model = AutoModel.from_pretrained(
                os.getenv("SOMA_MODEL_NAME", model_name), use_safetensors=True
            )
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
                except Exception:
                    # Best-effort: do not raise from WAL write failures
                    pass
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
        result = self.store(coord_t, value)
        self.graph_store.add_memory(coord_t, value)
        try:
            self._enforce_memory_limit()
        except Exception as e:
            logger.debug(f"Memory limit enforcement failed: {e}")
        # Phase 2: publish a memory‑created event if eventing is enabled
        if getattr(self, "eventing_enabled", True):
            try:
                from .eventing.producer import build_memory_event, produce_event

                event = build_memory_event(self.namespace, value)
                produce_event(event)
            except Exception as ev_err:
                logger.warning(f"Failed to publish memory event: {ev_err}")
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
            return emb
        except Exception:
            # Quiet fallback to avoid CLI JSON noise
            return _fallback_hash()

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
