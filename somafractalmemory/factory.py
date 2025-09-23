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
    Enum for supported memory system modes (v2).

    Modes:
    - DEVELOPMENT: Local development (default).
    - TEST: CI/test mode with in-memory components.
    - EVENTED_ENTERPRISE: Production event-driven mode (Kafka + Postgres + Qdrant).
    - CLOUD_MANAGED: Alias for EVENTED_ENTERPRISE using managed services.
    - LEGACY_COMPAT: Hidden compatibility mode for short-term migration.
    """

    DEVELOPMENT = "development"
    TEST = "test"
    EVENTED_ENTERPRISE = "evented_enterprise"
    CLOUD_MANAGED = "cloud_managed"
    # LEGACY_COMPAT removed — project is v2 JSON-first only.


# Note: legacy aliases were intentionally removed for v2. Callers should use
# the canonical v2 mode names (DEVELOPMENT, TEST, EVENTED_ENTERPRISE,
# CLOUD_MANAGED). This module enforces the new names to avoid ambiguity.


# Backwards-compatible aliases for older enum names used in tests and existing code.
# These provide a short-term compatibility shim so tests referencing the previous
# names (e.g. LOCAL_AGENT, ON_DEMAND, ENTERPRISE) do not immediately break.
# Keep this shim small and temporary — it's better to update callers to the new
# v2 mode names in follow-up work.
# Map the historical LOCAL_AGENT to LEGACY_COMPAT so older behavior (WAL format,
# storage expectations) remains available for tests and short-term compatibility.
# Legacy aliases removed — project is v2 JSON-first only.


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

    if mode == MemoryMode.DEVELOPMENT:
        # Development: local Redis + local Qdrant (fast feedback loop)
        kv_store = RedisKeyValueStore(testing=True)
        # If the developer explicitly requests qdrant (via vector backend) or
        # provides a qdrant path in config, prefer QdrantVectorStore and a
        # local Ollama prediction provider for a more realistic local setup.
        qdrant_cfg = config.get("qdrant", {})
        if vector_cfg.get("backend") == "qdrant" or qdrant_cfg.get("path"):
            # If a path is provided, hand it through to QdrantVectorStore so
            # tests that create on-disk qdrant instances continue to work.
            qconf = qdrant_cfg if qdrant_cfg else {"location": ":memory:"}
            vector_store = QdrantVectorStore(collection_name=namespace, **qconf)
            prediction_provider = OllamaPredictionProvider()
        else:
            vector_store = InMemoryVectorStore()
            prediction_provider = NoPredictionProvider()
        graph_store = NetworkXGraphStore()

    elif mode == MemoryMode.TEST:
        # Test mode mirrors development but favors in-memory deterministic stores
        kv_store = RedisKeyValueStore(testing=True)
        vector_store = InMemoryVectorStore()
        graph_store = NetworkXGraphStore()
        prediction_provider = NoPredictionProvider()

    elif mode in (MemoryMode.EVENTED_ENTERPRISE, MemoryMode.CLOUD_MANAGED):
        # Evented enterprise: expects remote connection details (Kafka/Postgres/Qdrant)
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
