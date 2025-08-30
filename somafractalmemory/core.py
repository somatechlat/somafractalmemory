import numpy as np
import pickle
import threading
import time
import logging
import os
import hashlib
import ast
import json
from typing import Dict, Any, List, Tuple, Optional, ContextManager, Callable
import uuid
from enum import Enum

# Optional heavy deps with safe fallbacks
try:
    from transformers import AutoTokenizer, AutoModel  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    AutoTokenizer = None  # type: ignore
    AutoModel = None  # type: ignore

try:
    from langfuse import Langfuse  # type: ignore
except Exception:  # pragma: no cover
    class Langfuse:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

try:
    from sklearn.ensemble import IsolationForest  # type: ignore
except Exception:  # pragma: no cover
    IsolationForest = None  # type: ignore

try:
    from cryptography.fernet import Fernet  # type: ignore
except Exception:  # pragma: no cover
    Fernet = None  # type: ignore

try:
    from prometheus_client import Counter, Histogram  # type: ignore
except Exception:  # pragma: no cover
    class _Noop:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
        def observe(self, *args, **kwargs):
            return None
        def inc(self, *args, **kwargs):
            return None
    Counter = _Noop  # type: ignore
    Histogram = _Noop  # type: ignore

try:
    import structlog  # type: ignore
    _logger = structlog.get_logger()
except Exception:  # pragma: no cover
    structlog = None  # type: ignore
    logging.basicConfig(level=logging.INFO)
    _logger = logging.getLogger("somafractalmemory")

try:
    from dynaconf import Dynaconf  # type: ignore
except Exception:  # pragma: no cover
    class Dynaconf:  # Minimal stand-in
        def __init__(self, settings_files=None, environments=None, envvar_prefix=None):
            self._data = {}
        def __getattr__(self, item):
            return None

from .interfaces.storage import IKeyValueStore, IVectorStore
from .interfaces.graph import IGraphStore
from .interfaces.prediction import IPredictionProvider

# --- Multi-modal Embedding Support ---
class MultiModalEmbedder:
	"""Stub for multi-modal embedding (text, image, audio). Extend as needed."""
	def __init__(self, text_model_name="microsoft/codebert-base", image_model_name="openai/clip-vit-base-patch16", audio_model_name="openai/whisper-base"):
		self.text_tokenizer = AutoTokenizer.from_pretrained(text_model_name)
		self.text_model = AutoModel.from_pretrained(text_model_name, use_safetensors=True)
		# Image embedding (CLIP)
		try:
			from transformers import CLIPProcessor, CLIPModel
			self.image_processor = CLIPProcessor.from_pretrained(image_model_name)
			self.image_model = CLIPModel.from_pretrained(image_model_name, use_safetensors=True)
		except Exception:
			self.image_processor = None
			self.image_model = None
		# Audio embedding (Whisper)
		try:
			from transformers import WhisperProcessor, WhisperModel
			self.audio_processor = WhisperProcessor.from_pretrained(audio_model_name)
			self.audio_model = WhisperModel.from_pretrained(audio_model_name, use_safetensors=True)
		except Exception:
			self.audio_processor = None
			self.audio_model = None

	def embed_text(self, text: str) -> np.ndarray:
		inputs = self.text_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
		outputs = self.text_model(**inputs)
		emb = outputs.last_hidden_state.mean(dim=1).detach().cpu().numpy().astype("float32")
		return emb

	def embed_image(self, image_bytes: bytes) -> np.ndarray:
		if self.image_processor is None or self.image_model is None:
			raise NotImplementedError("Image embedding model not loaded.")
		from PIL import Image
		import io
		image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
		inputs = self.image_processor(images=image, return_tensors="pt")
		outputs = self.image_model(**inputs)
		emb = outputs.pooler_output.detach().cpu().numpy().astype("float32")
		return emb

	def embed_audio(self, audio_bytes: bytes) -> np.ndarray:
		if self.audio_processor is None or self.audio_model is None:
			raise NotImplementedError("Audio embedding model not loaded.")
		import torchaudio
		import io
		waveform, sample_rate = torchaudio.load(io.BytesIO(audio_bytes))
		inputs = self.audio_processor(waveform, sampling_rate=sample_rate, return_tensors="pt")
		outputs = self.audio_model(**inputs)
		emb = outputs.last_hidden_state.mean(dim=1).detach().cpu().numpy().astype("float32")
		return emb

# --- Memory Types ---
class MemoryType(Enum):
	EPISODIC = "episodic"  # Event-based, time-stamped
	SEMANTIC = "semantic"  # Fact-based, general knowledge

# Custom exception for the package
class SomaFractalMemoryError(Exception):
	"""Custom exception for SomaFractalMemory errors."""
	pass

# Setup logging
logger = _logger

