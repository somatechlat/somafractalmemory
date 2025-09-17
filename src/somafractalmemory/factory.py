from enum import Enum
from typing import Any, Dict, Optional

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.implementations.storage import (
    InMemoryKeyValueStore,
    InMemoryVectorStore,
    QdrantVectorStore,
    RedisKeyValueStore,
)

try:
    from somafractalmemory.implementations.fractal_inmemory import (
        FractalInMemoryVectorStore,  # type: ignore
    )
except Exception:
    FractalInMemoryVectorStore = None  # type: ignore
from somafractalmemory.implementations.graph import NetworkXGraphStore
from somafractalmemory.implementations.prediction import (
    ExternalPredictionProvider,
    NoPredictionProvider,
    OllamaPredictionProvider,
)

try:
    from somafractalmemory.implementations.graph_neo4j import (
        Neo4jGraphStore,  # type: ignore
    )
except Exception:
    Neo4jGraphStore = None  # type: ignore


class MemoryMode(Enum):
    ON_DEMAND = "on_demand"
    LOCAL_AGENT = "local_agent"
    ENTERPRISE = "enterprise"


def create_memory_system(
    mode: MemoryMode, namespace: str, config: Optional[Dict[str, Any]] = None
) -> SomaFractalMemoryEnterprise:
    """
    Factory function to create a SomaFractalMemory instance based on the specified mode.
    """
    config = config or {}
    kv_store = None
    vector_store = None
    graph_store = None
    prediction_provider = None

    if mode == MemoryMode.ON_DEMAND:
        # Use RedisKeyValueStore with fakeredis for lightweight, dependency-free local testing
        kv_store = RedisKeyValueStore(testing=True)
        graph_backend = (config.get("graph", {}) or {}).get("backend", "networkx")
        if graph_backend == "neo4j" and Neo4jGraphStore:
            neo = (config.get("graph", {}) or {}).get("neo4j", {})
            graph_store = Neo4jGraphStore(uri=neo.get("uri", "bolt://localhost:7687"), user=neo.get("user", "neo4j"), password=neo.get("password", "neo4j"))
        else:
            graph_store = NetworkXGraphStore()
        prediction_provider = NoPredictionProvider()

    elif mode == MemoryMode.LOCAL_AGENT:
        redis_config = config.get("redis", {})
        kv_store = RedisKeyValueStore(**redis_config)
        graph_backend = (config.get("graph", {}) or {}).get("backend", "networkx")
        if graph_backend == "neo4j" and Neo4jGraphStore:
            neo = (config.get("graph", {}) or {}).get("neo4j", {})
            graph_store = Neo4jGraphStore(uri=neo.get("uri", "bolt://localhost:7687"), user=neo.get("user", "neo4j"), password=neo.get("password", "neo4j"))
        else:
            graph_store = NetworkXGraphStore()
        prediction_provider = OllamaPredictionProvider()

    elif mode == MemoryMode.ENTERPRISE:
        redis_config = config.get("redis", {})
        kv_store = RedisKeyValueStore(**redis_config)
        graph_backend = (config.get("graph", {}) or {}).get("backend", "networkx")
        if graph_backend == "neo4j" and Neo4jGraphStore:
            neo = (config.get("graph", {}) or {}).get("neo4j", {})
            graph_store = Neo4jGraphStore(uri=neo.get("uri", "bolt://localhost:7687"), user=neo.get("user", "neo4j"), password=neo.get("password", "neo4j"))
        else:
            graph_store = NetworkXGraphStore()
        ext_pred_cfg = config.get("external_prediction")
        if isinstance(ext_pred_cfg, dict) and ext_pred_cfg.get("api_key") and ext_pred_cfg.get("endpoint"):
            prediction_provider = ExternalPredictionProvider(
                api_key=ext_pred_cfg["api_key"], endpoint=ext_pred_cfg["endpoint"]
            )
        else:
            prediction_provider = OllamaPredictionProvider()
    else:
        raise ValueError(f"Unsupported memory mode: {mode}")

    # --- Vector Store Setup (Centralized) ---
    vec_cfg = config.get("vector", {})
    vector_backend = vec_cfg.get("backend", "").lower()

    # Determine default backend if not specified
    if not vector_backend:
        if mode == MemoryMode.ON_DEMAND:
            vector_backend = "inmemory"
        else:  # LOCAL_AGENT and ENTERPRISE default to qdrant
            vector_backend = "qdrant"

    if vector_backend == "qdrant":
        qdrant_config = config.get("qdrant", {})
        # Mode-specific defaults for qdrant
        if mode == MemoryMode.ON_DEMAND and not qdrant_config:
            qdrant_config = {"location": ":memory:"}
        elif mode == MemoryMode.LOCAL_AGENT and not qdrant_config:
            qdrant_config = {"path": f"./{namespace}_qdrant"}
        elif mode == MemoryMode.ENTERPRISE:
            if "url" in qdrant_config or "host" in qdrant_config or "location" in qdrant_config:
                qdrant_config.pop("path", None)
        vector_store = QdrantVectorStore(collection_name=namespace, **qdrant_config)
    # Legacy "aperture" backend removed in favor of unified FaissApertureStore
    elif vector_backend == "faiss_aperture":
        from .implementations.faiss_aperture import FaissApertureStore

        mem_cfg = config.get("memory_enterprise", {})
        vector_dim = mem_cfg.get("vector_dim", 768)
        aperture_config = config.get("faiss_aperture", {})
        profile = aperture_config.get("profile", "fast")
        # Pass the entire config dict to allow for GPU and parameter overrides
        vector_store = FaissApertureStore(vector_dim=vector_dim, profile=profile, config=aperture_config)
    elif vector_backend in {"inmemory", "fractal", "fractal_inmemory"}:
        # Feature flag: env SFM_FRACTAL_BACKEND=1 or config vector.fractal_enabled
        import os as _os
        fractal_enabled = False
        if vector_backend in {"fractal", "fractal_inmemory"}:
            fractal_enabled = True
        else:
            fractal_enabled = bool(vec_cfg.get("fractal_enabled", False) or _os.environ.get("SFM_FRACTAL_BACKEND") == "1")
        if fractal_enabled and FractalInMemoryVectorStore is not None:
            fcfg = vec_cfg.get("fractal", {}) if isinstance(vec_cfg.get("fractal"), dict) else {}
            vector_store = FractalInMemoryVectorStore(
                centroids=fcfg.get("centroids"),
                beam_width=int(fcfg.get("beam_width", 4)),
                max_candidates=int(fcfg.get("max_candidates", 1024)),
                rebuild_enabled=bool(fcfg.get("rebuild_enabled", True)),
                rebuild_size_delta=float(fcfg.get("rebuild_size_delta", 0.1)),
                rebuild_interval_seconds=int(fcfg.get("rebuild_interval_seconds", 600)),
            )
        else:
            vector_store = InMemoryVectorStore()
    else:
        raise ValueError(f"Unsupported vector backend: {vector_backend}")

    # --- Final Assembly ---
    mem_cfg = config.get("memory_enterprise", {}) if isinstance(config, dict) else {}
    return SomaFractalMemoryEnterprise(
        namespace=namespace,
        kv_store=kv_store,
        vector_store=vector_store,
        graph_store=graph_store,
        prediction_provider=prediction_provider,
        vector_dim=mem_cfg.get("vector_dim", 768),
        encryption_key=mem_cfg.get("encryption_key"),
        max_memory_size=mem_cfg.get("max_memory_size", 100000),
        predictions_enabled=mem_cfg.get("predictions", {}).get("enabled", False),
        predictions_error_policy=mem_cfg.get("predictions", {}).get("error_policy", "exact"),
        predictions_threshold=float(mem_cfg.get("predictions", {}).get("threshold", 0.0)),
        decay_enabled=mem_cfg.get("decay", {}).get("enabled", True),
        reconsolidation_enabled=mem_cfg.get("reconsolidation", {}).get("enabled", False),
        salience_threshold=float((mem_cfg.get("salience", {}) or {}).get("threshold", 0.0)),
        salience_weights=(mem_cfg.get("salience", {}) or {}).get("weights", {}),
    # Novelty gate (optional): salience.novelty_gate and salience.novelty_threshold
    novelty_gate_enabled=bool((mem_cfg.get("salience", {}) or {}).get("novelty_gate", False)),
    novelty_threshold=float((mem_cfg.get("salience", {}) or {}).get("novelty_threshold", 0.0)),
        pruning_interval_seconds=mem_cfg.get("pruning_interval_seconds", 600),
        decay_config=mem_cfg.get("decay", {}).get("config"),
        anomaly_detection_enabled=mem_cfg.get("anomaly_detection", {}).get("enabled", False),
    )
