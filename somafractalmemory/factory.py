from enum import Enum
from typing import Any, Dict, Optional

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.implementations.graph import NetworkXGraphStore
from somafractalmemory.implementations.prediction import (
    ExternalPredictionProvider,
    NoPredictionProvider,
    OllamaPredictionProvider,
)
from somafractalmemory.implementations.storage import (
    InMemoryVectorStore,
    QdrantVectorStore,
    RedisKeyValueStore,
)


class MemoryMode(Enum):
    """
    Enum for supported memory system modes.

    Attributes
    ----------
    ON_DEMAND : str
        In-memory mode for quick tests and demos.
    LOCAL_AGENT : str
        Local agent mode with Redis and Qdrant backends.
    ENTERPRISE : str
        Enterprise mode for remote/distributed backends.
    """

    ON_DEMAND = "on_demand"
    LOCAL_AGENT = "local_agent"
    ENTERPRISE = "enterprise"


def create_memory_system(
    mode: MemoryMode, namespace: str, config: Optional[Dict[str, Any]] = None
) -> SomaFractalMemoryEnterprise:
    """
    Factory function to create a SomaFractalMemoryEnterprise instance based on the specified mode.

    Parameters
    ----------
    mode : MemoryMode
        The mode to use (ON_DEMAND, LOCAL_AGENT, ENTERPRISE).
    namespace : str
        The namespace for the memory system.
    config : Optional[Dict[str, Any]]
        Optional configuration dictionary for backend setup.

    Returns
    -------
    SomaFractalMemoryEnterprise
        Configured memory system instance.
    """
    config = config or {}
    kv_store = None
    vector_store = None
    graph_store = None
    prediction_provider = None

    vector_cfg = config.get("vector", {})
    enterprise_cfg = config.get("memory_enterprise", {})

    if mode == MemoryMode.ON_DEMAND:
        # Pure in-memory setup for quick tests and demos
        kv_store = RedisKeyValueStore(testing=True)
        if vector_cfg.get("backend") == "qdrant":
            qconf = {"location": ":memory:"}
            vector_store = QdrantVectorStore(collection_name=namespace, **qconf)
        else:
            vector_store = InMemoryVectorStore()
        graph_store = NetworkXGraphStore()
        prediction_provider = NoPredictionProvider()

    elif mode == MemoryMode.LOCAL_AGENT:
        redis_config = config.get("redis", {})
        qdrant_config = config.get("qdrant", {"path": f"./{namespace}_qdrant"})
        kv_store = RedisKeyValueStore(**redis_config)
        vector_store = QdrantVectorStore(collection_name=namespace, **qdrant_config)
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
        graph_store = NetworkXGraphStore()  # Swap for a remote graph DB in prod

        ext_pred_cfg = config.get("external_prediction")
        if (
            isinstance(ext_pred_cfg, dict)
            and ext_pred_cfg.get("api_key")
            and ext_pred_cfg.get("endpoint")
        ):
            prediction_provider = ExternalPredictionProvider(
                api_key=ext_pred_cfg["api_key"], endpoint=ext_pred_cfg["endpoint"]
            )
        else:
            prediction_provider = OllamaPredictionProvider()

    else:
        raise ValueError(f"Unsupported memory mode: {mode}")

    return SomaFractalMemoryEnterprise(
        namespace=namespace,
        kv_store=kv_store,
        vector_store=vector_store,
        graph_store=graph_store,
        prediction_provider=prediction_provider,
        max_memory_size=enterprise_cfg.get("max_memory_size", 100000),
        pruning_interval_seconds=enterprise_cfg.get("pruning_interval_seconds", 600),
        decay_thresholds_seconds=enterprise_cfg.get("decay_thresholds_seconds", []),
        decayable_keys_by_level=enterprise_cfg.get("decayable_keys_by_level", []),
        decay_enabled=enterprise_cfg.get("decay_enabled", True),
        reconcile_enabled=enterprise_cfg.get("reconcile_enabled", True),
    )
