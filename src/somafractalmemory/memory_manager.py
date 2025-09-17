# memory_manager.py - Handles core memory operations like store, recall, delete

import hashlib
import json
import logging
import pickle
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from prometheus_client import REGISTRY, Counter, Histogram

from .interfaces.graph import IGraphStore
from .interfaces.prediction import IPredictionProvider
from .interfaces.storage import IKeyValueStore, IVectorStore


# Custom exception
class SomaFractalMemoryError(Exception):
    """Custom exception for SomaFractalMemory errors."""
    pass

# Memory Types
class MemoryType(Enum):
    EPISODIC = "episodic"  # Event-based, time-stamped
    SEMANTIC = "semantic"  # Fact-based, general knowledge

# Setup logging
logger = logging.getLogger(__name__)

# Unregister existing metrics to avoid duplication
for metric_name in ['soma_memory_store_total', 'soma_memory_store_latency_seconds', 'soma_memory_recall_total', 'soma_memory_recall_latency_seconds']:
    try:
        REGISTRY.unregister(REGISTRY._names_to_collectors[metric_name])
    except KeyError:
        pass

# Prometheus metrics (assuming prometheus_client is available)
store_count = Counter("soma_memory_store_total", "Total store operations", ["namespace"])
store_latency = Histogram("soma_memory_store_latency_seconds", "Store operation latency", ["namespace"])
recall_count = Counter("soma_memory_recall_total", "Total recall operations", ["namespace"])
recall_latency = Histogram("soma_memory_recall_latency_seconds", "Recall operation latency", ["namespace"])

def _coord_to_key(namespace: str, coord: Tuple[float, ...]) -> Tuple[str, str]:
    coord_str = repr(coord)
    data_key = f"{namespace}:{coord_str}:data"
    meta_key = f"{namespace}:{coord_str}:meta"
    return data_key, meta_key

def _point_id(namespace: str, coord: Tuple[float, ...]) -> str:
    """Stable point id for vector store based on namespace+coordinate."""
    try:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{namespace}:{repr(coord)}"))
    except Exception:
        return "pt-" + hashlib.blake2b(f"{namespace}:{repr(coord)}".encode("utf-8")).hexdigest()

