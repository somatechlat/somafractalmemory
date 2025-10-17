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


class InfraEndpoints(BaseModel):
    """DNS endpoints for shared infrastructure services."""

    redis: str = Field(default="redis")
    kafka: str = Field(default="kafka")
    vault: str = Field(default="vault")
    opa: str = Field(default="opa")
    auth: str = Field(default="auth")
    etcd: str = Field(default="etcd")
    prometheus: str = Field(default="prometheus")
    jaeger: str = Field(default="jaeger")
    # Additional services used by SMF
    qdrant: str = Field(default="qdrant")
    postgres: str = Field(default="postgres")


class LangfuseSettings(BaseModel):
    """Configuration for Langfuse observability integration."""

    # Intentionally empty defaults: services should obtain real keys from Vault or
    # environment variables. Keeping placeholders increases the risk of accidental
    # credential leakage or misuse in production.
    public_key: str = Field(default="", alias="langfuse_public")
    secret_key: str = Field(default="", alias="langfuse_secret")
    host: str = Field(default="", alias="langfuse_host")


class KafkaSettings(BaseSettings):
    bootstrap_servers: str = "localhost:9092"
    security_protocol: str = "PLAINTEXT"
    ssl_ca_location: str | None = None
    sasl_mechanism: str = "PLAIN"
    sasl_username: str | None = None
    sasl_password: str | None = None


class SMFSettings(SomaBaseSettings):
    """Settings specific to the SomaFractalMemory service."""

    namespace: str = Field(default="default")
    model_name: str = Field(default="microsoft/codebert-base")
    vector_dim: int = Field(default=768)
    # Canonical ports for the service interfaces
    api_port: int = Field(default=9595, description="FastAPI HTTP port")
    grpc_port: int = Field(default=50053, description="gRPC service port")
    postgres_url: str = Field(
        default="postgresql://soma:soma@postgres:5432/somamemory",
        description="DSN used by the Postgres-backed key-value store",
    )
    qdrant_host: str = Field(
        default="qdrant",
        description="Hostname for the Qdrant vector database",
    )
    infra: InfraEndpoints = Field(default_factory=InfraEndpoints)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)

    model_config = SettingsConfigDict(arbitrary_types_allowed=True)


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


__all__ = [
    "InfraEndpoints",
    "LangfuseSettings",
    "KafkaSettings",
    "SMFSettings",
    "SomaBaseSettings",
    "load_settings",
]
