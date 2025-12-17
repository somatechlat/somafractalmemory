# isort: skip_file
# ruff: noqa
"""SomaFractalMemory Core - Refactored for VIBE compliance (<500 lines).

This module contains the main SomaFractalMemoryEnterprise class with operations
delegated to the operations/ submodules.
"""

import hashlib
import threading
import time
from enum import Enum
from functools import lru_cache
from typing import Any, ContextManager, Dict, List, Optional, Tuple

import numpy as np
import structlog
from cryptography.fernet import Fernet
from prometheus_client import CollectorRegistry, Counter, Histogram

from common.config.settings import load_settings
from .interfaces.graph import IGraphStore
from .interfaces.storage import IKeyValueStore, IVectorStore
from .serialization import deserialize, serialize

# Import operations modules
from .operations import (
    store_op,
    store_memory_op,
    store_memories_bulk_op,
    store_vector_only_op,
    import_memories_op,
    export_memories_op,
    retrieve_op,
    retrieve_memories_op,
    get_all_memories_op,
    get_versions_op,
    save_version_op,
    recall_op,
    hybrid_recall_op,
    hybrid_recall_with_scores_op,
    keyword_search_op,
    find_hybrid_with_context_op,
    find_hybrid_by_type_op,
    find_by_coordinate_range_op,
    delete_op,
    forget_op,
    delete_many_op,
    remove_vector_entries_op,
    link_memories_op,
    get_linked_memories_op,
    find_shortest_path_op,
    sync_graph_from_memories_op,
    memory_stats_op,
    summarize_memories_op,
    get_recent_op,
    get_important_op,
    health_check_op,
    audit_log_op,
    decay_memories_op,
    apply_decay_to_all_op,
    run_decay_once_op,
    consolidate_memories_op,
    replay_memories_op,
    reflect_op,
    enforce_memory_limit_op,
    adaptive_importance_norm_op,
)

_settings = load_settings()
logger = structlog.get_logger()


class DeleteError(RuntimeError):
    """Base class for errors raised during a delete operation."""


class KeyValueStoreError(DeleteError):
    """Raised when the KV store fails during delete."""


class VectorStoreError(DeleteError):
    """Raised when the vector store fails during delete."""