class MemoryManager:
    def __init__(self, namespace: str, kv_store: IKeyValueStore, vector_store: IVectorStore, graph_store: IGraphStore, prediction_provider: IPredictionProvider, embedder, cipher=None, max_memory_size=100000, vector_dim: int = 768):
        self.namespace = namespace
        self.kv_store = kv_store
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.prediction_provider = prediction_provider
        self.embedder = embedder
        self.cipher = cipher
        self.max_memory_size = max_memory_size
        self.coordinates = {}
        self.vector_dim = int(vector_dim) if int(vector_dim) > 0 else 768

    def embed_text(self, text: str) -> np.ndarray:
        # Energy-aware caching: Check KV store for pre-computed embedding
        text_hash = hashlib.blake2b(text.encode("utf-8")).hexdigest()
        cache_key = f"{self.namespace}:embed_cache:{text_hash}"
        cached_vec = self.kv_store.get(cache_key)
        if cached_vec:
            try:
                vec = np.array(pickle.loads(cached_vec))
                if vec.shape == (1, self.vector_dim):
                    return vec
            except Exception:
                pass  # Cache miss or corruption

        # Get raw embedding (may be any length depending on model)
        vec = None
        try:
            vec = self.embedder.embed_text(text)
        except Exception:
            vec = None
        if vec is None:
            # deterministic fallback
            h = hashlib.blake2b(text.encode("utf-8")).digest()
            arr = np.frombuffer(h, dtype=np.uint8).astype("float32")
            if arr.size < self.vector_dim:
                reps = int(np.ceil(self.vector_dim / arr.size))
                arr = np.tile(arr, reps)
            vec = arr[: self.vector_dim].reshape(1, -1)
        
        # Fourier-Physics: Spectral Denoising (wavelet-based if available)
        try:
            import pywt

            # Apply wavelet denoising to reduce noise (harmonic artifacts)
            coeffs = pywt.wavedec(vec.flatten(), 'db1', level=2)
            # Threshold detail coefficients (soft thresholding for energy conservation)
            threshold = np.sqrt(2 * np.log(len(vec.flatten()))) * np.std(coeffs[-1])
            coeffs[1:] = [pywt.threshold(c, threshold, mode='soft') for c in coeffs[1:]]
            denoised = pywt.waverec(coeffs, 'db1')[:self.vector_dim]
            vec = denoised.reshape(1, -1)
        except ImportError:
            # No PyWavelets, skip denoising
            pass
        except Exception:
            # Denoising failed, use original
            pass
        
        # Enforce configured vector dimension
        if vec.ndim == 1:
            vec = vec.reshape(1, -1)
        cur = vec.shape[1]
        if cur < self.vector_dim:
            pad = np.zeros((vec.shape[0], self.vector_dim - cur), dtype=vec.dtype)
            vec = np.concatenate([vec, pad], axis=1)
        elif cur > self.vector_dim:
            vec = vec[:, : self.vector_dim]
        
        # Cache the result for energy conservation (TTL via metadata if supported)
        try:
            self.kv_store.set(cache_key, pickle.dumps(vec.tolist(), protocol=pickle.HIGHEST_PROTOCOL))
        except Exception:
            pass  # Caching optional
        
        return vec.astype("float32")

    def store(self, coordinate: Tuple[float, ...], value: dict):
        start = time.perf_counter()
        data_key, meta_key = _coord_to_key(self.namespace, coordinate)
        self.kv_store.set(data_key, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
        try:
            self.kv_store.hset(meta_key, mapping={
                b"creation_timestamp": str(time.time()).encode("utf-8")
            })
        except Exception as e:
            logger.warning(f"Failed to set metadata for {meta_key}: {e}")

        try:
            vector = self.embed_text(json.dumps(value))
            self.vector_store.upsert(
                points=[{
                    "id": _point_id(self.namespace, coordinate),
                    "vector": vector.flatten().tolist(),
                    "payload": value
                }]
            )
            # Make graph store operation more robust
            try:
                self.graph_store.add_memory(coordinate, value)
            except Exception as graph_error:
                logger.warning(f"Graph store operation failed (non-critical): {graph_error}")
                # Don't fail the entire operation for graph store issues
        except Exception as e:
            logger.error(f"Vector store operation failed: {e}")
            # Try to store in graph store as fallback if vector store fails
            try:
                self.graph_store.add_memory(coordinate, value)
                logger.info("Stored in graph store as fallback")
            except Exception as fallback_error:
                logger.error(f"Both vector and graph store failed: {fallback_error}")
                raise SomaFractalMemoryError("Storage failed") from e
        finally:
            try:
                store_count.labels(namespace=self.namespace).inc()
                store_latency.labels(namespace=self.namespace).observe(max(0.0, time.perf_counter() - start))
            except Exception:
                pass
        return True

    def retrieve(self, coordinate: Tuple[float, ...]) -> Optional[Dict[str, Any]]:
        data_key, _ = _coord_to_key(self.namespace, coordinate)
        data = self.kv_store.get(data_key)
        if not data:
            return None
        value = pickle.loads(data)
        if self.cipher:
            for k in ["task", "code"]:
                if k in value and value[k]:
                    try:
                        value[k] = self.cipher.decrypt(value[k].encode()).decode()
                    except Exception as e:
                        logger.warning(f"Decryption failed for key '{k}' in {coordinate}: {e}")
        return value

    def delete(self, coordinate: Tuple[float, ...]):
        data_key, meta_key = _coord_to_key(self.namespace, coordinate)
        self.kv_store.delete(data_key)
        self.kv_store.delete(meta_key)
        self.graph_store.remove_memory(coordinate)
        try:
            self.vector_store.delete([_point_id(self.namespace, coordinate)])
        except Exception as e:
            logger.warning(f"Vector delete failed during delete({coordinate}): {e}")

    def get_all_memories(self) -> List[Dict[str, Any]]:
        memories = []
        try:
            for point in self.vector_store.scroll():
                memories.append(point.payload)
        except Exception as e:
            logger.warning(f"Vector store unavailable for get_all_memories: {e}, falling back to key-value store.")
            pattern = f"{self.namespace}:*:data"
            for key in self.kv_store.scan_iter(pattern):
                data = self.kv_store.get(key)
                if data:
                    memories.append(pickle.loads(data))
        return memories

    def find_hybrid_by_type(self, query: str, top_k: int = 5, memory_type: Optional[MemoryType] = None, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        start = time.perf_counter()
        query_vector = self.embed_text(query)
        
        # Ensure query vector has consistent dimensions
        query_vector_flat = query_vector.flatten().tolist()
        
        try:
            results = self.vector_store.search(query_vector_flat, top_k=top_k)
        except Exception as e:
            logger.warning(f"Vector store search failed: {e}, falling back to empty results")
            return []
        
        payloads = []
        distances = []
        
        for r in results:
            try:
                payload = r.payload
                distance = getattr(r, 'score', 0.0)
                payloads.append(payload)
                distances.append(distance)
            except Exception as e:
                logger.warning(f"Error processing search result: {e}")
                continue
        
        if memory_type:
            filtered = [(p, d) for p, d in zip(payloads, distances) if p.get("memory_type") == memory_type.value]
            payloads, distances = zip(*filtered) if filtered else ([], [])
        if filters:
            def ok(p: Dict[str, Any]) -> bool:
                for k, v in filters.items():
                    if p.get(k) != v:
                        return False
                return True
            filtered = [(p, d) for p, d in zip(payloads, distances) if ok(p)]
            payloads, distances = zip(*filtered) if filtered else ([], [])
        
        # Quantum-Inspired: Probabilistic amplitudes (inverse distance as probability)
        if distances:
            try:
                inv_distances = np.array([1.0 / (d + 1e-6) for d in distances])  # Avoid division by zero
                probabilities = inv_distances / np.sum(inv_distances)  # Softmax-like normalization
                for i, p in enumerate(payloads):
                    p["retrieval_probability"] = float(probabilities[i])
            except Exception as e:
                logger.warning(f"Error calculating probabilities: {e}")
        
        try:
            recall_count.labels(namespace=self.namespace).inc()
            recall_latency.labels(namespace=self.namespace).observe(max(0.0, time.perf_counter() - start))
        except Exception:
            pass
        return list(payloads)

    # Add other methods like store_memory, recall, etc., delegating to store/retrieve/find_hybrid

    def store_memory(self, coordinate: Tuple[float, ...], value: Dict[str, Any], memory_type: MemoryType = MemoryType.EPISODIC) -> bool:
        coordinate = tuple(coordinate)
        value = dict(value)
        # Prediction enrichment
        if self.prediction_provider:
            try:
                pred_outcome, pred_conf = self.prediction_provider.predict(value)
                value["predicted_outcome"] = pred_outcome
                value["predicted_confidence"] = float(pred_conf)
                value["prediction_provider"] = type(self.prediction_provider).__name__
                value["prediction_timestamp"] = time.time()
            except Exception as e:
                logger.warning(f"Prediction enrichment failed: {e}")
        # Encryption
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
        value["coordinate"] = list(coordinate)
        result = self.store(coordinate, value)
        self.graph_store.add_memory(coordinate, value)
        return result

    def recall(self, query: str, top_k: int = 5, memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]:
        return self.find_hybrid_by_type(query, top_k=top_k, memory_type=memory_type)

    # Add more methods as needed
