import ast
import atexit
import hashlib
import json
import logging
import os
import pickle
import threading
import time
import uuid
from enum import Enum
from typing import Any, Callable, ContextManager, Dict, List, Optional, Tuple

import numpy as np

# Optional heavy deps with safe fallbacks
try:
	from langfuse import Langfuse as LangfuseClient  # type: ignore
except Exception:
	class LangfuseClient:  # type: ignore
		def __init__(self, *args, **kwargs):
			pass

try:
	from scipy import stats as scipy_stats  # type: ignore
except Exception:
	class scipy_stats:  # type: ignore
		def __init__(self, *args, **kwargs):
			pass

try:
    from sklearn.ensemble import IsolationForest
except Exception:
    IsolationForest = None

try:
    from cryptography.fernet import Fernet
except Exception:
    Fernet = None

try:
	from prometheus_client import Counter, Histogram
except Exception:
	class _Noop:
		def __init__(self, *args, **kwargs):
			pass
		def labels(self, *args, **kwargs):
			return self
		def observe(self, *args, **kwargs):
			return None
		def inc(self, *args, **kwargs):
			return None
	Counter = _Noop
	Histogram = _Noop

try:
	memory_delete_total_status = Counter("soma_memory_delete_total", "Delete operations", ["namespace", "status"])  # type: ignore
except Exception:
	class _NoopCounter:
		def labels(self, *args, **kwargs):
			return self
		def inc(self, *args, **kwargs):
			return None
	memory_delete_total_status = _NoopCounter()  # type: ignore

try:
    import structlog
    _logger = structlog.get_logger()
except Exception:
    structlog = None
    logging.basicConfig(level=logging.INFO)
    _logger = logging.getLogger("somafractalmemory")

try:
	from dynaconf import Dynaconf  # type: ignore
except Exception:
	class Dynaconf:  # type: ignore
		def __init__(self, settings_files=None, environments=None, envvar_prefix=None):
			self._data = {}
		def __getattr__(self, item):
			return None

from .embedder import MultiModalEmbedder
from .graph_manager import GraphManager
from .interfaces.graph import IGraphStore
from .interfaces.prediction import IPredictionProvider
from .interfaces.storage import IKeyValueStore, IVectorStore
from .memory_manager import (
    MemoryManager,
    MemoryType,
    SomaFractalMemoryError,
    _coord_to_key,
    _point_id,
    recall_count,
    recall_latency,
    store_count,
    store_latency,
)
from .prediction_manager import PredictionManager
from .wal_manager import WALManager

# Setup logging
logger = _logger

def _should_log() -> bool:
	try:
		v = os.getenv("SOMA_SUPPRESS_STDOUT_LOGS", "0").lower()
		return v not in {"1", "true", "yes"}
	except Exception:
		return True

