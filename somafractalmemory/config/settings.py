"""Centralised configuration for SomaFractalMemory.

All environment variables are declared here as typed fields using
``pydantic.BaseSettings``.  The ``settings`` singleton exported from
``somafractalmemory.config`` should be imported wherever configuration is
required.  This eliminates scattered ``os.getenv`` calls and satisfies the
Vibe coding rule **Consistency**.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import AnyUrl, Field, PostgresDsn, RedisDsn

# BaseSettings has been moved to the separate `pydantic-settings` package in
# Pydantic v2. Import it from there while keeping the other types from the main
# `pydantic` package.
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---------------------------------------------------------------------
    # Core feature flags
    # ---------------------------------------------------------------------
    async_metrics: bool = Field(
        False,
        validation_alias="SOMA_ASYNC_METRICS",
        description="Enable async metrics collection.",
    )
    enable_batch_upsert: bool = Field(
        False,
        validation_alias="SOMA_ENABLE_BATCH_UPSERT",
        description="Enable batch upserts.",
    )
    batch_size: int = Field(
        100,
        validation_alias="SOMA_BATCH_SIZE",
        description="Batch size for upserts.",
    )
    batch_flush_ms: int = Field(
        5,
        validation_alias="SOMA_BATCH_FLUSH_MS",
        description="Batch flush interval (ms).",
    )
    force_hash_embeddings: bool = Field(
        False,
        validation_alias="SOMA_FORCE_HASH_EMBEDDINGS",
        description="Force recompute of embeddings.",
    )
    fast_core_enabled: bool = Field(
        False,
        validation_alias="SFM_FAST_CORE",
        description="Enable fast‑core mode.",
    )

    # ---------------------------------------------------------------------
    # Resource limits / sizing
    # ---------------------------------------------------------------------
    max_memory_size: int = Field(
        10_000,
        validation_alias="SOMA_MAX_MEMORY_SIZE",
        description="Maximum number of memories.",
    )
    vector_dim: int = Field(
        768,
        validation_alias="SOMA_VECTOR_DIM",
        description="Embedding vector dimension.",
    )
    qdrant_scroll_limit: int = Field(
        100,
        validation_alias="SOMA_QDRANT_SCROLL_LIMIT",
        description="Qdrant scroll pagination limit.",
    )

    # ---------------------------------------------------------------------
    # Service URLs / DSNs
    # ---------------------------------------------------------------------
    # Postgres DSN – optional because the repository's .env provides component
    # variables (user, password, host, etc.) rather than a full DSN. If not set we
    # will build a default URL in the consuming code.
    postgres_url: PostgresDsn | None = Field(
        None,
        validation_alias="POSTGRES_URL",
        description="Postgres DSN.",
    )
    redis_url: RedisDsn | None = Field(
        None,
        validation_alias="REDIS_URL",
        description="Redis DSN.",
    )
    qdrant_url: AnyUrl | None = Field(
        None,
        validation_alias="QDRANT_URL",
        description="Qdrant URL.",
    )

    # Host/port components (kept for backward compatibility)
    redis_host: str = Field("localhost", validation_alias="REDIS_HOST")
    redis_port: int = Field(6379, validation_alias="REDIS_PORT")
    redis_db: int = Field(0, validation_alias="REDIS_DB")
    qdrant_host: str = Field("localhost", validation_alias="QDRANT_HOST")
    qdrant_port: int = Field(6333, validation_alias="QDRANT_PORT")
    qdrant_tls: bool = Field(False, validation_alias="QDRANT_TLS")
    qdrant_tls_cert: Path | None = Field(None, validation_alias="QDRANT_TLS_CERT")

    # ---------------------------------------------------------------------
    # API & security
    # ---------------------------------------------------------------------
    api_token: str | None = Field(
        None,
        validation_alias="SOMA_API_TOKEN",
        description="API bearer token.",
    )
    api_token_file: Path | None = Field(
        None,
        validation_alias="SOMA_API_TOKEN_FILE",
        description="File containing API token.",
    )
    cors_origins: list[str] = Field(
        default_factory=list,
        validation_alias="SOMA_CORS_ORIGINS",
        description="CORS whitelist.",
    )
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(
        "plain",
        validation_alias="LOG_FORMAT",
        description="plain or json",
    )

    # ---------------------------------------------------------------------
    # Rate limiting
    # ---------------------------------------------------------------------
    rate_limit_max: int = Field(
        60,
        validation_alias="SOMA_RATE_LIMIT_MAX",
        description="Max requests per window (0 disables).",
    )
    rate_limit_window_seconds: float = Field(
        60.0,
        validation_alias="SOMA_RATE_LIMIT_WINDOW_SECONDS",
        description="Rate‑limit window length.",
    )

    # ---------------------------------------------------------------------
    # Misc paths & flags
    # ---------------------------------------------------------------------
    config_file: Path = Field(Path("config.yaml"), validation_alias="CONFIG_FILE")
    backup_dir: Path = Field(Path("./backups"), validation_alias="SOMA_BACKUP_DIR")
    memory_data_dir: Path = Field(Path("./data"), validation_alias="SOMA_MEMORY_DATA_DIR")
    s3_bucket: str = Field("", validation_alias="SOMA_S3_BUCKET")
    serializer: str = Field("json", validation_alias="SOMA_SERIALIZER")
    memory_namespace: str = Field("api_ns", validation_alias="SOMA_MEMORY_NAMESPACE")
    model_name: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2",
        validation_alias="SOMA_MODEL_NAME",
    )
    hybrid_recall_default: bool = Field(True, validation_alias="SOMA_HYBRID_RECALL_DEFAULT")
    max_request_body_mb: float = Field(5.0, validation_alias="SOMA_MAX_REQUEST_BODY_MB")

    # ---------------------------------------------------------------------
    # Observability (OpenTelemetry)
    # ---------------------------------------------------------------------
    otel_exporter_endpoint: str | None = Field(
        None,
        validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT",
        description="OTLP collector endpoint.",
    )

    # ---------------------------------------------------------------------
    # Test‑only flags (used in conftest)
    # ---------------------------------------------------------------------
    use_live_infura: bool = Field(False, validation_alias="USE_LIVE_INFRA")
    use_real_infra: bool = Field(False, validation_alias="USE_REAL_INFRA")

    # Pydantic v2 configuration to enable the validation_alias usage.
    # Allow unknown environment variables (e.g., POSTGRES_USER, REDIS_HOST_PORT, etc.)
    # to be ignored rather than raising validation errors.
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


# Export a singleton for easy import
settings = Settings()
