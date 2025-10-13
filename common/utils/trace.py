"""Tracing helpers built on OpenTelemetry."""

from __future__ import annotations

from common.utils.logger import get_logger

LOGGER = get_logger("somafractalmemory").bind(component="trace")


def configure_tracer(
    service_name: str,
    *,
    endpoint: str = "http://jaeger.soma.svc.cluster.local:4317",
    insecure: bool = True,
) -> object | None:
    """Configure a global tracer for the service if OpenTelemetry is available.

    This function performs lazy imports so the package is optional at runtime.
    If OpenTelemetry packages aren't installed the function returns None and
    the caller should gracefully proceed without tracing.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception:  # pragma: no cover - optional dependency
        LOGGER.debug(
            "OpenTelemetry packages not found; tracer disabled",
            service_name=service_name,
        )
        return None

    try:
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        exporter = None
        try:
            exporter = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
        except Exception as exc:  # pragma: no cover - exporter creation environment dependent
            LOGGER.error(
                "Failed to initialise OTLP exporter",
                service_name=service_name,
                error=str(exc),
            )
            exporter = None

        if exporter is not None:
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)

        trace.set_tracer_provider(provider)
        return trace.get_tracer(service_name)
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.exception(
            "Unexpected error configuring tracer",
            service_name=service_name,
            error=str(exc),
        )
        return None


__all__ = ["configure_tracer"]