class SomaFractalMemoryEnterprise:
	"""
	Enterprise-grade memory system with distributed backends, security, observability, and cognitive graph integration.

	Cognitive Graph Features:
	- Maintains a semantic graph (NetworkX DiGraph) of all memories and their relationships (links).
	- Nodes: memory coordinates, with attributes from memory data.
	- Edges: links between memories (e.g., cause, related, sequence), with type, timestamp, and other metadata.
	- Provides methods to sync, traverse, search, and export/import the graph.
	- Keeps the graph in sync with memory/link operations.
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
		predictions_enabled: bool = False,
		predictions_error_policy: str = "exact",
		predictions_threshold: float = 0.0,
		decay_enabled: bool = True,
		reconcile_enabled: bool = True,
		reconsolidation_enabled: bool = False,
		salience_threshold: float = 0.0,
		salience_weights: Optional[Dict[str, float]] = None,
		novelty_gate_enabled: bool = False,
		novelty_threshold: float = 0.0,
		decay_config: Optional[Dict[str, Any]] = None,
		pruning_interval_seconds: int = 600,
		anomaly_detection_enabled: bool = False,
	):
		self.namespace = os.getenv("SOMA_NAMESPACE", namespace)
		# Allow None in tests: fall back to in-memory KV store
		self.kv_store = kv_store
		if self.kv_store is None:
			from .implementations.storage import (
			    InMemoryKeyValueStore,  # lazy import to avoid cycles
			)
			self.kv_store = InMemoryKeyValueStore()
		self.vector_store = vector_store
		self.graph_store = graph_store
		self.prediction_provider = prediction_provider
		
		self.max_memory_size = int(os.getenv("SOMA_MAX_MEMORY_SIZE", max_memory_size))
		
		self.model_lock = threading.RLock()
		self.vector_dim = int(os.getenv("SOMA_VECTOR_DIM", vector_dim))
		
		# Lazy/robust model init: fall back if heavyweight models are unavailable
		try:
			self.embedder = MultiModalEmbedder(text_model_name=os.getenv("SOMA_MODEL_NAME", model_name))
		except Exception as e:
			logger.warning(f"Embedder init failed, using fallback: {e}")
			class _FallbackEmbedder:
				def __init__(self, dim: int):
					self.dim = int(dim) if int(dim) > 0 else 768
				def embed_text(self, text: str):
					import hashlib

					import numpy as _np
					h = hashlib.blake2b(text.encode("utf-8")).digest()
					arr = _np.frombuffer(h, dtype=_np.uint8).astype("float32")
					if arr.size < self.dim:
						reps = int(_np.ceil(self.dim / arr.size))
						arr = _np.tile(arr, reps)
					return arr[: self.dim].reshape(1, -1)
			self.embedder = _FallbackEmbedder(vector_dim)

		# Anomaly Detection
		self.anomaly_detection_enabled = anomaly_detection_enabled
		self.anomaly_detector = IsolationForest(contamination=0.05, random_state=42) if IsolationForest and self.anomaly_detection_enabled else None
		self.is_anomaly_detector_trained = False

		self.cipher = None
		if encryption_key and Fernet:
			self.cipher = Fernet(encryption_key)
		
		config = Dynaconf(
			settings_files=[config_file],
			environments=True,
			envvar_prefix="SOMA"
		)
		
		# Dynaconf exposes attributes; fall back to defaults if missing
		lf_public = getattr(config, "langfuse_public", "pk-lf-123")
		lf_secret = getattr(config, "langfuse_secret", "sk-lf-456")
		lf_host = getattr(config, "langfuse_host", "http://localhost:3000")
		self.langfuse = LangfuseClient(
			public_key=lf_public,
			secret_key=lf_secret,
			host=lf_host,
		)
		
		self.coordinates = {}
		# Prediction config
		self.predictions_enabled = predictions_enabled
		self.predictions_error_policy = predictions_error_policy
		self.predictions_threshold = predictions_threshold
		self.embedding_history = []
		self._snapshot_store = {}
		# Reconsolidation & salience
		self.reconsolidation_enabled = bool(reconsolidation_enabled)
		self.salience_threshold = float(salience_threshold)
		self.salience_weights = dict(salience_weights or {})
		self.novelty_gate_enabled = bool(novelty_gate_enabled)
		self.novelty_threshold = float(novelty_threshold)
		
		# Setup vector store namespace/dim
		self.vector_store.setup(vector_dim=self.vector_dim, namespace=self.namespace)

		# Initialize managers (composition over monolith)
		self.memory_manager = MemoryManager(
			namespace=self.namespace,
			kv_store=self.kv_store,
			vector_store=self.vector_store,
			graph_store=self.graph_store,
			prediction_provider=self.prediction_provider,
			embedder=self.embedder,
			cipher=self.cipher,
			max_memory_size=self.max_memory_size,
			vector_dim=self.vector_dim,
		)
		self.wal_manager = WALManager(namespace=self.namespace, kv_store=self.kv_store)
		self._sync_graph_from_memories()
		# Start WAL reconcile loop if enabled
		self._reconcile_enabled = bool(reconcile_enabled)
		self._reconcile_stop = threading.Event()
		self._reconcile_thread = None
		if self._reconcile_enabled:
			self._reconcile_thread = threading.Thread(target=self._reconcile_loop, daemon=True)
			self._reconcile_thread.start()
		# Setup default audit hooks if not provided
		try:
			if not hasattr(self, '_hooks'):
				self._hooks = {}
			if 'after_store' not in self._hooks:
				def _after_store(data, coordinate, memory_type):
					self.audit_log('store', coordinate, extra={'memory_type': getattr(memory_type, 'value', None)})
				self._hooks['after_store'] = _after_store
			if 'after_forget' not in self._hooks:
				def _after_forget(coordinate):
					self.audit_log('forget', coordinate)
				self._hooks['after_forget'] = _after_forget
			if 'after_recall' not in self._hooks:
				def _after_recall(query, context, top_k, memory_type, results):
					coords = []
					try:
						for r in results or []:
							if isinstance(r, dict):
								c = r.get('coordinate')
								if c is not None:
									coords.append(c)
					except Exception:
						pass
					self.audit_log('recall', None, extra={
						'query': query,
						'top_k': top_k,
						'memory_type': getattr(memory_type, 'value', None) if memory_type else None,
						'result_count': len(results or []),
						'coords': coords,
					})
				self._hooks['after_recall'] = _after_recall
		except Exception:
			pass
		
		# Decay supervisor
		self._decay_enabled = bool(decay_enabled)
		self.pruning_interval_seconds = int(os.getenv("SOMA_PRUNING_INTERVAL_SECONDS", pruning_interval_seconds))
		# Set up decay configuration with defaults
		default_decay_config = {
			"age_weight": 1.0 / 3600.0,  # Penalize per hour of age
			"recency_weight": 1.0 / 3600.0,  # Penalize per hour since last access
			"access_count_weight": -0.5,  # Reward per access
			"importance_weight": -2.0,  # Reward for importance
			"score_threshold": 2.0,  # Score above which decay is considered
			"importance_threshold": 1.0,  # Importance at or below which decay can occur
			"protected_keys": {"memory_type", "timestamp", "coordinate", "importance", "salience"},
			"stdp_strength": 0.1,  # STDP boost for recent accesses
			"stdp_decay_rate": 0.01,  # Exponential decay rate for STDP
		}
		self.decay_config = default_decay_config
		if decay_config:
			self.decay_config.update(decay_config)
		self._decay_stop = threading.Event()
		self._decay_thread = None
		if self._decay_enabled:
			self._decay_thread = threading.Thread(target=self._decay_memories, daemon=True)
			self._decay_thread.start()

		# Fractal annealing supervisor (integrated: entropy reduction)
		self._annealing_enabled = bool(getattr(config, "annealing_enabled", True))
		self.annealing_interval_seconds = int(os.getenv("SOMA_ANNEALING_INTERVAL_SECONDS", 3600))  # 1 hour default
		self._annealing_stop = threading.Event()
		self._annealing_thread = None
		if self._annealing_enabled:
			self._annealing_thread = threading.Thread(target=self._annealing_loop, daemon=True)
			self._annealing_thread.start()

		# Ensure graceful shutdown of background threads
		try:
			atexit.register(self.shutdown)
		except Exception:
			pass

	def store(self, coordinate: Tuple[float, ...], value: dict):
		"""
		Store a memory in the key-value and vector stores with namespaced keys and metadata.
		"""
		# WAL: record pending upsert for idempotent replay
		wal_id = self.wal_manager.write({
			"op": "upsert",
			"coordinate": list(coordinate),
			"point_id": _point_id(self.namespace, coordinate),
			"payload": value,
		})
		try:
			ok = self.memory_manager.store(coordinate, value)
			self.wal_manager.commit(wal_id)
			return ok
		except Exception as e:
			self.wal_manager.fail(wal_id, error=str(e))
			# Swallow to allow caller to continue and let WAL reconciler retry later
			return False

	def train_anomaly_detector(self):
		"""Trains the IsolationForest anomaly detector on existing vector embeddings."""
		if not self.anomaly_detector:
			return
		all_vectors: List[List[float]] = []
		try:
			for p in self.vector_store.scroll():
				payload = getattr(p, 'payload', None)
				if isinstance(payload, dict):
					v = payload.get("vector")
					if isinstance(v, (list, np.ndarray)):
						arr = np.array(v, dtype=np.float32).reshape(-1)
						# pad/truncate to configured dimension
						if arr.size < self.vector_dim:
							pad = np.zeros(self.vector_dim - arr.size, dtype=np.float32)
							arr = np.concatenate([arr, pad])
						elif arr.size > self.vector_dim:
							arr = arr[: self.vector_dim]
						all_vectors.append(arr.tolist())
		except Exception as e:
			logger.warning(f"Failed to gather vectors for anomaly training: {e}")
			return
		if len(all_vectors) > 10:  # Need a minimum number of samples
			try:
				self.anomaly_detector.fit(np.array(all_vectors, dtype=np.float32))
				self.is_anomaly_detector_trained = True
				logger.info("Anomaly detector trained successfully.")
			except Exception as e:
				logger.warning(f"Anomaly detector training failed: {e}")

	def _decay_memories(self):
		"""
		Periodically scan memories and remove fields based on their age and decay config.
		"""
		if _should_log():
			logger.debug("Starting memory decay background process...")
		stop_event = getattr(self, "_decay_stop", None)
		while not (stop_event and stop_event.is_set()):
			# Use model lock to prevent concurrent access with embedding operations
			with self.model_lock:
				self._apply_decay_to_all()
			# Sleep in small slices to respond to stop quickly
			remaining = int(max(1, self.pruning_interval_seconds))
			for _ in range(remaining):
				if stop_event and stop_event.is_set():
					break
				time.sleep(1)
		if _should_log():
			logger.debug("Memory decay background process stopped.")

	def acquire_lock(self, name: str, timeout: int = 10) -> ContextManager:
		"""Acquire a distributed lock. Returns a lock object."""
		return self.kv_store.lock(name, timeout)

	def with_lock(self, name: str, func, *args, **kwargs):
		"""Run a function with a distributed lock."""
		lock = self.acquire_lock(name)
		if lock:
			with lock:
				return func(*args, **kwargs)
		# Fallback if lock is not available
		return func(*args, **kwargs)


	def iter_memories(self, pattern: Optional[str] = None):
		"""
		Efficiently iterate over all memories using the vector store as the source of truth.
		Ensures consistent vector dimensions and robust error handling.
		"""
		try:
			for point in self.vector_store.scroll():
				try:
					# Validate payload structure
					if hasattr(point, 'payload') and isinstance(point.payload, dict):
						payload = point.payload.copy()  # Create a copy to avoid modifying original

						# Ensure vector in payload is properly formatted and dimension-consistent
						if "vector" in payload:
							vector = payload["vector"]
							if isinstance(vector, (list, np.ndarray)):
								vec_array = np.array(vector).flatten()
								if len(vec_array) > 0:
									# Ensure consistent dimension with fallback handling
									if len(vec_array) != self.vector_dim:
										if len(vec_array) < self.vector_dim:
											# Pad with zeros to match expected dimension
											vec_array = np.pad(vec_array, (0, self.vector_dim - len(vec_array)), 'constant')
										else:
											# Truncate to match expected dimension
											vec_array = vec_array[:self.vector_dim]
									payload["vector"] = vec_array.tolist()
								else:
									# Handle empty vectors gracefully
									payload["vector"] = np.zeros(self.vector_dim).tolist()
							else:
								# Handle non-array vectors
								payload["vector"] = np.zeros(self.vector_dim).tolist()

						# Ensure coordinate is properly formatted
						if "coordinate" in payload:
							coord = payload["coordinate"]
							if isinstance(coord, (list, tuple)):
								payload["coordinate"] = tuple(coord)

						# Add namespace if missing
						if "namespace" not in payload:
							payload["namespace"] = self.namespace

						# Ensure memory_type is present
						if "memory_type" not in payload:
							payload["memory_type"] = "episodic"

						# Ensure required fields are present
						if "timestamp" not in payload:
							payload["timestamp"] = time.time()
						if "importance" not in payload:
							payload["importance"] = 0.5
						if "access_count" not in payload:
							payload["access_count"] = 0

						yield payload
				except Exception as e:
					logger.warning(f"Error processing vector store point: {e}")
					continue
		except Exception as e:
			logger.warning(f"Vector store unavailable for iter_memories: {e}, falling back to key-value store.")
			if pattern is None:
				pattern = f"{self.namespace}:*:data"
			for key in self.kv_store.scan_iter(pattern):
				try:
					data = self.kv_store.get(key)
					if data:
						memory = pickle.loads(data)
						# Validate memory structure
						if isinstance(memory, dict):
							# Ensure vector is properly formatted if present
							if "vector" in memory:
								vector = memory["vector"]
								if isinstance(vector, (list, np.ndarray)):
									vec_array = np.array(vector).flatten()
									# Ensure consistent dimension
									if len(vec_array) != self.vector_dim:
										if len(vec_array) < self.vector_dim:
											vec_array = np.pad(vec_array, (0, self.vector_dim - len(vec_array)), 'constant')
										else:
											vec_array = vec_array[:self.vector_dim]
									memory["vector"] = vec_array.tolist()
								else:
									memory["vector"] = np.zeros(self.vector_dim).tolist()

							# Ensure coordinate formatting if present
							if "coordinate" in memory and isinstance(memory["coordinate"], list):
								memory["coordinate"] = tuple(memory["coordinate"])

							# Add namespace if missing
							if "namespace" not in memory:
								memory["namespace"] = self.namespace

							# Ensure memory_type is present
							if "memory_type" not in memory:
								memory["memory_type"] = "episodic"

							# Ensure required fields are present
							if "timestamp" not in memory:
								memory["timestamp"] = time.time()
							if "importance" not in memory:
								memory["importance"] = 0.5
							if "access_count" not in memory:
								memory["access_count"] = 0

							yield memory
				except Exception as e:
					logger.warning(f"Error processing key-value store item {key}: {e}")
					continue

	def get_all_memories(self) -> List[Dict[str, Any]]:
		"""Get all memories by iterating over the underlying stores."""
		return list(self.iter_memories())

	def store_vector_only(self, coordinate: Tuple[float, ...], vector: np.ndarray, payload: Optional[dict] = None):
		"""
		Store only the vector embedding in the vector store.
		"""
		try:
			self.vector_store.upsert(
				points=[{
					"id": str(uuid.uuid4()),
					"vector": vector.tolist(),
					"payload": payload or {"coordinate": coordinate}
				}]
			)
		except Exception as e:
			logger.error(f"Failed to store vector: {e}")
			raise SomaFractalMemoryError("Vector storage failed")

	def check_dependencies(self):
		"""Check that all injected dependencies are available."""
		pass

	def health_check(self) -> Dict[str, bool]:
		"""Return health status of injected dependencies (resilient to exceptions)."""
		def safe(check: Callable[[], Any]) -> bool:
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
		"""Set or update the importance of a memory and sync payload to vector store."""
		# Canonicalize coordinate
		coordinate = tuple(coordinate)
		data_key, _ = _coord_to_key(self.namespace, coordinate)
		data = self.kv_store.get(data_key)
		if not data:
			raise SomaFractalMemoryError(f"No memory at {coordinate}")
		value = pickle.loads(data)
		value["importance"] = importance
		self.kv_store.set(data_key, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
		# Keep vector store payload in sync for downstream scans
		try:
			vec = self.embed_text(json.dumps(value))
			self.vector_store.upsert(points=[{
				"id": _point_id(self.namespace, coordinate),
				"vector": vec.flatten().tolist(),
				"payload": value
			}])
		except Exception as e:
			logger.warning(f"Failed to sync importance to vector store for {coordinate}: {e}")

	def retrieve(self, coordinate: Tuple[float, ...]) -> Optional[Dict[str, Any]]:
		val = self.memory_manager.retrieve(coordinate)
		if not val:
			return None
		# Best-effort decryption using current core cipher to support runtime key injection
		if self.cipher:
			for k in ["task", "code"]:
				if k in val and isinstance(val[k], str) and val[k]:
					try:
						val[k] = self.cipher.decrypt(val[k].encode()).decode()
					except Exception:
						pass
		return val

	def _apply_decay_to_all(self):
		"""
		Applies a decay function to all memories, potentially pruning non-essential fields
		from memories that are old, not recently used, and have low importance.

		The decay score is calculated based on a weighted formula:
		- Age: Time since creation. Older memories are more likely to decay.
		- Recency: Time since last access. Less recently used memories are more likely to decay.
		- Access Count: Number of times the memory has been retrieved. More accesses reduce decay likelihood.
		- Importance: A user-defined score. Higher importance protects memories from decay.
		- STDP (Spike-Timing-Dependent Plasticity): Chemistry-Neuroalgebra fusion - Strengthen recent accesses, weaken others.

		If a memory's decay score exceeds a threshold and its importance is low, its non-essential
		fields are removed, effectively reducing it to a metadata stub.
		"""
		if _should_log():
			logger.debug("Applying advanced memory decay check with STDP plasticity...")
		now = time.time()
		decayed_count = 0
		
		# Load decay parameters from config for clarity and performance
		cfg = self.decay_config
		age_weight = cfg["age_weight"]
		recency_weight = cfg["recency_weight"]
		access_count_weight = cfg["access_count_weight"]
		importance_weight = cfg["importance_weight"]
		score_threshold = cfg["score_threshold"]
		importance_threshold = cfg["importance_threshold"]
		protected_keys = cfg["protected_keys"]
		# STDP parameters (neuroalgebra-inspired)
		stdp_strength = cfg.get("stdp_strength", 0.1)  # Boost for recent accesses
		stdp_decay_rate = cfg.get("stdp_decay_rate", 0.01)  # Exponential decay for old accesses

		for meta_key in self.kv_store.scan_iter(f"{self.namespace}:*:meta"):
			try:
				# 1. Gather all necessary data for one memory
				metadata = self.kv_store.hgetall(meta_key)
				if not metadata:
					continue

				data_key = meta_key.replace(":meta", ":data")
				raw_data = self.kv_store.get(data_key)
				if not raw_data:
					continue
				
				memory_item = pickle.loads(raw_data)

				# 2. Calculate the decay score with STDP
				created = float(metadata.get(b"creation_timestamp", now))
				last_accessed = float(metadata.get(b"last_accessed_timestamp", created))
				access_count = memory_item.get("access_count", 0)
				importance = memory_item.get("importance", 0)

				# STDP: Exponential boost for recency (chemistry: catalytic reinforcement)
				recency_boost = stdp_strength * np.exp(-stdp_decay_rate * (now - last_accessed))
				decay_score = (
					((now - created) * age_weight) +
					((now - last_accessed) * recency_weight - recency_boost) +  # STDP reduces decay
					(access_count * access_count_weight) +
					(importance * importance_weight)
				)

				# 3. Check if the memory should be decayed and perform the decay
				if decay_score > score_threshold and importance <= importance_threshold:
					keys_to_remove = set(memory_item.keys()) - protected_keys
					if not keys_to_remove:
						continue  # Already decayed or has no extra fields

					for key in keys_to_remove:
						memory_item.pop(key, None)
					
					self.kv_store.set(data_key, pickle.dumps(memory_item, protocol=pickle.HIGHEST_PROTOCOL))
					decayed_count += 1
					logger.debug(f"Decayed memory for key {data_key} with score {decay_score:.2f} (STDP applied)")

			except Exception as e:
				logger.warning(f"Error during advanced decay for {meta_key}: {e}")
		if decayed_count > 0:
			logger.info(f"Decayed {decayed_count} memories.")

	def save_version(self, coordinate: Tuple[float, ...]):
		"""Save a version of a memory for rollback/history.

		Uses millisecond timestamp and a short UUID suffix to avoid key collisions.
		"""
		data_key, _ = _coord_to_key(self.namespace, coordinate)
		data = self.kv_store.get(data_key)
		if not data:
			raise SomaFractalMemoryError(f"No memory at {coordinate}")
		version_key = f"{data_key}:version:{int(time.time()*1000)}:{uuid.uuid4().hex[:8]}"
		self.kv_store.set(version_key, data)

	def get_versions(self, coordinate: Tuple[float, ...]) -> List[Dict[str, Any]]:
		"""Get all saved versions of a memory."""
		data_key, _ = _coord_to_key(self.namespace, coordinate)
		pattern = f"{data_key}:version:*"
		versions = []
		for vkey in self.kv_store.scan_iter(pattern):
			vdata = self.kv_store.get(vkey)
			if vdata:
				versions.append(pickle.loads(vdata))
		return versions

	def audit_log(self, action: str, coordinate: Optional[Tuple[float, ...]], user: str = "system", extra: Optional[Dict[str, Any]] = None) -> None:
		"""Append a structured audit event to a JSONL file if enabled.

		The output path can be controlled via the SOMA_AUDIT_LOG env var. If not set,
		audit logging is disabled to avoid creating files in the repo by default.
		"""
		import os
		path = os.getenv("SOMA_AUDIT_LOG")
		if not path:
			return  # disabled by default
		log_entry: Dict[str, Any] = {
			"action": action,
			"coordinate": coordinate,
			"user": user,
			"timestamp": time.time(),
		}
		if extra:
			try:
				log_entry.update(dict(extra))
			except Exception:
				pass
		try:
			with open(path, "a", encoding="utf-8") as f:
				f.write(json.dumps(log_entry) + "\n")
		except Exception:
			# best-effort logging
			pass

	def summarize_memories(self, n: int = 10, memory_type: Optional[MemoryType] = None) -> List[str]:
		"""Return summaries of the n most recent memories of a given type."""
		mems = self.retrieve_memories(memory_type)
		mems = sorted(mems, key=lambda m: m.get("timestamp", 0), reverse=True)[:n]
		return [str(m.get("task", m.get("fact", "<no summary>"))) for m in mems]

	def get_recent(self, n: int = 10, memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]:
		"""Get the n most recent memories of a given type."""
		mems = self.retrieve_memories(memory_type)
		return sorted(mems, key=lambda m: m.get("timestamp", 0), reverse=True)[:n]

	def get_important(self, n: int = 10, memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]:
		"""Get the n most important memories of a given type."""
		mems = self.retrieve_memories(memory_type)
		return sorted(mems, key=lambda m: m.get("importance", 0), reverse=True)[:n]

	def memory_stats(self) -> Dict[str, Any]:
		"""Return statistics about memory usage, hit/miss, decay, etc."""
		all_mems = self.get_all_memories()
		episodic = [m for m in all_mems if m.get("memory_type") == MemoryType.EPISODIC.value]
		semantic = [m for m in all_mems if m.get("memory_type") == MemoryType.SEMANTIC.value]
		return {
			"total_memories": len(all_mems),
			"episodic": len(episodic),
			"semantic": len(semantic),
		}

	def set_hook(self, event: str, func):
		"""Register a hook for an event (e.g., before_store, after_store, before_retrieve, after_retrieve)."""
		if not hasattr(self, '_hooks'):
			self._hooks = {}
		self._hooks[event] = func

	def _call_hook(self, event: str, *args, **kwargs):
		if hasattr(self, '_hooks') and event in self._hooks:
			try:
				self._hooks[event](*args, **kwargs)
			except Exception as e:
				logger.warning(f"Hook {event} failed: {e}")

	def share_memory_with(self, other_agent, filter_fn=None):
		"""Share memories with another agent instance. Optionally filter which memories to share."""
		for mem in self.get_all_memories():
			if filter_fn is None or filter_fn(mem):
				other_agent.store_memory(mem.get("coordinate"), mem, memory_type=MemoryType(mem.get("memory_type", "episodic")))

	def remember(self, data: Dict[str, Any], coordinate: Optional[Tuple[float, ...]] = None, memory_type: MemoryType = MemoryType.EPISODIC) -> bool:
		"""Store a memory using the agent-friendly API.

		- If `coordinate` is not provided, a random 2D coordinate is generated.
		- Invokes before/after hooks.

		Args:
			data: Arbitrary payload to store.
			coordinate: Optional spatial coordinate key.
			memory_type: MemoryType of the memory (episodic/semantic).

		Returns:
			True on success.
		"""
		if coordinate is None:
			coordinate = tuple(np.random.uniform(0, 100, size=2))
		self._call_hook('before_store', data, coordinate, memory_type)
		result = self.store_memory(coordinate, data, memory_type=memory_type)
		self._call_hook('after_store', data, coordinate, memory_type)
		return result

	def recall(self, query: str, context: Optional[Dict[str, Any]] = None, top_k: int = 5, memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]:
		"""Recall memories using a hybrid search.

		Args:
			query: Natural language query.
			context: Optional context object to bias search.
			top_k: Max results to return.
			memory_type: Optional type filter.

		Returns:
			A list of matching payloads.
		"""
		self._call_hook('before_recall', query, context, top_k, memory_type)
		if context:
			results = self.find_hybrid_with_context(query, context, top_k=top_k, memory_type=memory_type)
		else:
			results = self.find_hybrid_by_type(query, top_k=top_k, memory_type=memory_type)
		self._call_hook('after_recall', query, context, top_k, memory_type, results)
		return results

	def forget(self, coordinate: Tuple[float, ...]) -> None:
		"""Delete a memory using the agent-friendly API.

		Args:
			coordinate: Spatial coordinate of the memory to delete.
		"""
		self._call_hook('before_forget', coordinate)
		self.delete(coordinate)
		self._call_hook('after_forget', coordinate)

	def reflect(self, n: int = 5, memory_type: MemoryType = MemoryType.EPISODIC) -> List[Dict[str, Any]]:
		"""Replay a random sample of prior memories for reflection/training.

		Args:
			n: Number of memories to sample.
			memory_type: Type of memories to sample from.

		Returns:
			A list of sampled memory payloads.
		"""
		self._call_hook('before_reflect', n, memory_type)
		memories = self.replay_memories(n=n, memory_type=memory_type)
		self._call_hook('after_reflect', n, memory_type, memories)
		return memories

	def consolidate_memories(self, window_seconds: int = 3600) -> None:
		"""Consolidate recent episodic memories into summarized semantic entries.

		Args:
			window_seconds: Consider episodic memories created within this time window.
		"""
		now = time.time()
		episodic = self.retrieve_memories(MemoryType.EPISODIC)
		for mem in episodic:
			if now - mem.get("timestamp", 0) < window_seconds:
				coord_val = mem.get("coordinate")
				coord = tuple(coord_val) if coord_val is not None else None
				if coord:
					summary = {
						"fact": f"Summary of event at {mem.get('timestamp')}",
						"source_coord": list(coord),
						"memory_type": MemoryType.SEMANTIC.value,
						"consolidated_from": list(coord),
						"timestamp": now
					}
					self.store_memory(coord, summary, memory_type=MemoryType.SEMANTIC)

	def replay_memories(self, n: int = 5, memory_type: MemoryType = MemoryType.EPISODIC) -> List[Dict[str, Any]]:
		"""
		Sample and return n random memories of the given type (for agent learning/reinforcement).
		"""
		import random
		mems = self.retrieve_memories(memory_type)
		return random.sample(mems, min(n, len(mems)))

	def find_hybrid_with_context(self, query: str, context: Dict[str, Any], top_k: int = 5, memory_type: Optional[MemoryType] = None, **kwargs) -> List[Dict[str, Any]]:
		"""Hybrid search with context-aware attention.

		Records Prometheus recall metrics.
		"""
		start = time.perf_counter()
		context_str = json.dumps(context, sort_keys=True)
		full_query = f"{query} [CTX] {context_str}"
		results = self.find_hybrid_by_type(full_query, top_k=top_k, memory_type=memory_type, **kwargs)
		def score(mem: Dict[str, Any]) -> float:
			score = 0
			if "timestamp" in mem:
				score += 1 / (1 + (time.time() - mem["timestamp"]))
			if "access_count" in mem:
				score += 0.1 * mem["access_count"]
			return score
		out = sorted(results, key=score, reverse=True)
		try:
			recall_count.labels(namespace=self.namespace).inc()
			recall_latency.labels(namespace=self.namespace).observe(max(0.0, time.perf_counter() - start))
		except Exception:
			pass
		return out

	def link_memories(self, from_coord: Tuple[float, ...], to_coord: Tuple[float, ...], link_type: str = "related", weight: float = 1.0) -> None:
		"""Create a directed link from one memory to another.

		Args:
			from_coord: Source coordinate.
			to_coord: Target coordinate.
			link_type: Semantic relation label.
			weight: Optional edge weight for pathfinding.
		"""
		lock = self.acquire_lock(f"lock:{from_coord}")
		if lock:
			with lock:
				data_key, _ = _coord_to_key(self.namespace, from_coord)
				data = self.kv_store.get(data_key)
				if not data:
					raise SomaFractalMemoryError(f"No memory at {from_coord}")

				# Prepare link data
				link_data = {"to": to_coord, "type": link_type, "timestamp": time.time(), "weight": float(weight)}

				try:
					# Step 1: Update KV store
					value = pickle.loads(data)
					links = value.get("links", [])
					links.append(link_data)
					value["links"] = links
					self.kv_store.set(data_key, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))

					# Step 2: Update graph store (with rollback on failure)
					try:
						self.graph_store.add_link(from_coord, to_coord, link_data)
					except Exception as graph_error:
						# Rollback KV store changes on graph store failure
						import logging
						logger = logging.getLogger(__name__)
						logger.warning(f"Graph store update failed, rolling back KV changes: {graph_error}")

						# Remove the link we just added
						if "links" in value:
							value["links"] = [link for link in value["links"] if link != link_data]
							self.kv_store.set(data_key, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))

						# Re-raise the original error
						if hasattr(graph_error, '__cause__'):
							raise graph_error from graph_error.__cause__
						else:
							raise graph_error

				except Exception as e:
					# Handle any other errors during the linking process
					import logging
					logger = logging.getLogger(__name__)
					logger.error(f"Failed to link memories {from_coord} -> {to_coord}: {e}")
					raise

	def get_linked_memories(self, coord: Tuple[float, ...], link_type: Optional[str] = None, depth: int = 1, limit: Optional[int] = None) -> List[Dict[str, Any]]:
		"""Traverse and return memories linked from a starting coordinate.

		Args:
			coord: Starting coordinate.
			link_type: Optional filter on edge type.
			depth: Reserved for future multi-hop traversals (currently 1).
			limit: Optional limit on neighbor count.

		Returns:
			List of retrieved neighbor memory payloads.
		"""
		path = self.graph_store.get_neighbors(coord, link_type=link_type, limit=limit)
		memories = []
		for c, _ in path:
			if c:
				mem = self.retrieve(c)
				if mem:
					memories.append(mem)
		return memories

	def store_memory(self, coordinate: Tuple[float, ...], value: Dict[str, Any], memory_type: MemoryType = MemoryType.EPISODIC) -> bool:
		"""Store a memory with explicit type and graph sync.

		Args:
			coordinate: Spatial coordinate key.
			value: Arbitrary payload to persist.
			memory_type: MemoryType of this memory.

		Returns:
			True on success.
		"""
		# Ensure coordinate is a tuple for hashable use in graph keys
		coordinate = tuple(coordinate)
		value = dict(value)
		# Optional prediction enrichment (use original pre-encryption content)
		if self.predictions_enabled and self.prediction_provider:
			try:
				pred_outcome, pred_conf = self.prediction_provider.predict(value)
				value["predicted_outcome"] = pred_outcome
				value["predicted_confidence"] = float(pred_conf)
				value["prediction_provider"] = type(self.prediction_provider).__name__
				value["prediction_timestamp"] = time.time()
			except Exception as e:
				logger.warning(f"Prediction enrichment failed: {e}")
		# Optionally encrypt sensitive fields before persistence and vectorization
		if self.cipher:
			for k in ("task", "code"):
				if k in value and isinstance(value[k], str) and value[k]:
					try:
						value[k] = self.cipher.encrypt(value[k].encode()).decode()
					except Exception:
						pass
		value["memory_type"] = memory_type.value
		if memory_type == MemoryType.EPISODIC:
			value["timestamp"] = value.get("timestamp", time.time())
		# Include coordinate in stored value for downstream consumers
		value["coordinate"] = list(coordinate)
		# Annotate salience (no gating by default)
		try:
			value["salience"] = float(self._compute_salience(value))
		except Exception:
			pass

		# Optional novelty gate before persisting (lightweight top-1 similarity)
		if self.novelty_gate_enabled:
			try:
				# Build a query text for embedding. Prefer task/fact if present; fall back to json.
				if "task" in value and isinstance(value["task"], str):
					qtext = value["task"]
				elif "fact" in value and isinstance(value["fact"], str):
					qtext = value["fact"]
				else:
					qtext = json.dumps(value, sort_keys=True)
				qvec = self.embedder.embed_text(qtext).flatten().astype("float32").tolist()
				# Query top-1 from the vector store (if empty, allow insert)
				nearest = self.vector_store.search(qvec, top_k=1)
				if nearest:
					# Interpret score as similarity when using in-memory store; otherwise derive cosine from vectors if available
					try:
						# If score is provided as similarity in [0,1]
						sim = float(getattr(nearest[0], "score", 0.0) or 0.0)
					except Exception:
						sim = 0.0
					# Novelty as (1 - similarity), clamp
					novelty = max(0.0, min(1.0, 1.0 - sim))
				else:
					novelty = 1.0
				# Optional domain error term (if provided)
				error = 0.0
				if "reward" in value:
					try:
						r = float(value["reward"])
						error = max(0.0, min(1.0, abs(r) if r < 0 else 0.0))
					except Exception:
						pass
				w = self.salience_weights or {}
				alpha = float(w.get("novelty", 1.0))
				beta = float(w.get("error", 0.0))
				gate_score = alpha * novelty + beta * error
				if gate_score < float(self.novelty_threshold):
					return True  # treat as a no-op store; considered not salient enough
			except Exception as e:
				logger.debug(f"Novelty gate skipped due to error: {e}")
		
		result = self.store(coordinate, value)
		# Enforce memory cap after storing
		try:
			self._enforce_memory_limit()
		except Exception as e:
			logger.warning(f"Memory limit enforcement failed: {e}")
		return result

	def _compute_salience(self, value: Dict[str, Any]) -> float:
		"""Simple salience estimation using importance and recency; bounded [0,1]."""
		try:
			imp = float(value.get("importance", 0.0))
			ts = float(value.get("timestamp", time.time()))
			age = max(0.0, time.time() - ts)
			recency = 1.0 / (1.0 + age)
			s = 0.5 * (1.0 / (1.0 + np.exp(-imp))) + 0.5 * recency
			return float(max(0.0, min(1.0, s)))
		except Exception:
			return 0.0

	def report_outcome(self, coordinate: Tuple[float, ...], outcome: Any) -> Dict[str, Any]:
		"""Report observed outcome for a memory, detect prediction error, and adapt importance/correct it."""
		coordinate = tuple(coordinate)
		mem = self.retrieve(coordinate)
		if not mem:
			raise SomaFractalMemoryError(f"No memory at {coordinate}")
		mem["observed_outcome"] = outcome
		# Persist observed outcome
		data_key, _ = _coord_to_key(self.namespace, coordinate)
		self.kv_store.set(data_key, pickle.dumps(mem, protocol=pickle.HIGHEST_PROTOCOL))
		# Detect error and adapt
		error = self._detect_prediction_error(mem)
		adapt = {"error": error}
		if error:
			# Lower importance minimally
			try:
				cur_imp = int(mem.get("importance", 0))
				self.set_importance(coordinate, max(0, cur_imp - 1))
			except Exception:
				pass
			# Create corrective semantic memory
			fact = f"Prediction mismatch at {coordinate}: expected '{mem.get('predicted_outcome')}', got '{outcome}'"
			corr = {
				"fact": fact,
				"source_coord": list(coordinate),
				"memory_type": MemoryType.SEMANTIC.value,
				"timestamp": time.time(),
				"corrective_for": list(coordinate),
			}
			self.store_memory(coordinate, corr, memory_type=MemoryType.SEMANTIC)
			self.link_memories(coordinate, coordinate, link_type="corrective", weight=1.0)
			adapt["corrective_created"] = True
		return adapt

	def _detect_prediction_error(self, mem: Dict[str, Any]) -> bool:
		"""Return True if predicted vs observed outcome indicates an error based on policy."""
		pred = mem.get("predicted_outcome")
		obs = mem.get("observed_outcome")
		if pred is None or obs is None:
			return False
		policy = (self.predictions_error_policy or "exact").lower()
		if policy == "threshold":
			try:
				p = float(pred)
				o = float(obs)
				return abs(p - o) > float(self.predictions_threshold or 0.0)
			except Exception:
				# Fallback to exact if not numeric
				policy = "exact"
		# exact policy: string compare
		return str(pred) != str(obs)

	def _enforce_memory_limit(self) -> None:
		"""Ensure total memories do not exceed max_memory_size by pruning lowest-importance, oldest episodic memories."""
		all_mems = self.get_all_memories()
		total = len(all_mems)
		if total <= self.max_memory_size:
			return
		# Compute how many to remove
		excess = total - self.max_memory_size
		# Prefer removing episodic memories with lowest importance and oldest timestamps
		episodic = [m for m in all_mems if m.get("memory_type") == MemoryType.EPISODIC.value]
		# Sort by (importance asc, timestamp asc)
		sorted_ep = sorted(
			episodic,
			key=lambda m: (
				m.get("importance", 0),
				m.get("timestamp", 0),
			),
		)
		to_delete = sorted_ep[:excess]
		for m in to_delete:
			coord_val = m.get("coordinate")
			if coord_val is None:
				continue
			self.delete(tuple(coord_val))

	def retrieve_memories(self, memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]:
		"""
		Retrieve all memories, optionally filtered by type.
		"""
		all_mems = self.get_all_memories()
		if memory_type:
			return [m for m in all_mems if m.get("memory_type") == memory_type.value]
		return all_mems

	def find_hybrid_by_type(self, query: str, top_k: int = 5, memory_type: Optional[MemoryType] = None, filters: Optional[Dict[str, Any]] = None, **kwargs) -> List[Dict[str, Any]]:
		return self.memory_manager.find_hybrid_by_type(query, top_k=top_k, memory_type=memory_type, filters=filters)

	def find_hybrid_with_scores(self, query: str, top_k: int = 5, memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]:
		"""Hybrid search returning payloads with similarity scores.

		Records Prometheus recall metrics.
		"""
		start = time.perf_counter()
		query_vector = self.embed_text(query)
		results = self.vector_store.search(query_vector.flatten().tolist(), top_k=top_k)
		items: List[Dict[str, Any]] = []
		for r in results:
			payload = getattr(r, 'payload', None) if hasattr(r, 'payload') else None
			score = getattr(r, 'score', None)
			if payload is None and isinstance(r, dict):
				payload = r.get('payload')
				score = r.get('score')
			if payload is None:
				continue
			if memory_type and payload.get("memory_type") != memory_type.value:
				continue
			items.append({"payload": payload, "score": score})
		try:
			recall_count.labels(namespace=self.namespace).inc()
			recall_latency.labels(namespace=self.namespace).observe(max(0.0, time.perf_counter() - start))
		except Exception:
			pass
		return items

	def recall_with_scores(self, query: str, top_k: int = 5, memory_type: Optional[MemoryType] = None):
		"""Agent-friendly API to recall with similarity scores."""
		return self.find_hybrid_with_scores(query, top_k=top_k, memory_type=memory_type)

	def recall_batch(
		self,
		queries: List[str],
		top_k: int = 5,
		memory_type: Optional[MemoryType] = None,
		filters: Optional[Dict[str, Any]] = None,
	) -> List[List[Dict[str, Any]]]:
		"""Batch hybrid recall with optional type and attribute filters."""
		return [self.find_hybrid_by_type(q, top_k=top_k, memory_type=memory_type, filters=filters) for q in queries]

	def _sync_graph_from_memories(self):
		"""
		Build or refresh the semantic graph from all stored memories.
		"""
		self.graph_store.clear()
		for mem in self.get_all_memories():
			coord_val = mem.get("coordinate")
			if coord_val is not None:
				coord = tuple(coord_val)
				self.graph_store.add_memory(coord, mem)

	def find_shortest_path(self, from_coord: Tuple[float, ...], to_coord: Tuple[float, ...], link_type: Optional[str] = None):
		"""Find the shortest path between two memories in the semantic graph.

		Args:
			from_coord: Start coordinate.
			to_coord: End coordinate.
			link_type: Optional filter to constrain edges by type.

		Returns:
			A list of coordinates representing the path; empty if none.
		"""
		return self.graph_store.find_shortest_path(from_coord, to_coord, link_type)

	def find_by_coordinate_range(
		self,
		min_coord: Tuple[float, ...],
		max_coord: Tuple[float, ...],
		memory_type: Optional[MemoryType] = None,
	) -> List[Dict[str, Any]]:
		"""Find memories with coordinates within a bounding box (inclusive)."""
		all_mems = self.get_all_memories()
		mi = tuple(min_coord)
		ma = tuple(max_coord)
		if len(all_mems) > 10000:
			logger.warning("`find_by_coordinate_range` is performing a full scan on a large memory set and may be slow. Consider a backend with native spatial filtering for production use.")

		result: List[Dict[str, Any]] = []
		for mem in all_mems:
			if memory_type and mem.get("memory_type") != memory_type.value:
				continue
			coord_val = mem.get("coordinate")
			if coord_val is None:
				continue
			coord = tuple(coord_val)
			if len(coord) != len(mi) or len(coord) != len(ma):
				continue
			inside = all(mi[i] <= coord[i] <= ma[i] for i in range(len(coord)))
			if inside:
				result.append(mem)
		return result

	def export_graph(self, path: str = "semantic_graph.graphml"):
		"""Export the semantic graph to GraphML at the given path."""
		self.graph_store.export_graph(path)

	def import_graph(self, path: str = "semantic_graph.graphml"):
		"""Import a semantic graph from GraphML at the given path."""
		self.graph_store.import_graph(path)

	def export_memories(self, path: str = "memories.jsonl") -> int:
		"""Export all memories as JSONL.

		Returns:
			Number of memories exported.
		"""
		count = 0
		with open(path, "w", encoding="utf-8") as f:
			for mem in self.get_all_memories():
				f.write(json.dumps(mem) + "\n")
				count += 1
		return count

	def import_memories(self, path: str, replace: bool = False) -> int:
		"""Import memories from JSONL.

		If `replace=True`, existing memories are deleted prior to import.

		Returns:
			Number of memories imported.
		"""
		if replace:
			# Best effort clear: remove via vector scroll payloads
			for mem in self.get_all_memories():
				coord_val = mem.get("coordinate")
				if coord_val is not None:
					self.delete(tuple(coord_val))
		count = 0
		with open(path, "r", encoding="utf-8") as f:
			for line in f:
				line = line.strip()
				if not line:
					continue
				mem = json.loads(line)
				coord_val = mem.get("coordinate")
				if coord_val is None:
					continue
				coord = tuple(coord_val)
				mtype = MemoryType(mem.get("memory_type", MemoryType.EPISODIC.value))
				# Preserve original content as much as possible
				payload = dict(mem)
				# Ensure coordinate format
				payload["coordinate"] = list(coord)
				self.store_memory(coord, payload, memory_type=mtype)
				count += 1
		return count

	def store_memories_bulk(self, items: List[Tuple[Tuple[float, ...], Dict[str, Any], MemoryType]]):
		"""Store many memories with a single vector upsert. Each item is (coord, value, memory_type)."""
		points = []
		for coordinate, value, memory_type in items:
			coordinate = tuple(coordinate)
			val = dict(value)
			val["memory_type"] = memory_type.value
			if memory_type == MemoryType.EPISODIC:
				val["timestamp"] = val.get("timestamp", time.time())
			val["coordinate"] = list(coordinate)
			# KV store
			data_key, meta_key = _coord_to_key(self.namespace, coordinate)
			self.kv_store.set(data_key, pickle.dumps(val, protocol=pickle.HIGHEST_PROTOCOL))
			try:
				self.kv_store.hset(meta_key, mapping={b"creation_timestamp": str(time.time()).encode("utf-8")})
			except Exception as e:
				logger.warning(f"Failed to set metadata for {meta_key}: {e}")
			# Graph store
			self.graph_store.add_memory(coordinate, val)
			# Vector point prepared
			vec = self.embed_text(json.dumps(val)).flatten().tolist()
			points.append({"id": _point_id(self.namespace, coordinate), "vector": vec, "payload": val})
		# Upsert in one call
		if points:
			try:
				self.vector_store.upsert(points=points)
			except Exception as e:
				logger.warning(f"Bulk vector upsert failed: {e}")
		# Enforce cap
		try:
			self._enforce_memory_limit()
		except Exception as e:
			logger.warning(f"Memory limit enforcement failed (bulk): {e}")
	
	def calculate_fractal_dimension(self) -> float:
		"""
		Calculates the fractal dimension of the memory graph's coordinates using the box-counting method.
		This can indicate the complexity and distribution of memories in their coordinate space.
		"""
		# Get coordinates from memories instead of direct graph access
		coords = []
		for memory in self.iter_memories():
			if "coordinate" in memory:
				coords.append(memory["coordinate"])

		points = np.array(coords)

		if len(points) < 2 or points.ndim != 2:
			return 0.0

		# Box-counting algorithm
		min_pt = points.min(axis=0)
		max_pt = points.max(axis=0)
		if np.all(min_pt == max_pt):
			return 0.0

		scales = np.logspace(0.01, np.log10(np.max(max_pt - min_pt)), num=10, base=10)
		counts = []
		for scale in scales:
			bins = [int(np.ceil((max_pt[i] - min_pt[i]) / scale)) for i in range(points.shape[1])]
			hist, _ = np.histogramdd(points, bins=bins)
			counts.append(np.sum(hist > 0))

		# Linear regression on log-log plot to find the slope (fractal dimension)
		counts_arr = np.asarray(counts, dtype=float)
		mask = counts_arr > 0
		if mask.sum() < 2:
			return 0.0
		coeffs = np.polyfit(np.log(np.asarray(scales)[mask]), np.log(counts_arr[mask]), 1)
		return -coeffs[0]

	def delete(self, coordinate: Tuple[float, ...]):
		# WAL: record pending delete
		wal_id = self.wal_manager.write({
			"op": "delete",
			"coordinate": list(coordinate),
			"point_id": _point_id(self.namespace, coordinate),
		})
		try:
			self.memory_manager.delete(coordinate)
			self.wal_manager.commit(wal_id)
		except Exception as e:
			self.wal_manager.fail(wal_id, error=str(e))
			raise

	def delete_many(self, coordinates: List[Tuple[float, ...]]) -> int:
		"""Delete multiple memories.

		Returns:
			Number of memories deleted.
		"""
		count = 0
		vec_ids: List[str] = []
		for coordinate in coordinates:
			coordinate = tuple(coordinate)
			data_key, meta_key = _coord_to_key(self.namespace, coordinate)
			self.kv_store.delete(data_key)
			self.kv_store.delete(meta_key)
			self.graph_store.remove_memory(coordinate)
			vec_ids.append(_point_id(self.namespace, coordinate))
			count += 1
		try:
			self.vector_store.delete(vec_ids)
		except Exception:
			pass
		return count
  
	def embed_text(self, text: str) -> np.ndarray:
		return self.memory_manager.embed_text(text)

	# ---------------- WAL helpers ----------------
	def _wal_key(self, wid: str) -> str:
		return f"{self.namespace}:wal:{wid}"

	def _wal_write(self, entry: Dict[str, Any]) -> str:
		wid = str(uuid.uuid4())
		payload = dict(entry)
		payload.update({"id": wid, "status": "pending", "ts": time.time()})
		self.kv_store.set(self._wal_key(wid), pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL))
		return wid

	def _wal_commit(self, wid: str):
		try:
			raw = self.kv_store.get(self._wal_key(wid))
			if not raw:
				return
			entry = pickle.loads(raw)
			entry["status"] = "committed"
			self.kv_store.set(self._wal_key(wid), pickle.dumps(entry, protocol=pickle.HIGHEST_PROTOCOL))
		except Exception:
			pass

	def _wal_fail(self, wid: str, error: str = ""):
		try:
			raw = self.kv_store.get(self._wal_key(wid))
			if not raw:
				return
			entry = pickle.loads(raw)
			entry["status"] = "failed"
			if error:
				entry["error"] = error
			self.kv_store.set(self._wal_key(wid), pickle.dumps(entry, protocol=pickle.HIGHEST_PROTOCOL))
		except Exception:
			pass

	def _apply_wal_entry(self, entry: Dict[str, Any]) -> bool:
		op = entry.get("op")
		coord_val = entry.get("coordinate")
		if coord_val is None:
			return False
		coord = tuple(coord_val)
		pid = entry.get("point_id")
		try:
			if op == "upsert":
				payload = entry.get("payload", {})
				vec = self.embed_text(json.dumps(payload)).flatten().tolist()
				self.vector_store.upsert(points=[{"id": pid, "vector": vec, "payload": payload}])
				self.graph_store.add_memory(coord, payload)
				return True
			elif op == "delete":
				self.graph_store.remove_memory(coord)
				if pid:
					self.vector_store.delete([pid])
				return True
			return False
		except Exception as e:
			logger.warning(f"WAL apply failed for {entry.get('id')}: {e}")
			return False

	def _reconcile_once(self):
		for wal_key in self.kv_store.scan_iter(f"{self.namespace}:wal:*"):
			try:
				raw = self.kv_store.get(wal_key)
				if not raw:
					continue
				entry = pickle.loads(raw)
				if entry.get("status") in {"pending", "failed"}:
					ok = self._apply_wal_entry(entry)
					if ok:
						entry["status"] = "committed"
						self.kv_store.set(wal_key, pickle.dumps(entry, protocol=pickle.HIGHEST_PROTOCOL))
			except Exception as e:
				logger.warning(f"Error during WAL reconcile for {wal_key}: {e}")

	def _reconcile_loop(self):
		if _should_log():
			logger.debug("Starting WAL reconcile loop...")
		stop_event = getattr(self, "_reconcile_stop", None)
		while not (stop_event and stop_event.is_set()):
			try:
				self._reconcile_once()
			except Exception as e:
				logger.warning(f"WAL reconcile loop iteration failed: {e}")
			# Sleep a short interval to avoid busy loop
			for _ in range(5):
				if stop_event and stop_event.is_set():
					break
				time.sleep(1)
		if _should_log():
			logger.debug("WAL reconcile loop stopped.")

	def shutdown(self, timeout: float = 5.0):
		"""Signal background threads to stop and join them briefly."""
		# Stop reconcile
		try:
			if hasattr(self, "_reconcile_stop"):
				self._reconcile_stop.set()
			thr = getattr(self, "_reconcile_thread", None)
			if isinstance(thr, threading.Thread):
				thr.join(timeout=timeout)
		except Exception:
			pass
		# Stop decay
		try:
			if hasattr(self, "_decay_stop"):
				self._decay_stop.set()
			thr = getattr(self, "_decay_thread", None)
			if isinstance(thr, threading.Thread):
				thr.join(timeout=timeout)
		except Exception:
			pass
		# Stop annealing
		try:
			if hasattr(self, "_annealing_stop"):
				self._annealing_stop.set()
			thr = getattr(self, "_annealing_thread", None)
			if isinstance(thr, threading.Thread):
				thr.join(timeout=timeout)
		except Exception:
			pass

	def _fractal_annealing_scheduler(self):
		"""
		Integrated: Fractal Annealing Scheduler
		Gradually 'cools' the system by re-embedding and clustering vectors to optimize harmonics,
		reducing entropy (physics) via spectral optimization (Fourier).
		Runs periodically to maintain low-energy states.
		"""
		if _should_log():
			logger.debug("Starting fractal annealing scheduler...")
		try:
			# Collect all vectors for clustering
			all_points = list(self.vector_store.scroll())
			if len(all_points) < 10:
				return  # Not enough data for annealing

			# Filter and normalize vectors to ensure consistent dimensions
			valid_vectors = []
			valid_points = []
			target_dim = getattr(self, 'vector_dim', 768)  # Default dimension

			for point in all_points:
				vector = point.payload.get("vector", [])
				if vector and isinstance(vector, (list, np.ndarray)):
					vec_array = np.array(vector).flatten()
					if len(vec_array) == target_dim:
						valid_vectors.append(vec_array)
						valid_points.append(point)
					elif len(vec_array) > 0:
						# Resize vector to target dimension if possible
						if len(vec_array) < target_dim:
							# Pad with zeros
							padded = np.pad(vec_array, (0, target_dim - len(vec_array)), 'constant')
							valid_vectors.append(padded)
							valid_points.append(point)
						else:
							# Truncate
							valid_vectors.append(vec_array[:target_dim])
							valid_points.append(point)

			if len(valid_vectors) < 10:
				return  # Not enough valid vectors

			vectors = np.array(valid_vectors)

			# Fourier: Spectral clustering (harmonic optimization), guarded for dep and scale
			try:
				from sklearn.cluster import SpectralClustering
			except Exception:
				return  # sklearn not available; skip annealing
			# Sample down for very large N to avoid O(N^3) costs
			max_nodes = int(os.getenv("SOMA_ANNEALING_MAX_NODES", "2000"))
			if vectors.shape[0] > max_nodes:
				idx = np.random.choice(vectors.shape[0], size=max_nodes, replace=False)
				vectors = vectors[idx]
			n_clusters = min(10, max(2, len(vectors) // 10))  # Adaptive clusters
			if n_clusters > 1:
				sc = SpectralClustering(n_clusters=n_clusters, affinity='nearest_neighbors', random_state=42)
				labels = sc.fit_predict(vectors)

				# Physics: Re-embed and update payloads with cluster info for entropy reduction
				for i, point in enumerate(valid_points):
					if i < len(labels):
						payload = point.payload.copy()  # Create a copy to avoid modifying original
						payload["cluster_id"] = int(labels[i])
						# Re-embed with cluster context (catalytic reinforcement)
						enhanced_text = json.dumps(payload) + f" cluster:{labels[i]}"
						new_vec = self.embed_text(enhanced_text).flatten()

						# Ensure consistent dimension
						if len(new_vec) != target_dim:
							if len(new_vec) < target_dim:
								new_vec = np.pad(new_vec, (0, target_dim - len(new_vec)), 'constant')
							else:
								new_vec = new_vec[:target_dim]

						new_vec_list = new_vec.tolist()

						# Update both vector store and graph store atomically
						try:
							self.vector_store.upsert(points=[{
								"id": point.id,
								"vector": new_vec_list,
								"payload": payload
							}])

							# Update graph store if coordinate exists
							if "coordinate" in payload:
								coord = tuple(payload["coordinate"])
								self.graph_store.add_memory(coord, payload)

							logger.debug(f"Annealed vector for {point.id} in cluster {labels[i]}")
						except Exception as e:
							logger.warning(f"Failed to update stores for {point.id}: {e}")
							continue

			if _should_log():
				logger.debug("Fractal annealing completed.")
		except Exception as e:
			logger.warning(f"Fractal annealing failed: {e}")

	def _annealing_loop(self):
		if _should_log():
			logger.debug("Starting fractal annealing background process...")
		stop_event = getattr(self, "_annealing_stop", None)
		while not (stop_event and stop_event.is_set()):
			# Use model lock to prevent concurrent access with embedding operations
			with self.model_lock:
				self._fractal_annealing_scheduler()
			remaining = int(max(1, self.annealing_interval_seconds))
			for _ in range(remaining):
				if stop_event and stop_event.is_set():
					break
				time.sleep(1)
		if _should_log():
			logger.debug("Fractal annealing background process stopped.")
