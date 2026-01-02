"""Service endpoint registry for SomaFractalMemory."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceEndpoint:
    """Service endpoint configuration."""

    name: str
    env_var: str
    description: str
    default_port: int
    path: str = ""
    required: bool = True
    health_check: str | None = None

    def get_url(self, environment: str = "development", host: str | None = None) -> str:
        """Resolve service URL from environment or defaults."""
        url = os.environ.get(self.env_var)
        if url:
            return url.rstrip("/") + self.path

        if environment == "production" and self.required:
            raise ValueError(
                f"Missing required service: {self.env_var}\n"
                f"Service: {self.name} - {self.description}"
            )

        if not host:
            host = self.name.lower().replace(" ", "").replace("-", "")
        if environment == "development":
            host = "localhost"

        return f"http://{host}:{self.default_port}{self.path}"


class ServiceRegistry:
    """SomaFractalMemory service dependencies."""

    POSTGRES = ServiceEndpoint(
        name="postgres",
        env_var="SOMA_POSTGRES_URL",
        description="Database",
        default_port=5432,
        required=True,
    )

    REDIS = ServiceEndpoint(
        name="redis",
        env_var="SOMA_REDIS_HOST",
        description="Cache",
        default_port=6379,
        required=False,
    )

    MILVUS = ServiceEndpoint(
        name="milvus",
        env_var="SOMA_MILVUS_HOST",
        description="Vector store",
        default_port=19530,
        required=False,
    )

    SOMABRAIN = ServiceEndpoint(
        name="somabrain",
        env_var="SOMABRAIN_URL",
        description="Cognitive runtime callback",
        default_port=9696,
        required=False,
        health_check="/health",
    )

    @classmethod
    def get_all_services(cls) -> dict[str, ServiceEndpoint]:
        """Return all registered services."""
        return {
            name: getattr(cls, name)
            for name in dir(cls)
            if isinstance(getattr(cls, name), ServiceEndpoint)
        }

    @classmethod
    def validate_required(cls, environment: str) -> list[str]:
        """Return list of missing required service environment variables."""
        missing = []
        for _name, service in cls.get_all_services().items():
            if service.required:
                try:
                    service.get_url(environment=environment)
                except ValueError:
                    missing.append(service.env_var)
        return missing


SERVICES = ServiceRegistry()

__all__ = ["ServiceEndpoint", "ServiceRegistry", "SERVICES"]
