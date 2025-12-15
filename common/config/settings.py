"""Centralised settings definitions for Soma services.

The goal of this module is to provide a single Pydantic-based source of truth
for configuration. Service-specific settings classes should inherit from
``SomaBaseSettings`` so they automatically pick up the ``SOMA_`` environment
prefix and shared defaults (e.g. DNS names for shared infrastructure).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import json
    from json import JSONDecodeError
except ImportError:  # pragma: no cover - json is part of the stdlib
    json = None
    JSONDecodeError = ValueError

try:  # ``yaml`` is optional; config files fall back to JSON when absent.
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    yaml = None

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SomaBaseSettings(BaseSettings):
    """Base settings class shared by all Soma services.

    * ``env_prefix`` ensures environment variables follow ``SOMA_`` naming.
    * ``env_nested_delimiter`` allows structured values such as
      ``SOMA_REDIS__HOST``.
    """

    model_config = SettingsConfigDict(env_prefix="SOMA_", env_nested_delimiter="__")
    # Avoid pydantic warnings about names that collide with internal protected
    # namespaces (e.g. fields starting with "model_"). This keeps the
    # settings classes free of noisy warnings in tests and runtime.
    model_config.setdefault("protected_namespaces", ("settings_",))


class InfraEndpoints(BaseModel):
    """DNS endpoints for shared infrastructure services."""

    redis: str = Field(default="redis")
    vault: str = Field(default="vault")
    opa: str = Field(default="opa")
    auth: str = Field(default="auth")
    etcd: str = Field(default="etcd")
    prometheus: str = Field(default="prometheus")
    jaeger: str = Field(default="jaeger")
    # Additional services used by SMF
    milvus: str = Field(default="milvus")
    postgres: str = Field(default="postgres")


class LangfuseSettings(BaseModel):
    """Configuration for Langfuse observability integration."""

    # Intentionally empty defaults: services should obtain real keys from Vault or
    # environment variables. Keeping placeholders increases the risk of accidental
    # credential leakage or misuse in production.
    public_key: str = Field(default="", alias="langfuse_public")
    secret_key: str = Field(default="", alias="langfuse_secret")
    host: str = Field(default="", alias="langfuse_host")


class SMFSettings(SomaBaseSettings):
    """Settings specific to the SomaFractalMemory service."""

    namespace: str = Field(default="default")
    model_name: str = Field(default="microsoft/codebert-base")
    vector_dim: int = Field(default=768)
    # Canonical port for the HTTP service interface
    api_port: int = Field(default=9595, description="FastAPI HTTP port")
    postgres_url: str = Field(
        default="postgresql://soma:soma@postgres:5432/somamemory",
        description="DSN used by the Postgres-backed key-value store",
    )

    infra: InfraEndpoints = Field(default_factory=InfraEndpoints)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)

    # Additional environment‑driven flags that were previously accessed via
    # ``os.getenv`` throughout the codebase. They are now centralised here so
    # that all configuration is sourced from a single Pydantic model.
    async_metrics_enabled: bool = Field(
        default=False,
        description="Enable asynchronous metric submission (formerly SOMA_ASYNC_METRICS)",
    )
    fast_core_enabled: bool = Field(
        default=False,
        alias="SFM_FAST_CORE",
        description="Enable fast‑core in‑memory slab (formerly SFM_FAST_CORE env var)",
    )
    force_hash_embeddings: bool = Field(
        default=False,
        alias="SOMA_FORCE_HASH_EMBEDDINGS",
        description="Force hash‑based embeddings instead of transformer model",
    )
    model_name: str = Field(
        default="microsoft/codebert-base",
        alias="SOMA_MODEL_NAME",
        description="Transformer model name for embeddings (formerly SOMA_MODEL_NAME)",
    )

    hybrid_recall_default: bool = Field(
        default=True,
        alias="SOMA_HYBRID_RECALL_DEFAULT",
        description="Enable hybrid recall by default (formerly SOMA_HYBRID_RECALL_DEFAULT)",
    )

    # ---------------------------------------------------------------------
    # Core runtime limits (mirroring values previously accessed via env vars)
    # ---------------------------------------------------------------------
    max_memory_size: int = Field(
        default=100_000,
        validation_alias="SOMA_MAX_MEMORY_SIZE",
        description="Maximum number of memories the system will retain.",
    )
    pruning_interval_seconds: int = Field(
        default=600,
        validation_alias="SOMA_PRUNING_INTERVAL_SECONDS",
        description="Interval in seconds between background pruning runs.",
    )

    # Math/scoring knobs (kept optional; defaults preserve current behavior)
    similarity_metric: str = Field(
        default="cosine",
        description="Similarity metric for vector search (cosine only at present)",
    )
    similarity_allow_negative: bool = Field(
        default=False,
        description="If true, do not clamp negative cosine similarities to 0.",
    )
    hybrid_boost: float = Field(
        default=2.0,
        description="Default keyword boost added per matched term in hybrid scoring.",
    )

    # Hybrid/vector search fine-tuning
    hybrid_candidate_multiplier: float = Field(
        default=4.0,
        description="Multiply top_k by this factor to fetch more vector candidates before re-ranking.",
    )

    # Fast-core slab parameters
    fast_core_initial_capacity: int = Field(
        default=1024,
        description="Initial capacity for fast-core contiguous slabs.",
    )

    # ---------------------------------------------------------------------
    # Additional runtime and API configuration (mirrors environment vars used
    # throughout the codebase). These fields allow the HTTP API and other
    # components to obtain configuration from a single source.
    # ---------------------------------------------------------------------
    log_level: str = Field(default="INFO", description="Logging level for the service")
    cors_origins: str = Field(
        default="", description="Comma‑separated list of allowed CORS origins"
    )
    rate_limit_max: int = Field(
        default=60, description="Maximum requests per rate‑limit window (0 disables)"
    )
    rate_limit_window: float = Field(
        default=60.0, description="Rate‑limit window length in seconds"
    )
    memory_namespace: str = Field(
        default="api_ns", description="Namespace for memory operations used by the HTTP API."
    )
    memory_mode: str = Field(
        default="evented_enterprise", description="Memory mode identifier used by the API."
    )
    max_request_body_mb: float = Field(default=5.0, description="Maximum request body size in MB.")
    # Redis connection defaults (mirroring typical local dev values)
    redis_port: int = Field(default=6379, description="Redis port (overrides infra if set)")
    redis_db: int = Field(default=0, description="Redis DB index")

    # Postgres TLS/SSL options (optional)
    postgres_ssl_mode: str | None = Field(
        default=None, description="Postgres SSL mode (e.g., require)"
    )
    postgres_ssl_root_cert: str | None = Field(
        default=None, description="Path to root CA cert for Postgres TLS"
    )
    postgres_ssl_cert: str | None = Field(default=None, description="Client cert for Postgres TLS")
    postgres_ssl_key: str | None = Field(default=None, description="Client key for Postgres TLS")

    # Importance normalization parameters
    importance_reservoir_max: int = Field(default=512, description="Max samples in reservoir")
    importance_recompute_stride: int = Field(
        default=64, description="Recompute quantiles every N inserts"
    )
    importance_winsor_delta: float = Field(
        default=0.25,
        description="Winsorization delta as a fraction of core spread (q90-q10)",
    )
    importance_logistic_target_ratio: float = Field(
        default=9.0,
        description="Target odds ratio for logistic slope (k = ln(target)/spread)",
    )
    importance_logistic_k_max: float = Field(
        default=25.0, description="Maximum logistic slope to avoid overflow"
    )

    # Decay heuristic weights and threshold
    decay_age_hours_weight: float = Field(default=1.0)
    decay_recency_hours_weight: float = Field(default=1.0)
    decay_access_weight: float = Field(default=0.5)
    decay_importance_weight: float = Field(default=2.0)
    decay_threshold: float = Field(default=2.0)

    # JWT authentication config
    jwt_enabled: bool = Field(default=False, description="Enable JWT authentication")
    jwt_issuer: str = Field(default="", description="JWT expected issuer")
    jwt_audience: str = Field(default="", description="JWT expected audience")
    jwt_secret: str = Field(default="", description="JWT HMAC secret (if using HS256)")
    jwt_public_key: str = Field(default="", description="JWT public key (if using RS256)")

    # Vault/Kubernetes secrets integration
    vault_url: str = Field(default="", description="Vault endpoint URL")
    secrets_path: str = Field(default="", description="Path to secrets in Vault/K8s")

    model_config = SettingsConfigDict(arbitrary_types_allowed=True)

    def validate_config(self) -> None:
        """Validate critical config fields for production readiness."""
        errors = []
        if not self.namespace:
            errors.append("namespace is required")
        if not self.api_port or not (1024 <= self.api_port <= 65535):
            errors.append("api_port must be valid TCP port")
        if self.jwt_enabled:
            if not (self.jwt_secret or self.jwt_public_key):
                errors.append("JWT enabled but no key configured")
            if not self.jwt_issuer:
                errors.append("JWT issuer required")
            if not self.jwt_audience:
                errors.append("JWT audience required")
        if errors:
            raise ValueError(f"Config validation failed: {errors}")

    # ---------------------------------------------------------------------
    # Additional operational flags and paths previously scattered via
    # ``os.getenv`` in various modules. Centralising them here ensures a single
    # source of truth for configuration.
    # ---------------------------------------------------------------------
    # Backup / data directories
    backup_dir: Path = Field(default=Path("./backups"), description="Backup directory path")
    memory_data_dir: Path = Field(default=Path("./data"), description="Memory data directory path")
    s3_bucket: str = Field(default="", description="S3 bucket name for backups")

    # Serialization format (json or msgpack)
    serializer: str = Field(default="json", description="Serializer format for memory data")

    # API authentication token (used by end‑to‑end tests and external callers)
    api_token: str | None = Field(default=None, description="Bearer token for API access")

    # Batch upsert controls (formerly SOMA_ENABLE_BATCH_UPSERT etc.)
    enable_batch_upsert: bool = Field(default=False, description="Enable batched KV/vector upserts")
    batch_size: int = Field(default=100, description="Batch size for upserts")
    batch_flush_ms: int = Field(default=5, description="Batch flush interval in milliseconds")

    # Milvus configuration (Qdrant removed - standardized on Milvus)
    milvus_host: str = Field(default="milvus", description="Milvus service host")
    milvus_port: int = Field(default=19530, description="Milvus gRPC port")

    # ---------------------------------------------------------------------
    # Logging / API runtime configuration
    # ---------------------------------------------------------------------
    log_level: str = Field(default="INFO", description="Logging level for the service")
    cors_origins: str = Field(
        default="", description="Comma‑separated list of allowed CORS origins"
    )

    # ---------------------------------------------------------------------
    # Rate limiting defaults (mirrors existing env vars)
    # ---------------------------------------------------------------------
    rate_limit_max: int = Field(
        default=60, description="Maximum requests per rate‑limit window (0 disables)"
    )
    rate_limit_window: float = Field(
        default=60.0, description="Rate‑limit window length in seconds"
    )


def _load_file_data(config_file: Path | None) -> dict[str, Any]:
    """Load settings data from JSON or YAML, returning an empty dict when absent."""

    if not config_file:
        return {}
    if not config_file.exists():
        return {}

    suffix = config_file.suffix.lower()
    raw: dict[str, Any] = {}
    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError(
                "PyYAML is required to parse YAML configuration files; install the 'pyyaml' package."
            )
        data = yaml.safe_load(config_file.read_text())
        if isinstance(data, dict):
            raw = data
    elif suffix == ".json":
        if json is None:
            raise RuntimeError("The Python json module is required but not available.")
        try:
            raw = json.loads(config_file.read_text())
        except JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in config file {config_file}: {exc}") from exc
    else:
        raise ValueError(
            f"Unsupported config file extension '{suffix}' for {config_file}. Use .json or .yaml/.yml."
        )
    return raw


def load_settings(
    *,
    config_file: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> SMFSettings:
    """Construct :class:`SMFSettings` from the provided sources.

    Precedence (highest first):
    1. ``overrides`` dict passed explicitly.
    2. Environment variables (handled by ``SMFSettings``).
    3. Data from ``config_file`` (JSON or YAML).

    Parameters
    ----------
    config_file:
        Optional path to a JSON or YAML file containing settings payload.
    overrides:
        Optional dict used to override or supplement the file/env-derived data.
    """

    path = Path(config_file).expanduser() if config_file else None
    file_data = _load_file_data(path)
    payload = {**file_data, **(overrides or {})}
    return SMFSettings(**payload)


# Export a singleton instance for convenient imports throughout the project.
# This mirrors the pattern used in `somafractalmemory/config/settings.py` and
# satisfies test modules that import ``settings`` directly from this module.
settings = SMFSettings()


__all__ = [
    "InfraEndpoints",
    "LangfuseSettings",
    "SMFSettings",
    "SomaBaseSettings",
    "load_settings",
]