class MemoryType(Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class SomaFractalMemoryError(Exception):
    pass


def _coord_to_key(namespace: str, coord: Tuple[float, ...]) -> Tuple[str, str]:
    coord_str = repr(coord)
    return f"{namespace}:{coord_str}:data", f"{namespace}:{coord_str}:meta"


class SomaFractalMemoryEnterprise:
    """Enterprise-grade agentic memory system with modular backends."""

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
        self.namespace = _settings.namespace or namespace
        self.kv_store = kv_store
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.max_memory_size = int(_settings.max_memory_size or max_memory_size)
        self.pruning_interval_seconds = int(
            getattr(_settings, "pruning_interval_seconds", pruning_interval_seconds)
        )
        self.decay_thresholds_seconds = decay_thresholds_seconds or []
        self.decayable_keys_by_level = decayable_keys_by_level or []
        self.decay_enabled = decay_enabled
        self.reconcile_enabled = reconcile_enabled
        self.model_lock = threading.RLock()
        self.vector_dim = int(_settings.vector_dim or vector_dim)
        self.fast_core_enabled = _settings.fast_core_enabled

        # Adaptive importance normalization state
        self._imp_reservoir: List[float] = []
        self._imp_reservoir_max = 512
        self._imp_last_recompute = 0
        self._imp_q10 = self._imp_q50 = self._imp_q90 = self._imp_q99 = None
        self._imp_method = "minmax"
        self._importance_min = None
        self._importance_max = None

        # Fast core slabs
        if self.fast_core_enabled:
            self._fast_capacity = 1024
            self._fast_size = 0
            self._fast_vectors = np.zeros((self._fast_capacity, self.vector_dim), dtype="float32")
            self._fast_importance = np.zeros(self._fast_capacity, dtype="float32")
            self._fast_timestamps = np.zeros(self._fast_capacity, dtype="float64")
            self._fast_payloads: List[Optional[Dict[str, Any]]] = [None] * self._fast_capacity

        config = load_settings(config_file=config_file)
        self._allow_negative = bool(getattr(config, "similarity_allow_negative", False))
        self._hybrid_boost = float(getattr(config, "hybrid_boost", 2.0))
        self._hybrid_candidate_multiplier = float(
            getattr(config, "hybrid_candidate_multiplier", 4.0)
        )
        self._imp_stride = int(getattr(config, "importance_recompute_stride", 64))
        self._imp_winsor_delta = float(getattr(config, "importance_winsor_delta", 0.25))
        self._imp_logit_target_ratio = float(
            getattr(config, "importance_logistic_target_ratio", 9.0)
        )
        self._imp_logit_k_max = float(getattr(config, "importance_logistic_k_max", 25.0))
        self._decay_w_age = float(getattr(config, "decay_age_hours_weight", 1.0))
        self._decay_w_recency = float(getattr(config, "decay_recency_hours_weight", 1.0))
        self._decay_w_access = float(getattr(config, "decay_access_weight", 0.5))
        self._decay_w_importance = float(getattr(config, "decay_importance_weight", 2.0))
        self._decay_threshold = float(getattr(config, "decay_threshold", 2.0))

        # Embedding model
        force_hash = _settings.force_hash_embeddings
        if force_hash:
            self.tokenizer = None
            self.model = None
        else:
            try:
                from transformers import AutoModel, AutoTokenizer

                self.tokenizer = AutoTokenizer.from_pretrained(
                    _settings.model_name, revision="main"
                )
                self.model = AutoModel.from_pretrained(
                    _settings.model_name, use_safetensors=True, revision="main"
                )
            except Exception:
                self.tokenizer = None
                self.model = None

        self.anomaly_detector = None
        self.cipher = Fernet(encryption_key or Fernet.generate_key()) if encryption_key else None

        # Prometheus metrics
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

        self.eventing_enabled = False
        self.langfuse = None
        self.vector_store.setup(vector_dim=self.vector_dim, namespace=self.namespace)
        try:
            setattr(self.vector_store, "_allow_negative", self._allow_negative)
        except Exception:
            pass
        sync_graph_from_memories_op(self)

        if self.decay_enabled:
            threading.Thread(target=lambda: decay_memories_op(self), daemon=True).start()

        self.hybrid_recall_default = _settings.hybrid_recall_default
        self._hooks: Dict[str, Any] = {}

    # --- Hooks ---
    def set_hook(self, event: str, func):
        self._hooks[event] = func

    def _call_hook(self, event: str, *args, **kwargs):
        if event in self._hooks:
            try:
                self._hooks[event](*args, **kwargs)
            except Exception as e:
                logger.warning(f"Hook {event} failed: {e}")

    # --- Lock ---
    def acquire_lock(self, name: str, timeout: int = 10) -> ContextManager:
        return self.kv_store.lock(name, timeout)

    def with_lock(self, name: str, func, *args, **kwargs):
        lock = self.acquire_lock(name)
        if lock:
            with lock:
                return func(*args, **kwargs)
        return func(*args, **kwargs)

    # --- Embedding ---
    def embed_text(self, text: str) -> np.ndarray:
        @lru_cache(maxsize=10000)
        def _cached_fallback_hash(s: str) -> np.ndarray:
            h = hashlib.blake2b(s.encode("utf-8")).digest()
            arr = np.frombuffer(h, dtype=np.uint8).astype("float32")
            if arr.size < self.vector_dim:
                arr = np.tile(arr, int(np.ceil(self.vector_dim / arr.size)))
            return arr[: self.vector_dim].reshape(1, -1)

        if self.tokenizer is None or self.model is None:
            return _cached_fallback_hash(text)
        try:
            with self.model_lock:
                inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
                outputs = self.model(**inputs)
                emb = outputs.last_hidden_state.mean(dim=1).detach().cpu().numpy().astype("float32")
            norm = float(np.linalg.norm(emb)) or 1.0
            return emb / norm
        except Exception:
            return _cached_fallback_hash(text)

    # --- Delegated Operations ---
    def store(self, coordinate: Tuple[float, ...], value: dict):
        return store_op(self, coordinate, value)

    def store_memory(
        self, coordinate, value: Dict[str, Any], memory_type: MemoryType = MemoryType.EPISODIC
    ):
        return store_memory_op(self, coordinate, value, memory_type)

    def store_memories_bulk(
        self, items: List[Tuple[Tuple[float, ...], Dict[str, Any], MemoryType]]
    ):
        return store_memories_bulk_op(self, items)

    def store_vector_only(
        self, coordinate: Tuple[float, ...], vector: np.ndarray, payload: Optional[dict] = None
    ):
        return store_vector_only_op(self, coordinate, vector, payload)

    def import_memories(self, path: str, replace: bool = False) -> int:
        return import_memories_op(self, path, replace)

    def export_memories(self, path: str) -> int:
        return export_memories_op(self, path)

    def retrieve(self, coordinate: Tuple[float, ...]) -> Optional[Dict[str, Any]]:
        return retrieve_op(self, coordinate)

    def retrieve_memories(self, memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]:
        return retrieve_memories_op(self, memory_type)

    def get_all_memories(self) -> List[Dict[str, Any]]:
        return get_all_memories_op(self)

    def get_versions(self, coordinate: Tuple[float, ...]) -> List[Dict[str, Any]]:
        return get_versions_op(self, coordinate)

    def save_version(self, coordinate: Tuple[float, ...]):
        return save_version_op(self, coordinate)

    def recall(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
    ):
        return recall_op(self, query, context, top_k, memory_type)

    def hybrid_recall(
        self,
        query: str,
        *,
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
        exact: bool = True,
        case_sensitive: bool = False,
        terms: Optional[List[str]] = None,
    ):
        return hybrid_recall_op(
            self,
            query,
            top_k=top_k,
            memory_type=memory_type,
            exact=exact,
            case_sensitive=case_sensitive,
            terms=terms,
        )

    def hybrid_recall_with_scores(
        self,
        query: str,
        *,
        terms: Optional[List[str]] = None,
        boost: float | None = None,
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
        exact: bool = True,
        case_sensitive: bool = False,
    ):
        return hybrid_recall_with_scores_op(
            self,
            query,
            terms=terms,
            boost=boost,
            top_k=top_k,
            memory_type=memory_type,
            exact=exact,
            case_sensitive=case_sensitive,
        )

    def keyword_search(
        self,
        term: str,
        *,
        exact: bool = True,
        case_sensitive: bool = False,
        top_k: int = 50,
        memory_type: Optional[MemoryType] = None,
    ):
        return keyword_search_op(
            self,
            term,
            exact=exact,
            case_sensitive=case_sensitive,
            top_k=top_k,
            memory_type=memory_type,
        )

    def find_hybrid_with_context(
        self,
        query: str,
        context: Dict[str, Any],
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
        **kwargs,
    ):
        return find_hybrid_with_context_op(self, query, context, top_k, memory_type, **kwargs)

    def find_hybrid_by_type(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        return find_hybrid_by_type_op(self, query, top_k, memory_type, filters, **kwargs)

    def find_by_coordinate_range(
        self,
        min_coord: Tuple[float, ...],
        max_coord: Tuple[float, ...],
        memory_type: Optional[MemoryType] = None,
    ):
        return find_by_coordinate_range_op(self, min_coord, max_coord, memory_type)

    def delete(self, coordinate: Tuple[float, ...]) -> bool:
        return delete_op(self, coordinate)

    def forget(self, coordinate: Tuple[float, ...]):
        return forget_op(self, coordinate)

    def delete_many(self, coordinates: List[Tuple[float, ...]]) -> int:
        return delete_many_op(self, coordinates)

    def _remove_vector_entries(self, coordinate: Tuple[float, ...]) -> None:
        return remove_vector_entries_op(self, coordinate)

    def link_memories(
        self,
        from_coord: Tuple[float, ...],
        to_coord: Tuple[float, ...],
        link_type: str = "related",
        weight: Optional[float] = None,
    ):
        return link_memories_op(self, from_coord, to_coord, link_type, weight)

    def get_linked_memories(
        self, coord: Tuple[float, ...], link_type: Optional[str] = None, depth: int = 1
    ):
        return get_linked_memories_op(self, coord, link_type, depth)

    def find_shortest_path(
        self,
        from_coord: Tuple[float, ...],
        to_coord: Tuple[float, ...],
        link_type: Optional[str] = None,
    ):
        return find_shortest_path_op(self, from_coord, to_coord, link_type)

    def _sync_graph_from_memories(self) -> None:
        return sync_graph_from_memories_op(self)

    def memory_stats(self) -> Dict[str, Any]:
        return memory_stats_op(self)

    def summarize_memories(
        self, n: int = 10, memory_type: Optional[MemoryType] = None
    ) -> List[str]:
        return summarize_memories_op(self, n, memory_type)

    def get_recent(
        self, n: int = 10, memory_type: Optional[MemoryType] = None
    ) -> List[Dict[str, Any]]:
        return get_recent_op(self, n, memory_type)

    def get_important(
        self, n: int = 10, memory_type: Optional[MemoryType] = None
    ) -> List[Dict[str, Any]]:
        return get_important_op(self, n, memory_type)

    def health_check(self) -> Dict[str, bool]:
        return health_check_op(self)

    def audit_log(self, action: str, coordinate: Tuple[float, ...], user: str = "system"):
        return audit_log_op(self, action, coordinate, user)

    def _decay_memories(self):
        return decay_memories_op(self)

    def _apply_decay_to_all(self):
        return apply_decay_to_all_op(self)

    def run_decay_once(self):
        return run_decay_once_op(self)

    def consolidate_memories(self, window_seconds: int = 3600):
        return consolidate_memories_op(self, window_seconds)

    def replay_memories(self, n: int = 5, memory_type: MemoryType = MemoryType.EPISODIC):
        return replay_memories_op(self, n, memory_type)

    def reflect(self, n: int = 5, memory_type: MemoryType = MemoryType.EPISODIC):
        return reflect_op(self, n, memory_type)

    def _enforce_memory_limit(self):
        return enforce_memory_limit_op(self)

    def _adaptive_importance_norm(self, raw: float) -> Tuple[float, str]:
        return adaptive_importance_norm_op(self, raw)

    # --- Additional methods that remain in core ---
    def iter_memories(self, pattern: Optional[str] = None):
        from .operations.retrieve import iter_memories_op

        return iter_memories_op(self, pattern)

    def set_importance(self, coordinate: Tuple[float, ...], importance: int = 1):
        data_key, _ = _coord_to_key(self.namespace, coordinate)
        data = self.kv_store.get(data_key)
        if not data:
            raise SomaFractalMemoryError(f"No memory at {coordinate}")
        value = deserialize(data)
        value["importance"] = importance
        self.kv_store.set(data_key, serialize(value))

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

    def share_memory_with(self, other_agent, filter_fn=None):
        for mem in self.get_all_memories():
            if filter_fn is None or filter_fn(mem):
                other_agent.store_memory(
                    mem.get("coordinate"),
                    mem,
                    memory_type=MemoryType(mem.get("memory_type", "episodic")),
                )

    def _reconcile_once(self):
        wal_prefix = f"{self.namespace}:wal:"
        for wal_key in self.kv_store.scan_iter(f"{wal_prefix}*"):
            raw = self.kv_store.get(wal_key)
            if not raw:
                continue
            try:
                entry = deserialize(raw)
            except Exception:
                continue
            if entry.get("status") != "committed":
                entry["status"] = "committed"
                try:
                    self.kv_store.set(wal_key, serialize(entry))
                except Exception:
                    pass