# Prometheus metrics
store_count = Counter("soma_memory_store_total", "Total store operations", ["namespace"])  # type: ignore
store_latency = Histogram("soma_memory_store_latency_seconds", "Store operation latency", ["namespace"])  # type: ignore

recall_count = Counter("soma_memory_recall_total", "Total recall operations", ["namespace"])  # type: ignore
recall_latency = Histogram("soma_memory_recall_latency_seconds", "Recall operation latency", ["namespace"])  # type: ignore
def _coord_to_key(namespace: str, coord: Tuple[float, ...]) -> Tuple[str, str]:
	"""
	Generates data and metadata keys from a namespace and coordinate.

	Args:
		namespace: The memory namespace.
		coord: A tuple of floats representing the spatial coordinate.

	Returns:
		A tuple containing the data key and the metadata key for Redis.
	"""
	coord_str = repr(coord)
	data_key = f"{namespace}:{coord_str}:data"
	meta_key = f"{namespace}:{coord_str}:meta"
	return data_key, meta_key

def _point_id(namespace: str, coord: Tuple[float, ...]) -> str:
	"""Stable point id for vector store based on namespace+coordinate."""
	try:
		return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{namespace}:{repr(coord)}"))
	except Exception:
		# Fallback deterministic hash string
		return "pt-" + hashlib.blake2b(f"{namespace}:{repr(coord)}".encode("utf-8")).hexdigest()

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
		pruning_interval_seconds: int = 600,
		decay_thresholds_seconds: Optional[List[int]] = None,
		decayable_keys_by_level: Optional[List[List[str]]] = None,
		predictions_enabled: bool = False,
		predictions_error_policy: str = "exact",
		predictions_threshold: float = 0.0,
		decay_enabled: bool = True,
		reconcile_enabled: bool = True,
		reconsolidation_enabled: bool = False,
		salience_threshold: float = 0.0,
		salience_weights: Optional[Dict[str, float]] = None,
	):
		self.namespace = os.getenv("SOMA_NAMESPACE", namespace)
		self.kv_store = kv_store
		self.vector_store = vector_store
		self.graph_store = graph_store
		self.prediction_provider = prediction_provider
		
		self.max_memory_size = int(os.getenv("SOMA_MAX_MEMORY_SIZE", max_memory_size))
		self.pruning_interval_seconds = int(os.getenv("SOMA_PRUNING_INTERVAL_SECONDS", pruning_interval_seconds))
		self.decay_thresholds_seconds = decay_thresholds_seconds or []
		self.decayable_keys_by_level = decayable_keys_by_level or []
		
		self.model_lock = threading.RLock()
		self.vector_dim = int(os.getenv("SOMA_VECTOR_DIM", vector_dim))
		
		config = Dynaconf(
			settings_files=[config_file],
			environments=True,
			envvar_prefix="SOMA"
		)
		
		# Lazy/robust model init: fall back if heavyweight models are unavailable
		try:
			if AutoTokenizer is None or AutoModel is None:
				raise RuntimeError("transformers unavailable")
			self.tokenizer = AutoTokenizer.from_pretrained(os.getenv("SOMA_MODEL_NAME", model_name))
			self.model = AutoModel.from_pretrained(os.getenv("SOMA_MODEL_NAME", model_name), use_safetensors=True)
		except Exception as e:
			logger.warning(f"Transformer model init failed, falling back to hash-based embeddings: {e}")
			self.tokenizer = None
			self.model = None
		self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42) if IsolationForest else None
		self.cipher = None
		if encryption_key and Fernet:
			self.cipher = Fernet(encryption_key)
		
		# Dynaconf exposes attributes; fall back to defaults if missing
		lf_public = getattr(config, "langfuse_public", "pk-lf-123")
		lf_secret = getattr(config, "langfuse_secret", "sk-lf-456")
		lf_host = getattr(config, "langfuse_host", "http://localhost:3000")
		self.langfuse = Langfuse(
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
		
		self.vector_store.setup(vector_dim=self.vector_dim, namespace=self.namespace)
		self._sync_graph_from_memories()
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
		self._decay_stop = threading.Event()
		if self._decay_enabled:
			threading.Thread(target=self._decay_memories, daemon=True).start()

		# WAL reconciler supervisor
		self._reconcile_enabled = bool(reconcile_enabled)
		self._reconcile_stop = threading.Event()
		if self._reconcile_enabled:
			threading.Thread(target=self._reconcile_loop, daemon=True).start()
		logger.info(f"SomaFractalMemoryEnterprise initialized: namespace={self.namespace}")

	def store(self, coordinate: Tuple[float, ...], value: dict):
		"""
		Store a memory in the key-value and vector stores with namespaced keys and metadata.
		"""
		start = time.perf_counter()
		data_key, meta_key = _coord_to_key(self.namespace, coordinate)
		self.kv_store.set(data_key, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
		try:
			self.kv_store.hset(meta_key, mapping={
				b"creation_timestamp": str(time.time()).encode("utf-8")
			})
		except Exception as e:
			logger.warning(f"Failed to set metadata for {meta_key}: {e}")

		# WAL: record pending upsert for vector+graph idempotent replay
		wal_id = self._wal_write({
			"op": "upsert",
			"coordinate": list(coordinate),
			"point_id": _point_id(self.namespace, coordinate),
			"payload": value,
		})
		try:
			vector = self.embed_text(json.dumps(value))
			self.vector_store.upsert(
				points=[{
					"id": _point_id(self.namespace, coordinate),
					"vector": vector.flatten().tolist(),
					"payload": value
				}]
			)
			# Graph add
			self.graph_store.add_memory(coordinate, value)
			self._wal_commit(wal_id)
		except Exception as e:
			logger.error(f"Vector/Graph apply failed: {e}")
			self._wal_fail(wal_id, error=str(e))
		finally:
			try:
				store_count.labels(namespace=self.namespace).inc()
				store_latency.labels(namespace=self.namespace).observe(max(0.0, time.perf_counter() - start))
			except Exception:
				pass
		return True

	def _decay_memories(self):
		"""
		Periodically scan memories and remove fields based on their age and decay config.
		"""
		logger.info("Starting memory decay background process...")
		stop_event = getattr(self, "_decay_stop", None)
		while not (stop_event.is_set() if stop_event else False):
			self.run_decay_once()
			# Sleep in small slices to respond to stop quickly
			remaining = int(max(1, self.pruning_interval_seconds))
			for _ in range(remaining):
				if stop_event and stop_event.is_set():
					break
				time.sleep(1)

	def start_decay(self):
		"""Start the decay background worker if not running."""
		if getattr(self, "_decay_enabled", False) and getattr(self, "_decay_stop", threading.Event()) and not self._decay_stop.is_set():
			return
		self._decay_enabled = True
		self._decay_stop = threading.Event()
		threading.Thread(target=self._decay_memories, daemon=True).start()

	def stop_decay(self):
		"""Stop the decay background worker if running."""
		self._decay_enabled = False
		if getattr(self, "_decay_stop", None):
			self._decay_stop.set()

	def run_decay_once(self):
		"""Run a single pass of field-level decay (deterministic for tests)."""
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
				memory_item = pickle.loads(raw_data)
				for i, threshold in enumerate(self.decay_thresholds_seconds):
					if age > threshold:
						keys_to_remove = set(self.decayable_keys_by_level[i])
						for key in keys_to_remove:
							memory_item.pop(key, None)
				self.kv_store.set(data_key, pickle.dumps(memory_item, protocol=pickle.HIGHEST_PROTOCOL))
			except Exception as e:
				logger.warning(f"Error during decay for {meta_key}: {e}")

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
		"""
		try:
			for point in self.vector_store.scroll():
				yield point.payload
		except Exception as e:
			logger.warning(f"Vector store unavailable for iter_memories: {e}, falling back to key-value store.")
			if pattern is None:
				pattern = f"{self.namespace}:*:data"
			for key in self.kv_store.scan_iter(pattern):
				data = self.kv_store.get(key)
				if data:
					yield pickle.loads(data)

	def get_all_memories(self) -> List[Dict[str, Any]]:
		"""Get all memories."""
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
		"""Retrieve and return a memory payload by coordinate, incrementing access count."""
		lock = self.acquire_lock(f"lock:{coordinate}")
		if lock:
			with lock:
				data_key, _ = _coord_to_key(self.namespace, coordinate)
				data = self.kv_store.get(data_key)
				if not data:
					return None
				
				_, meta_key = _coord_to_key(self.namespace, coordinate)
				self.kv_store.hset(meta_key, mapping={b"last_accessed_timestamp": str(time.time()).encode('utf-8')})
				
				value = pickle.loads(data)
				value["access_count"] = value.get("access_count", 0) + 1
				self.kv_store.set(data_key, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
				
				if self.cipher:
					for k in ["task", "code"]:
						if k in value and value[k]:
							try:
								value[k] = self.cipher.decrypt(value[k].encode()).decode()
							except Exception as e:
								logger.warning(f"Decryption failed for key '{k}' in {coordinate}: {e}")
				return value
		return None

	def _apply_decay_to_all(self):
		"""
		Advanced decay: use weighted formula of age, recency, access_count, and importance.
		"""
		logger.info("Applying advanced memory decay check...")
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
				if not raw_data: continue
				memory_item = pickle.loads(raw_data)
				access_count = memory_item.get("access_count", 0)
				importance = memory_item.get("importance", 0)
				
				decay_score = (age/3600) + (recency/3600) - (0.5*access_count) - (2*importance)
				if decay_score > 2 and importance <= 1:
					keys_to_remove = set(memory_item.keys()) - {"memory_type", "timestamp", "coordinate", "importance"}
					for key in keys_to_remove:
						memory_item.pop(key, None)
					self.kv_store.set(data_key, pickle.dumps(memory_item, protocol=pickle.HIGHEST_PROTOCOL))
					decayed_count += 1
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
		"""Append a structured audit event to audit_log.jsonl.

		Args:
			action: Event action string (e.g., 'store', 'recall', 'forget').
			coordinate: Optional coordinate for point events.
			user: Actor, default 'system'.
			extra: Optional additional fields to include.
		"""
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
		with open("audit_log.jsonl", "a", encoding="utf-8") as f:
			f.write(json.dumps(log_entry) + "\n")

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
				value = pickle.loads(data)
				links = value.get("links", [])
				link_data = {"to": to_coord, "type": link_type, "timestamp": time.time(), "weight": float(weight)}
				links.append(link_data)
				value["links"] = links
				self.kv_store.set(data_key, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
				self.graph_store.add_link(from_coord, to_coord, link_data)

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
		
		result = self.store(coordinate, value)
		self.graph_store.add_memory(coordinate, value)
		# Enforce memory cap after storing
		try:
			self._enforce_memory_limit()
		except Exception as e:
			logger.warning(f"Memory limit enforcement failed: {e}")
		return result

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
		"""Hybrid search with optional type and exact-attribute filters.

		Records Prometheus recall metrics.
		"""
		start = time.perf_counter()
		query_vector = self.embed_text(query)
		results = self.vector_store.search(query_vector.flatten().tolist(), top_k=top_k)
		
		payloads = [r.payload for r in results]
		if memory_type:
			payloads = [p for p in payloads if p.get("memory_type") == memory_type.value]
		if filters:
			def ok(p: Dict[str, Any]) -> bool:
				for k, v in filters.items():
					if p.get(k) != v:
						return False
				return True
			payloads = [p for p in payloads if ok(p)]
		try:
			recall_count.labels(namespace=self.namespace).inc()
			recall_latency.labels(namespace=self.namespace).observe(max(0.0, time.perf_counter() - start))
		except Exception:
			pass
		return payloads

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
		mi = tuple(min_coord)
		ma = tuple(max_coord)
		result: List[Dict[str, Any]] = []
		for mem in self.get_all_memories():
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
	
	def delete(self, coordinate: Tuple[float, ...]):
		"""
		Deletes a memory and its associated metadata.
		"""
		data_key, meta_key = _coord_to_key(self.namespace, coordinate)
		# WAL: record pending delete for vector+graph replay
		wal_id = self._wal_write({
			"op": "delete",
			"coordinate": list(coordinate),
			"point_id": _point_id(self.namespace, coordinate),
		})
		self.kv_store.delete(data_key)
		self.kv_store.delete(meta_key)
		self.graph_store.remove_memory(coordinate)
		# Also remove from vector store: try both legacy id and new stable id
		try:
			self.vector_store.delete([
				str(coordinate),
				_point_id(self.namespace, coordinate)
			])
		except Exception as e:
			logger.warning(f"Vector delete failed during delete({coordinate}): {e}")
		# Commit WAL
		self._wal_commit(wal_id)

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
			vec_ids.extend([str(coordinate), _point_id(self.namespace, coordinate)])
			count += 1
		try:
			self.vector_store.delete(vec_ids)
		except Exception:
			pass
		return count
  
	def embed_text(self, text: str) -> np.ndarray:
		"""
		Embeds a text string into a vector. Falls back to a stable hash-based embedding if transformer models are unavailable.
		"""
		def _fallback_hash() -> np.ndarray:
			# Deterministic pseudo-embedding based on text hash
			h = hashlib.blake2b(text.encode("utf-8")).digest()
			arr = np.frombuffer(h, dtype=np.uint8).astype("float32")
			if arr.size < self.vector_dim:
				reps = int(np.ceil(self.vector_dim / arr.size))
				arr = np.tile(arr, reps)
			return arr[:self.vector_dim].reshape(1, -1)
		# If models aren't loaded, use fallback immediately
		if self.tokenizer is None or self.model is None:
			return _fallback_hash()

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
				self.vector_store.delete([str(coord), pid])
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
		logger.info("Starting WAL reconcile background process...")
		stop_event = getattr(self, "_reconcile_stop", None)
		while not (stop_event.is_set() if stop_event else False):
			self._reconcile_once()
			# basic interval
			for _ in range(5):
				if stop_event and stop_event.is_set():
					break
				time.sleep(1)
