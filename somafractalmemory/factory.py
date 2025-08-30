from enum import Enum
from typing import Dict, Any, Optional

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.implementations.storage import (
    RedisKeyValueStore,
    QdrantVectorStore,
)
from somafractalmemory.implementations.prediction import (
    NoPredictionProvider,
    OllamaPredictionProvider,
    ExternalPredictionProvider,
)
from somafractalmemory.implementations.graph import NetworkXGraphStore
try:
    from somafractalmemory.implementations.graph_neo4j import Neo4jGraphStore  # type: ignore
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
        # Pure in-memory setup for quick tests and demos
        kv_store = RedisKeyValueStore(testing=True)
        qdrant_config = {"location": ":memory:"}
        vector_store = QdrantVectorStore(collection_name=namespace, **qdrant_config)
        graph_backend = (config.get("graph", {}) or {}).get("backend", "networkx")
        if graph_backend == "neo4j" and Neo4jGraphStore:
            neo = (config.get("graph", {}) or {}).get("neo4j", {})
            graph_store = Neo4jGraphStore(uri=neo.get("uri", "bolt://localhost:7687"), user=neo.get("user", "neo4j"), password=neo.get("password", "neo4j"))
        else:
            graph_store = NetworkXGraphStore()
        prediction_provider = NoPredictionProvider()

    elif mode == MemoryMode.LOCAL_AGENT:
        redis_config = config.get("redis", {})
        qdrant_config = config.get("qdrant", {"path": f"./{namespace}_qdrant"})
        kv_store = RedisKeyValueStore(**redis_config)
        vector_store = QdrantVectorStore(collection_name=namespace, **qdrant_config)
        graph_backend = (config.get("graph", {}) or {}).get("backend", "networkx")
        if graph_backend == "neo4j" and Neo4jGraphStore:
            neo = (config.get("graph", {}) or {}).get("neo4j", {})
            graph_store = Neo4jGraphStore(uri=neo.get("uri", "bolt://localhost:7687"), user=neo.get("user", "neo4j"), password=neo.get("password", "neo4j"))
        else:
            graph_store = NetworkXGraphStore()
        prediction_provider = OllamaPredictionProvider()

    elif mode == MemoryMode.ENTERPRISE:
        # For enterprise, we expect explicit remote connection details
        redis_config = config.get("redis", {})
        qdrant_config = config.get("qdrant", {})

        # Ensure path is not passed if other connection details are present
        if "url" in qdrant_config or "host" in qdrant_config or "location" in qdrant_config:
            qdrant_config.pop("path", None)

        kv_store = RedisKeyValueStore(**redis_config)
        vector_store = QdrantVectorStore(collection_name=namespace, **qdrant_config)
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

    # Thread memory-related settings from config into the core constructor
    mem_cfg = config.get("memory_enterprise", {}) if isinstance(config, dict) else {}
    return SomaFractalMemoryEnterprise(
        namespace=namespace,
        kv_store=kv_store,
        vector_store=vector_store,
        graph_store=graph_store,
        prediction_provider=prediction_provider,
        vector_dim=mem_cfg.get("vector_dim", 768),
        encryption_key=mem_cfg.get("encryption_key"),
        pruning_interval_seconds=mem_cfg.get("pruning_interval_seconds", 600),
        decay_thresholds_seconds=mem_cfg.get("decay_thresholds_seconds"),
        decayable_keys_by_level=mem_cfg.get("decayable_keys_by_level"),
        max_memory_size=mem_cfg.get("max_memory_size", 100000),
        predictions_enabled=mem_cfg.get("predictions", {}).get("enabled", False),
        predictions_error_policy=mem_cfg.get("predictions", {}).get("error_policy", "exact"),
        predictions_threshold=float(mem_cfg.get("predictions", {}).get("threshold", 0.0)),
        decay_enabled=mem_cfg.get("decay", {}).get("enabled", True),
        reconsolidation_enabled=mem_cfg.get("reconsolidation", {}).get("enabled", False),
        salience_threshold=float((mem_cfg.get("salience", {}) or {}).get("threshold", 0.0)),
        salience_weights=(mem_cfg.get("salience", {}) or {}).get("weights", {}),
    )
